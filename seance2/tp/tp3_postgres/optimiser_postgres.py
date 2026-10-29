"""TP 3, partie optimisation : filtrer dans Pandas ou filtrer dans la base ?

Les deux fonctions renvoient le même résultat : les locations à partir du 1er août 2005,
avec le titre et le tarif du film. On compare le temps, ainsi que les lignes et la mémoire transférées depuis la base.

Usage : python optimiser_postgres.py
"""

import time

import pandas as pd
from sqlalchemy import text  # noqa: F401

from ingest_postgres import connecter

COLONNES = ["rental_id", "customer_id", "title", "rental_rate", "rental_date"]
DEPUIS = "2005-08-01"


def filtre_pandas(engine) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Tout transférer, puis filtrer et choisir les colonnes dans Pandas."""
    brut = pd.read_sql(
        "SELECT * FROM rental r JOIN inventory i USING (inventory_id) JOIN film f USING (film_id)", engine
    )
    brut["rental_date"] = brut["rental_period"].map(lambda periode: periode.lower)
    return brut.loc[brut["rental_date"] >= pd.Timestamp(DEPUIS), COLONNES], brut


def filtre_sql(engine) -> tuple[pd.DataFrame, pd.DataFrame]:
    """À compléter : même résultat que filtre_pandas, mais filtre, jointure et colonnes dans la requête.

    Utilisez une requête paramétrée (:depuis) et renvoyez (résultat, données transférées).
    """
    raise NotImplementedError("À compléter")


if __name__ == "__main__":
    engine = connecter()
    print(f"{'Méthode':<14}{'Transférées':>12}{'Gardées':>9}{'Mémoire':>10}{'Temps':>9}")
    for nom, methode in [("Pandas", filtre_pandas), ("SQL", filtre_sql)]:
        debut = time.perf_counter()
        resultat, transfere = methode(engine)
        duree = time.perf_counter() - debut
        memoire = transfere.memory_usage(deep=True).sum() / 1e6
        print(f"{nom:<14}{len(transfere):>12}{len(resultat):>9}{memoire:>8.1f}Mo{duree:>8.3f}s")
