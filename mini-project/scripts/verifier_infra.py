"""Vérifie que l'infrastructure du projet répond et respecte ses règles de sécurité. Fichier fourni, à ne pas modifier.

Usage depuis la racine du projet : make verify
Code de sortie : 0 si tout est conforme, 1 s'il reste un écart.
"""

import json
import os
import sys
from collections.abc import Callable

import requests
from dotenv import dotenv_values
from psycopg.errors import InsufficientPrivilege, ReadOnlySqlTransaction
from socle import HERE, HOTE, ErreurConfiguration, creer_moteur, diagnostiquer_connexion, lire_port
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, OperationalError

EXEMPLE = HERE / ".env.example"
SECRETS = (
    "POSTGRES_PASSWORD",
    "LECTEUR_PASSWORD",
    "GENERATEUR_PASSWORD",
    "AIRFLOW_DB_PASSWORD",
    "AIRFLOW_ADMIN_PASSWORD",
)
DELAI_HTTP_S = 5
# WHERE false : les droits sont contrôlés sans qu'aucune ligne puisse changer, même si le contrôle échoue
ECRITURE_LECTEUR = (
    "INSERT INTO commandes (client_id, produit, quantite, montant, statut) SELECT 1, 'x', 1, 1, 'payee' WHERE false"
)
ECRITURE_GENERATEUR = "DELETE FROM commandes WHERE false"


def verifier_secrets() -> list[str]:
    exemple = dotenv_values(EXEMPLE)
    ecarts = []
    for nom in SECRETS:
        valeur = os.environ.get(nom)
        if not valeur:
            ecarts.append(f"{nom} absent")
        elif valeur == exemple.get(nom):
            ecarts.append(f"{nom} garde sa valeur d'exemple")
        elif not (valeur.isascii() and valeur.isalnum()):
            # Ces mots de passe entrent tels quels dans une URL et dans le JSON de la connexion Airflow
            ecarts.append(f"{nom} doit contenir uniquement des lettres sans accent et des chiffres")
    return ecarts


def ecriture_refusee(moteur: Engine, requete: str) -> bool:
    with moteur.connect() as conn:
        try:
            conn.execute(text(requete))
        except DBAPIError as erreur:
            if isinstance(erreur.orig, InsufficientPrivilege | ReadOnlySqlTransaction):
                return True
            raise
        conn.rollback()
    return False


def verifier_source() -> list[str]:
    try:
        lecteur = creer_moteur("lecteur", "LECTEUR_PASSWORD", "verifier_infra")
        generateur = creer_moteur("generateur", "GENERATEUR_PASSWORD", "verifier_infra")
        with lecteur.connect() as conn:
            conn.execute(text("SELECT count(*) FROM commandes"))
        ecarts = []
        if not ecriture_refusee(lecteur, ECRITURE_LECTEUR):
            ecarts.append("lecteur peut écrire")
        if not ecriture_refusee(generateur, ECRITURE_GENERATEUR):
            ecarts.append("generateur peut supprimer")
    except ErreurConfiguration as erreur:
        return [str(erreur)]
    except OperationalError as erreur:
        return [diagnostiquer_connexion(erreur)[1]]
    except DBAPIError as erreur:
        return [str(erreur.orig).strip()]
    lecteur.dispose()
    generateur.dispose()
    return ecarts


def verifier_hdfs() -> list[str]:
    base = f"http://{HOTE}:{lire_port('HDFS_UI_PORT', 9870)}"
    try:
        reponse = requests.get(
            f"{base}/jmx", params={"qry": "Hadoop:service=NameNode,name=NameNodeInfo"}, timeout=DELAI_HTTP_S
        )
        reponse.raise_for_status()
        info = reponse.json()["beans"][0]
        bronze = requests.get(f"{base}/webhdfs/v1/bronze", params={"op": "GETFILESTATUS"}, timeout=DELAI_HTTP_S)
    except (requests.RequestException, IndexError, KeyError):
        return ["NameNode injoignable"]

    ecarts = []
    if info["Safemode"]:
        ecarts.append("NameNode en safe mode")
    noeuds = len(json.loads(info["LiveNodes"]))
    if noeuds != 1:
        ecarts.append(f"{noeuds} DataNode actif, 1 attendu")
    if bronze.status_code != 200:
        ecarts.append("dossier /bronze absent")
        return ecarts
    statut = bronze.json()["FileStatus"]
    if statut["owner"] != "airflow":
        ecarts.append("/bronze n'appartient pas à airflow")
    if statut["permission"] != "750":
        ecarts.append(f"/bronze en droits {statut['permission']}, 750 attendu")
    return ecarts


def verifier_airflow() -> list[str]:
    base = f"http://{HOTE}:{lire_port('AIRFLOW_PORT', 8081)}"
    try:
        reponse = requests.get(f"{base}/api/v2/monitor/health", timeout=DELAI_HTTP_S)
        reponse.raise_for_status()
        sante = reponse.json()
        ecarts = [
            f"{composant} n'est pas sain"
            for composant in ("metadatabase", "scheduler", "dag_processor")
            if sante.get(composant, {}).get("status") != "healthy"
        ]
        jeton = requests.post(
            f"{base}/auth/token",
            json={"username": "admin", "password": os.environ.get("AIRFLOW_ADMIN_PASSWORD", "")},
            timeout=DELAI_HTTP_S,
        )
        if jeton.status_code >= 400:
            ecarts.append("connexion admin refusée : vérifiez AIRFLOW_ADMIN_PASSWORD")
            return ecarts
        erreurs = requests.get(
            f"{base}/api/v2/importErrors",
            headers={"Authorization": f"Bearer {jeton.json()['access_token']}"},
            timeout=DELAI_HTTP_S,
        )
        erreurs.raise_for_status()
        if erreurs.json()["total_entries"]:
            ecarts.append(f"{erreurs.json()['total_entries']} DAG en erreur d'import")
    except requests.RequestException:
        return ["Airflow injoignable"]
    return ecarts


VERIFICATIONS: dict[str, Callable[[], list[str]]] = {
    "secrets": verifier_secrets,
    "source": verifier_source,
    "hdfs": verifier_hdfs,
    "airflow": verifier_airflow,
}


if __name__ == "__main__":
    total = 0
    for nom, verifier in VERIFICATIONS.items():
        ecarts = verifier()
        total += len(ecarts)
        print(f"{nom:<8} {'OK' if not ecarts else ' ; '.join(ecarts)}")
    sys.exit(1 if total else 0)
