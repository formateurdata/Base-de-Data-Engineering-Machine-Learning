"""TP 3 : ingestion des locations de la base Pagila (PostgreSQL), en mode complet ou incrémental.

Complétez les fonctions marquées « À compléter », dans l'ordre. Lancez ensuite :
  python ingest_postgres.py                  (mode complet)
  python ingest_postgres.py --incremental    (ne relit que les lignes modifiées)
"""

import argparse
import json  # noqa: F401
import os  # noqa: F401
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text  # noqa: F401
from sqlalchemy.engine import Engine

TP_DIR = Path(__file__).resolve().parent.parent
CLEAN = TP_DIR / "data" / "clean" / "pagila"
SORTIE = CLEAN / "locations.parquet"
ETAT = TP_DIR / "data" / "state" / "pagila.json"
DEBUT = "1900-01-01"

# À compléter (étape 2) : une seule requête, paramétrée, qui renvoie une ligne par location avec
#   rental_id, customer_id, store_id (table inventory), film_id, title et rental_rate (table film),
#   rental_date = lower(rental_period), return_date = upper(rental_period), last_update,
# et seulement les lignes dont last_update est postérieur au paramètre :repere.
REQUETE = text("""
    SELECT 1
""")


def connecter() -> Engine:
    """Étape 1 : créer l'engine SQLAlchemy à partir des variables de tp3_postgres/.env.

    URL attendue : postgresql+psycopg://utilisateur:mot_de_passe@hôte:port/base
    Aucun identifiant ne doit apparaître en clair dans ce fichier.
    """
    load_dotenv(TP_DIR / "tp3_postgres" / ".env")
    raise NotImplementedError("À compléter")


def lire_repere() -> str:
    """Étape 4 : renvoyer le dernier last_update stocké dans ETAT, ou DEBUT si le fichier n'existe pas."""
    raise NotImplementedError("À compléter")


def extraire(engine: Engine, repere: str, taille: int = 5_000) -> pd.DataFrame:
    """Étape 3 : exécuter REQUETE avec pd.read_sql, par morceaux de `taille` lignes (chunksize).

    Renvoyer un seul DataFrame, éventuellement vide.
    """
    raise NotImplementedError("À compléter")


def ingest(incremental: bool = False) -> dict:
    """Étape 5 : assembler.

    - mode complet : tout relire et écrire SORTIE ;
    - mode incrémental : relire depuis le repère, fusionner avec SORTIE sans créer de doublon
      sur rental_id (la version la plus récente gagne) ;
    - enregistrer le nouveau repère dans ETAT ;
    - renvoyer {"source": ..., "lignes": ..., "lues": ...}.
    """
    raise NotImplementedError("À compléter")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--incremental", action="store_true", help="ne relire que les lignes modifiées")
    print(ingest(parser.parse_args().incremental))
