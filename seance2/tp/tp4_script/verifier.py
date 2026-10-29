"""Relit les fichiers Parquet produits par les ingestions et signale les écarts. Fichier fourni, à ne pas modifier.

Usage : python verifier.py
"""

import sys
from pathlib import Path

import pandas as pd

CLEAN = Path(__file__).resolve().parent.parent / "data" / "clean"

# fichier : (lignes minimum, clé unique, {colonne: début du type attendu})
ATTENDUS = {
    "accidents/caract.parquet": (
        50_000,
        "Num_Acc",
        {"Num_Acc": "str", "dep": "str", "com": "str", "lat": "float", "long": "float", "date_heure": "datetime64"},
    ),
    "accidents/usagers.parquet": (100_000, "id_usager", {"Num_Acc": "str", "grav": "Int8", "an_nais": "Int16"}),
    "api_geo/communes.parquet": (
        30_000,
        "code",
        {"code": "str", "dep": "str", "population": "Int64", "lon": "float", "lat": "float"},
    ),
    "pagila/locations.parquet": (
        16_000,
        "rental_id",
        {"rental_id": "int", "title": "str", "rental_date": "datetime64", "last_update": "datetime64"},
    ),
}


def verifier(nom: str, min_lignes: int, cle: str, types: dict[str, str]) -> list[str]:
    path = CLEAN / nom
    if not path.exists():
        return ["fichier absent"]
    df = pd.read_parquet(path)
    ecarts = []
    if len(df) < min_lignes:
        ecarts.append(f"{len(df)} lignes, au moins {min_lignes} attendues")
    for colonne, attendu in types.items():
        if colonne not in df.columns:
            ecarts.append(f"colonne {colonne} absente")
        elif not str(df[colonne].dtype).startswith(attendu):
            ecarts.append(f"{colonne} en {df[colonne].dtype}, {attendu} attendu")
    if cle in df.columns and df[cle].duplicated().any():
        ecarts.append(f"{df[cle].duplicated().sum()} doublons sur {cle} : l'ingestion n'est pas idempotente")
    return ecarts


if __name__ == "__main__":
    total = 0
    for nom, (min_lignes, cle, types) in ATTENDUS.items():
        ecarts = verifier(nom, min_lignes, cle, types)
        total += len(ecarts)
        print(f"{nom:<28} {'OK' if not ecarts else ' ; '.join(ecarts)}")
    sys.exit(1 if total else 0)
