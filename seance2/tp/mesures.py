"""Mesures de vitesse et de mémoire citées dans les slides de la séance 2.

Chaque mesure de temps garde le meilleur de cinq essais. Le résultat est écrit dans
mesures.json, relu par slides/build/seance2.py : les chiffres projetés sont donc ceux
de la dernière exécution.

Usage, depuis seance2/tp :
  python mesures.py            (fichiers CSV seulement)
  python mesures.py --sql      (ajoute les mesures PostgreSQL, base du TP 3 démarrée)
"""

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import pandas as pd
import polars as pl

HERE = Path(__file__).parent
RAW = HERE / "data" / "raw" / "accidents_2024"
USAGERS = RAW / "usagers-2024.csv"

CODES = ["place", "catu", "grav", "sexe", "trajet", "secu1", "secu2", "secu3", "locp", "etatp"]
USAGERS_DTYPES = {"Num_Acc": "str", "id_usager": "str", "id_vehicule": "str", "num_veh": "str",
                  "actp": "category", "an_nais": "Int16"} | {c: "Int8" for c in CODES}
UTILES = ["Num_Acc", "id_vehicule", "catu", "grav", "sexe", "an_nais", "trajet", "secu1"]


def best_of(fn, repeat=5):
    times = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return min(times)


def mo(df):
    return round(df.memory_usage(deep=True).sum() / 1e6, 1)


def csv_measures(tmp):
    implicite = lambda: pd.read_csv(USAGERS, sep=";")
    explicite = lambda: pd.read_csv(USAGERS, sep=";", dtype=USAGERS_DTYPES, na_values=["-1", " -1"])
    reduite = lambda: pd.read_csv(USAGERS, sep=";", usecols=UTILES,
                                  dtype={k: v for k, v in USAGERS_DTYPES.items() if k in UTILES},
                                  na_values=["-1", " -1"])
    arrow = lambda: pd.read_csv(USAGERS, sep=";", dtype=USAGERS_DTYPES, na_values=["-1", " -1"], engine="pyarrow")

    df = explicite()
    parquet = tmp / "usagers.parquet"
    df.to_parquet(parquet, index=False)

    return {
        "lignes": len(df),
        "taille_csv_mo": round(USAGERS.stat().st_size / 1e6, 1),
        "taille_parquet_mo": round(parquet.stat().st_size / 1e6, 1),
        "memoire_implicite_mo": mo(implicite()),
        "memoire_explicite_mo": mo(df),
        "memoire_reduite_mo": mo(reduite()),
        "temps_implicite_s": round(best_of(implicite), 3),
        "temps_explicite_s": round(best_of(explicite), 3),
        "temps_reduite_s": round(best_of(reduite), 3),
        "temps_pyarrow_s": round(best_of(arrow), 3),
        "temps_parquet_s": round(best_of(lambda: pd.read_parquet(parquet)), 3),
        "temps_polars_s": round(best_of(lambda: pl.read_csv(USAGERS, separator=";")), 3),
    }


def loop_measures():
    """Âge de chaque usager au moment de l'accident : boucle, apply, puis vectorisé."""
    df = pd.read_csv(USAGERS, sep=";", dtype=USAGERS_DTYPES, na_values=["-1", " -1"])

    def boucle():
        ages = []
        for _, row in df.iterrows():
            ages.append(2024 - row["an_nais"])
        return ages

    return {
        "lignes": len(df),
        "temps_iterrows_s": round(best_of(boucle, repeat=3), 3),
        "temps_apply_s": round(best_of(lambda: df.apply(lambda r: 2024 - r["an_nais"], axis=1), repeat=3), 3),
        "temps_vectorise_s": round(best_of(lambda: 2024 - df["an_nais"]), 6),
    }


def sql_measures():
    """Mêmes requêtes que la correction du TP 3 (corrections/optimiser_postgres.py)."""
    sys.path.insert(0, str(HERE / "corrections"))
    from optimiser_postgres import connecter, filtre_pandas, filtre_sql

    engine = connecter()
    gardees, transfere = filtre_pandas(engine)
    _, cible = filtre_sql(engine)
    return {
        "lignes_transferees_select_etoile": len(transfere),
        "colonnes_select_etoile": transfere.shape[1],
        "memoire_select_etoile_mo": mo(transfere),
        "lignes_gardees": len(gardees),
        "lignes_transferees_filtre_sql": len(cible),
        "memoire_filtre_sql_mo": mo(cible),
        "temps_filtre_pandas_s": round(best_of(lambda: filtre_pandas(engine)), 3),
        "temps_filtre_sql_s": round(best_of(lambda: filtre_sql(engine)), 3),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql", action="store_true", help="ajoute les mesures sur la base PostgreSQL du TP 3")
    args = parser.parse_args()

    tmp = HERE / "data" / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    result = {
        "machine": f"{platform.machine()}, {platform.system()} {platform.release()}, Python {platform.python_version()}",
        "versions": {"pandas": pd.__version__, "polars": pl.__version__},
        "csv": csv_measures(tmp),
        "boucles": loop_measures(),
    }
    if args.sql:
        result["sql"] = sql_measures()
    (HERE / "mesures.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
