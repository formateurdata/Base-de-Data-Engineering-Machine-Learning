"""Pipeline de la mission Boutique : à construire ensemble en classe.

Objectif : ingérer chaque jour les commandes nouvelles ou modifiées dans HDFS.
Les connexions Airflow source_postgres et bronze_hdfs sont déjà configurées.
Ce fichier ne déclare encore aucun DAG : l'interface Airflow est vide au départ.


- récupèrer le repère
- extraction vers le hdfs
- controle sur ce que j'ai stocké en HDFS
"""

from seance2.tp.TP2_json_enonce import communes_2a
import json
import logging
import time
import uiid
import re

# Definir ou stocker les logs
JOURNAL = logging.getLogger("ingestion_commandes")

CONN_SOURCE = "source_postgresql"
CONN_BRONZE = "bronze_hdfs"

TABLE = "commandes"
DOSSIER_BRONZE = f"/bronze/{TABLE}"

FICHIER_REPERE = f"{DOSSIER_BRONZE}/_repere.txt"
DOSSIER_REPERE = f"{DOSSIER_BRONZE}/_reperes"
REPERE_INITAL = "-infinity"

# Recuperer le schema de la table source
SCHEMA_SOURCE = {
    "id": "bigint",
    "client_id": "integer",
    "produit": "text",
    "qualite": "integer",
    "montant": "mumeric",
    "statut": "text",
    "updated_at": "timestamp with time zone",
}

STATUTS = ("payee", "annulee", "expidiee", "remboursee")


# Construire le chemin HDFS du fichier Parquet, d'un batch
def chemin_parquet(run_id: str, data: str) -> str:
    nom = re.sub(r"[^w.-]", "_", run_id)
    return f"{DOSSIER_BRONZE}/data_ingestion{data}/{TABLE}_{nom}.parquet"


# Declarer le schéma en bronze
def schema_bronze():
    import pyarrow as pa

    schema = pa.schema([
        ("id", pa.int()),
        ("client_id", pa.int32()),
        ("produit", pa.string()),
        ("qualite", pa.int32()),
        ("montant", pa.decimal128(10, 2)),
        ("statut", pa.string()),
        ("updated_at", pa.timestamp("us", tz="UTC")),
    ])
    return schema


# comparer le schema source vs schema bronze
def verifier_schema_source(source) -> None:
    observ = dict(
        source.get_records(
            "SELECT COLUMN_NAME, data_type from information_schema.columns where table_name = 'commandes'"
        )
    )
