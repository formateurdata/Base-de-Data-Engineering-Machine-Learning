"""Ingestion des communes depuis l'API Géo : reprenez le code du TP 2 sous forme de fonctions.

Usage : python ingest_api.py [--date AAAA-MM-JJ]
"""

import argparse
from datetime import date  # noqa: F401
from pathlib import Path

import pandas as pd
import requests

from controles import ErreurImport, controler_fichier, controler_table  # noqa: F401

TP_DIR = Path(__file__).resolve().parent.parent
RAW = TP_DIR / "data" / "raw" / "api_geo"
CLEAN = TP_DIR / "data" / "clean" / "api_geo"
CARACT = TP_DIR / "data" / "clean" / "accidents" / "caract.parquet"

API = "https://geo.api.gouv.fr/communes"
CHAMPS = "nom,code,codeDepartement,population,centre,codesPostaux,type"
TYPES = "commune-actuelle,arrondissement-municipal"


def appeler(session: requests.Session, departement: str) -> list[dict]:
    """Un appel à l'API pour un département, avec timeout et vérification du code HTTP."""
    raise NotImplementedError("À compléter")


def extraire(departements: list[str], dossier: Path, pause: float = 0.1) -> list[Path]:
    """Sauvegarder une réponse brute par département dans `dossier`, sans rappeler l'API si elle y est déjà."""
    raise NotImplementedError("À compléter")


def aplatir(paths: list[Path]) -> pd.DataFrame:
    """Une ligne par commune : colonnes code, nom, dep, population (Int64), type, codes_postaux, lon, lat."""
    raise NotImplementedError("À compléter")


def ingest(jour: str | None = None) -> dict:
    """Départements lus dans CARACT, extraction, aplatissement, contrôles, écriture de communes.parquet."""
    raise NotImplementedError("À compléter")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--date", help="dossier de la zone brute à utiliser, par défaut aujourd'hui")
    print(ingest(parser.parse_args().date))
