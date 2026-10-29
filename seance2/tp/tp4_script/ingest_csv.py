"""Ingestion des accidents corporels 2024 (BAAC) : reprenez le code du TP 1 sous forme de fonctions.

Usage : python ingest_csv.py [--force]
"""

import argparse
from pathlib import Path

import pandas as pd
import requests

from controles import ErreurImport, controler_fichier, controler_table  # noqa: F401

TP_DIR = Path(__file__).resolve().parent.parent
RAW = TP_DIR / "data" / "raw" / "accidents_2024"
CLEAN = TP_DIR / "data" / "clean" / "accidents"

BASE = (
    "https://static.data.gouv.fr/resources/bases-de-donnees-annuelles-des-accidents-corporels-de-la-"
    "circulation-routiere-annees-de-2005-a-2024"
)
URLS = {
    "caract-2024.csv": f"{BASE}/20251021-115900/caract-2024.csv",
    "lieux-2024.csv": f"{BASE}/20251021-115812/lieux-2024.csv",
    "vehicules-2024.csv": f"{BASE}/20251107-100240/vehicules-2024.csv",
    "usagers-2024.csv": f"{BASE}/20251021-115506/usagers-2024.csv",
}


def telecharger(nom: str, url: str, session: requests.Session, force: bool = False) -> Path:
    """Déposer le fichier dans RAW, sauf s'il y est déjà (et que force est faux). Renvoyer son chemin."""
    raise NotImplementedError("À compléter")


def lire_caract(path: Path) -> pd.DataFrame:
    """Lecture explicite des caractéristiques, colonne date_heure, puis contrôles d'import."""
    raise NotImplementedError("À compléter")


def lire_usagers(path: Path) -> pd.DataFrame:
    """Lecture explicite des usagers, types réduits, puis contrôles d'import."""
    raise NotImplementedError("À compléter")


def ingest(force: bool = False) -> dict:
    """Télécharger, lire, vérifier que chaque usager se rattache à un accident, écrire en Parquet dans CLEAN.

    Fichiers attendus : caract.parquet et usagers.parquet. Renvoyer {"source": ..., "lignes": ...}.
    """
    raise NotImplementedError("À compléter")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="retélécharger les fichiers déjà présents")
    print(ingest(parser.parse_args().force))
