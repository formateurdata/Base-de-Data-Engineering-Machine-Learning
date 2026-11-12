"""Ingestion de la table `commandes` vers la zone bronze : la première brique du pipeline ETL du module.

À déclencher à la main, après `make generate`. Chaque étape est une tâche, et la ligne `>>` en bas du fichier
fixe leur ordre :

- `lire_repere` récupère la date de la dernière modification déjà ingérée.
- `extraire_vers_bronze` vérifie le schéma de la source, extrait les lignes modifiées depuis cette date, contrôle leur
  qualité, puis les copie dans un fichier Parquet sur HDFS. Un contrôle bloquant en échec arrête le lot sans nouvelle
  tentative, avant toute écriture.
- `controler_bronze` relit le fichier, le compare à ce qui a été écrit, puis affiche ses premières lignes et le dossier.
- `avancer_repere` enregistre le nouveau repère, seulement si le contrôle a réussi.

Sans nouvelle ligne, `extraire_vers_bronze` et les tâches suivantes passent à `skipped`, et aucun fichier n'est écrit.
Les lignes ne passent jamais par XCom, qui ne transporte que le repère, le chemin du fichier et les chiffres du lot.
"""

import json
import logging
import re
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import pendulum
from airflow.providers.apache.hdfs.hooks.webhdfs import WebHDFSHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import DAG, task
from airflow.sdk.exceptions import AirflowFailException, AirflowSkipException

# Les messages de ce logger apparaissent dans l'onglet Logs de la tâche
JOURNAL = logging.getLogger("ingestion_commandes")

CONN_SOURCE = "source_postgres"  # Identifiant de la connexion Airflow vers PostgreSQL
CONN_BRONZE = "bronze_hdfs"  # Identifiant de la connexion Airflow vers HDFS (WebHDFS)
TABLE = (
    "commandes"  # Table source, aussi utilisée pour nommer les dossiers et les fichiers
)
DOSSIER_BRONZE = f"/bronze/{TABLE}"  # Racine de la zone bronze pour cette table
# Le préfixe « _ » fait ignorer ce fichier par les outils qui lisent le dossier comme un jeu de données
FICHIER_REPERE = f"{DOSSIER_BRONZE}/_repere.txt"
# Valeur PostgreSQL antérieure à toute date : à la première exécution, toutes les lignes sont nouvelles
REPERE_INITIAL = "-infinity"
DOSSIER_REPERES = f"{DOSSIER_BRONZE}/_reperes"  # Un fichier par repère publié, on garde le plus récent
APERCU_LIGNES = 5  # Nombre de lignes affichées dans le journal par controler_bronze
# Schéma attendu de la source, d'après sa documentation (01_schema.sql)
SCHEMA_SOURCE = {
    "id": "bigint",
    "client_id": "integer",
    "produit": "text",
    "quantite": "integer",
    "montant": "numeric",
    "statut": "text",
    "updated_at": "timestamp with time zone",
}
STATUTS = (
    "payee",
    "expediee",
    "annulee",
    "remboursee",
)  # Valeurs autorisées pour la colonne statut


# Construit le chemin HDFS du fichier Parquet d'un lot, à partir de l'exécution et de la date d'ingestion
def chemin_parquet(run_id: str, date: str) -> str:
    """Une nouvelle tentative réécrit le même fichier. HDFS refuse « : » dans un nom."""
    nom = re.sub(
        r"[^\w.-]", "_", run_id
    )  # Remplace tout caractère interdit (« : », « + ») par « _ »
    return f"{DOSSIER_BRONZE}/date_ingestion={date}/{TABLE}_{nom}.parquet"


# Schéma Arrow du fichier Parquet : il fixe le type de chaque colonne, quel que soit le contenu du lot
def schema_bronze():
    """Sans ces types, la précision de `montant` dépend de chaque lot et le dossier ne se relit plus en une fois."""
    # Importé ici : Airflow relit ce fichier en continu, PyArrow ne sert qu'à l'exécution
    import pyarrow as pa

    return pa.schema([
        ("id", pa.int64()),  # bigint
        ("client_id", pa.int32()),  # integer
        ("produit", pa.string()),  # text
        ("quantite", pa.int32()),  # integer
        (
            "montant",
            pa.decimal128(10, 2),
        ),  # numeric : 10 chiffres dont 2 décimales, sans arrondi flottant
        ("statut", pa.string()),  # text
        (
            "updated_at",
            pa.timestamp("us", tz="UTC"),
        ),  # timestamptz, microsecondes, en UTC
    ])


# Contrôle de schéma : compare les colonnes réelles de la table source à SCHEMA_SOURCE, avant de lire une ligne
def verifier_schema_source(source) -> None:
    """Colonne absente ou de type différent : arrêt. Colonne en trop : simple avertissement."""
    # Dictionnaire {nom de colonne: type PostgreSQL} lu dans le catalogue de la base
    observe = dict(
        source.get_records(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s",
            parameters=(TABLE,),
        )
    )
    # Parcourir l'union des colonnes attendues et observées,
    # pour détecter aussi les colonnes en plus
    # Écarts sur les colonnes attendues uniquement : colonne manquante ou type différent
    ecarts = {
        nom: (attendu, obs)
        for nom, attendu in SCHEMA_SOURCE.items()
        if (obs := observe.get(nom)) != attendu
    }

    # Colonnes présentes dans la source mais non prévues : tolérées, car le lot n'en lit aucune
    if en_trop := sorted(observe.keys() - SCHEMA_SOURCE.keys()):
        JOURNAL.warning("colonnes_en_trop table=%s colonnes=%s", TABLE, en_trop)

    if ecarts:
        # Échec définitif : une nouvelle tentative lirait le même schéma
        raise AirflowFailException(
            f"Schéma de {TABLE} non conforme, (attendu, reçu) : {ecarts}"
        )


# Contrôle de qualité : chaque règle donne un masque des lignes en défaut, calculé sur tout le lot
def controler_lot(lignes) -> None:
    """Règles de qualité bloquantes : une seule suffit à arrêter le lot, sans nouvelle tentative."""
    regles = {
        "aucune valeur vide": lignes.isna().any(
            axis=1
        ),  # Au moins une cellule vide dans la ligne
        "id unique": lignes[
            "id"
        ].duplicated(),  # Marque les répétitions d'un id déjà vu dans le lot
        "quantite positive": lignes["quantite"] <= 0,  # Défaut : zéro ou négatif
        # Les montants sont des Decimal : le flottant ne sert qu'à lire le signe
        "montant positif ou nul": lignes["montant"].astype(float) < 0,
        "statut dans la liste": ~lignes["statut"].isin(
            STATUTS
        ),  # Défaut : valeur hors de STATUTS
    }
    # Nombre de lignes en défaut par règle ; écrit dans le journal même quand tout est à zéro
    compte_rendu = {nom: int(defauts.sum()) for nom, defauts in regles.items()}
    JOURNAL.info(
        "qualite table=%s lignes_en_defaut=%s",
        TABLE,
        json.dumps(compte_rendu, ensure_ascii=False),
    )
    # Une seule règle en défaut suffit : AirflowFailException interdit les nouvelles tentatives
    if echecs := [nom for nom, nombre in compte_rendu.items() if nombre]:
        exemples = {
            nom: lignes.loc[regles[nom], "id"].head(5).tolist() for nom in echecs
        }
        raise AirflowFailException(
            f"Règles de qualité en échec : {echecs}, premiers id : {exemples}"
        )


# Liste le contenu de la zone bronze, pour l'afficher dans le journal du contrôle
def decrire_bronze(client) -> str:
    """Une ligne par fichier avec sa taille en octets, comme `hdfs dfs -ls -R`."""
    lignes = []
    for (dossier, _), _, fichiers in client.walk(
        DOSSIER_BRONZE, status=True
    ):  # Parcours récursif des sous-dossiers
        lignes += [
            f"{statut['length']:>10} {dossier}/{nom}" for nom, statut in fichiers
        ]
    return "\n".join(lignes)


# Callback appelé par Airflow à chaque échec de tâche (voir on_failure_callback dans default_args)
def signaler_echec(contexte: dict) -> None:
    """Seul point d'alerte du projet pour l'instant : un événement dans le journal de la tâche."""
    instance = contexte[
        "ti"
    ]  # Instance de tâche : donne le DAG, la tâche, l'exécution et le numéro d'essai
    JOURNAL.error(
        "tache_en_echec dag=%s tache=%s run=%s essai=%s",
        instance.dag_id,
        instance.task_id,
        instance.run_id,
        instance.try_number,
    )


# Vérifie qu'une chaîne est une date ISO avec fuseau horaire, et la renvoie normalisée
def valider_repere(valeur: str) -> str:
    """Seules les dates avec fuseau horaire peuvent devenir un repère PostgreSQL."""
    date = datetime.fromisoformat(
        valeur
    )  # Lève ValueError si le format n'est pas une date ISO
    if (
        date.utcoffset() is None
    ):  # Date « naïve » : l'heure serait ambiguë côté PostgreSQL
        raise ValueError("Le repère doit contenir un fuseau horaire")
    return date.isoformat()


# Retourne le repère le plus récent publié sur HDFS, ou REPERE_INITIAL si aucun n'existe
def dernier_repere(client) -> str:
    """Ignore les fichiers temporaires ; accepte aussi l'ancien format pour migrer."""
    valeurs = []
    if client.status(
        DOSSIER_REPERES, strict=False
    ):  # strict=False : renvoie None si le dossier n'existe pas
        for nom in client.list(DOSSIER_REPERES):
            if nom.endswith(
                ".txt"
            ):  # Les .tmp sont des écritures inachevées : ignorées
                with client.read(
                    f"{DOSSIER_REPERES}/{nom}", encoding="utf-8"
                ) as fichier:
                    valeurs.append(valider_repere(fichier.read()))
    # Ancien format : un fichier unique, écrasé à chaque fois
    if client.status(FICHIER_REPERE, strict=False):
        with client.read(FICHIER_REPERE, encoding="utf-8") as fichier:
            try:
                valeurs.append(valider_repere(fichier.read()))
            except (
                ValueError
            ):  # Contenu illisible : on s'appuie sur les versions valides
                JOURNAL.warning(
                    "ancien_repere_invalide : reprise depuis les versions valides ou depuis le début"
                )
    # Le maximum est pris en tant que date, pas en tant que texte
    return max(valeurs, key=datetime.fromisoformat) if valeurs else REPERE_INITIAL


# Écrit un nouveau repère de façon atomique : fichier temporaire, relecture, puis renommage
def publier_repere(client, valeur: str) -> None:
    """Publie par renommage HDFS atomique sans jamais écraser un repère validé.

    Une interruption laisse au plus un .tmp ignoré à la lecture. Si le renommage
    a réussi avant une perte de connexion, la nouvelle tentative est sans danger.
    """
    valeur = valider_repere(
        valeur
    )  # Refuse une date sans fuseau avant d'écrire quoi que ce soit
    client.makedirs(DOSSIER_REPERES)  # Sans effet si le dossier existe déjà
    nom = f"{DOSSIER_REPERES}/{uuid.uuid4().hex}"  # Nom unique : un repère n'en écrase jamais un autre
    client.write(f"{nom}.tmp", data=valeur, encoding="utf-8")
    with client.read(
        f"{nom}.tmp", encoding="utf-8"
    ) as fichier:  # Relecture pour détecter une écriture tronquée
        if fichier.read() != valeur:
            raise ValueError("Écriture du repère incomplète")
    # Le client HDFS lève une exception si le renommage est refusé.
    client.rename(f"{nom}.tmp", f"{nom}.txt")


# Tâche 1 : lit le repère, c'est-à-dire la date de la dernière modification déjà ingérée
@task
def lire_repere() -> str:
    """Lit la dernière version publiée ; vider la zone bronze relance tout."""
    repere = dernier_repere(WebHDFSHook(webhdfs_conn_id=CONN_BRONZE).get_conn())
    JOURNAL.info("repere_lu table=%s repere=%s", TABLE, repere)
    return repere


# Tâche 2 : vérifie le schéma, extrait les lignes nouvelles, les contrôle, puis les écrit en Parquet sur HDFS
@task
def extraire_vers_bronze(ti=None, run_id=None, dag_run=None) -> dict:
    """Copie dans un Parquet, avec le rôle lecteur, les lignes modifiées depuis le repère.

    Lecture et écriture restent dans la même tâche pour que les lignes ne passent pas par XCom. Le repère suppose un
    seul écrivain à la fois, ce que garantit le verrou du générateur : une transaction plus ancienne, validée après une
    plus récente, serait manquée. Le lot tient en mémoire : sans conséquence sur quelques milliers de lignes, à revoir
    sur un gros volume.
    """
    debut = time.monotonic()  # Sert à mesurer la durée de la tâche pour le journal
    repere = ti.xcom_pull(task_ids="lire_repere")  # Résultat de la tâche précédente
    source = PostgresHook(postgres_conn_id=CONN_SOURCE)
    verifier_schema_source(
        source
    )  # Contrôle 1 : le schéma de la source, avant toute lecture
    lignes = source.get_df(
        """
        SELECT id, client_id, produit, quantite, montant, statut, updated_at
        FROM commandes
        WHERE updated_at > %(repere)s
        ORDER BY updated_at, id
        """,  # Seulement les lignes créées ou modifiées après le repère
        parameters={"repere": repere},
        # Par défaut, Pandas changerait les montants en nombres flottants, donc inexacts
        coerce_float=False,
    )
    if (
        lignes.empty
    ):  # Rien de nouveau : la tâche et celles qui la suivent passent à « skipped »
        JOURNAL.info("aucune_nouvelle_ligne table=%s repere=%s", TABLE, repere)
        raise AirflowSkipException(f"Aucune ligne de {TABLE} modifiée depuis {repere}")
    controler_lot(lignes)  # Contrôle 2 : la qualité du lot, avant toute écriture

    fichier = chemin_parquet(
        run_id, dag_run.run_after.date().isoformat()
    )  # Chemin HDFS du fichier de ce lot
    with (
        tempfile.TemporaryDirectory() as dossier_local
    ):  # Dossier local supprimé à la sortie du bloc
        chemin_local = Path(dossier_local) / "lot.parquet"
        lignes.to_parquet(
            chemin_local, schema=schema_bronze(), index=False
        )  # Écrit avec les types imposés
        octets = (
            chemin_local.stat().st_size
        )  # Taille du fichier, comparée plus tard par controler_bronze
        # Envoi vers HDFS, en remplaçant le fichier d'une tentative précédente
        WebHDFSHook(webhdfs_conn_id=CONN_BRONZE).load_file(
            str(chemin_local), fichier, overwrite=True
        )

    # Bornes du lot ; la dernière devient le nouveau repère
    premiere_maj, derniere_maj = (
        lignes["updated_at"].min().isoformat(),
        lignes["updated_at"].max().isoformat(),
    )
    JOURNAL.info(
        "lot_ecrit table=%s lignes=%s colonnes=%s octets=%s premiere_maj=%s derniere_maj=%s fichier=%s duree_ms=%d",
        TABLE,
        len(lignes),
        lignes.shape[1],
        octets,
        premiere_maj,
        derniere_maj,
        fichier,
        (time.monotonic() - debut) * 1000,
    )
    # Seul un petit résumé passe par XCom, jamais les lignes
    return {
        "table": TABLE,
        "lignes": len(lignes),
        "octets": octets,
        "fichier": fichier,
        "repere": derniere_maj,
    }


# Tâche 3 : relit le fichier écrit sur HDFS et le compare au résumé du lot
@task
def controler_bronze(ti=None) -> None:
    """Relit le fichier : une écriture sans erreur ne prouve pas que les données sont lisibles."""
    import pandas as pd

    lot = ti.xcom_pull(
        task_ids="extraire_vers_bronze"
    )  # Résumé du lot écrit par la tâche précédente
    hook = WebHDFSHook(webhdfs_conn_id=CONN_BRONZE)
    contenu = hook.read_file(
        lot["fichier"]
    )  # Octets du fichier tel qu'il est stocké dans HDFS
    relues = pd.read_parquet(BytesIO(contenu))  # Échoue si le Parquet est illisible
    constate = {
        "lignes": len(relues),
        "octets": len(contenu),
        "repere": relues["updated_at"].max().isoformat(),
    }
    attendu = {
        cle: lot[cle] for cle in constate
    }  # Les mêmes trois valeurs, côté écriture
    if constate != attendu:  # Une différence signale une écriture incomplète ou altérée
        raise ValueError(f"{lot['fichier']} contient {constate}, {attendu} attendu")
    JOURNAL.info(
        "bronze_controle table=%s lignes=%s octets=%s fichier=%s",
        TABLE,
        lot["lignes"],
        lot["octets"],
        lot["fichier"],
    )
    # Pour la classe, avec des données fictives : des lignes réelles n'auraient pas leur place dans un journal
    JOURNAL.info(
        "apercu_bronze table=%s\n%s",
        TABLE,
        relues.head(APERCU_LIGNES).to_string(index=False),
    )
    JOURNAL.info(
        "bronze_contenu dossier=%s\n%s", DOSSIER_BRONZE, decrire_bronze(hook.get_conn())
    )


# Tâche 4 : enregistre le nouveau repère, ce qui clôt l'ingestion de ce lot
@task
def avancer_repere(ti=None) -> None:
    """N'avance qu'après le contrôle : en cas d'échec, la prochaine exécution reprend les mêmes lignes."""
    ancien = ti.xcom_pull(task_ids="lire_repere")  # Gardé pour le journal
    nouveau = ti.xcom_pull(task_ids="extraire_vers_bronze")[
        "repere"
    ]  # Date de la dernière ligne du lot
    publier_repere(WebHDFSHook(webhdfs_conn_id=CONN_BRONZE).get_conn(), nouveau)
    JOURNAL.info("repere_avance table=%s ancien=%s nouveau=%s", TABLE, ancien, nouveau)


# Définition du DAG : paramètres communs à toutes les tâches, puis enchaînement des 4 tâches
with (
    DAG(
        dag_id="ingestion_commandes",
        description="Copie les lignes nouvelles ou modifiées de la table commandes dans la zone bronze de HDFS",
        doc_md=__doc__,  # La docstring du module s'affiche dans l'interface d'Airflow
        start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
        schedule=None,  # Pas de planification : déclenchement manuel
        catchup=False,  # Pas de rattrapage des exécutions passées
        # Deux exécutions simultanées liraient le même repère et écriraient les mêmes lignes deux fois
        max_active_runs=1,
        dagrun_timeout=timedelta(minutes=15),  # Durée maximale d'une exécution complète
        tags=["ingestion", "bronze"],  # Étiquettes de filtrage dans l'interface
        default_args={
            "owner": "projet",  # Responsable affiché dans l'interface
            "retries": 2,  # Nouvelles tentatives en cas d'erreur transitoire (pas pour AirflowFailException)
            "retry_delay": timedelta(
                seconds=10
            ),  # Attente avant la première nouvelle tentative
            "retry_exponential_backoff": True,  # L'attente double à chaque tentative...
            "max_retry_delay": timedelta(minutes=1),  # ...jusqu'à cette limite
            "execution_timeout": timedelta(minutes=3),  # Durée maximale d'une tâche
            "on_failure_callback": signaler_echec,  # Appelé quand une tâche échoue définitivement
        },
    ) as dag
):
    # Chaque appel crée la tâche dans le DAG ; rien ne s'exécute encore
    repere = lire_repere()
    extraire = extraire_vers_bronze()
    controler = controler_bronze()
    avancer = avancer_repere()

    # L'ordre n'est pas libre : extraire a besoin du repère, et le repère n'avance qu'après le contrôle.
    repere >> extraire >> controler >> avancer
