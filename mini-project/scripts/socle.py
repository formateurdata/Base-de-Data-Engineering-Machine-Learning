"""Socle technique des scripts du projet : configuration, connexion à la base et journaux structurés."""

import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

HERE = Path(__file__).resolve().parent.parent
load_dotenv(HERE / ".env")

HOTE = "127.0.0.1"
BASE = "boutique"
DELAI_CONNEXION_S = 5
INDICES_SECRET = ("password", "mot_de_passe", "secret", "token", "jeton")


class ErreurConfiguration(Exception):
    """Une variable de .env manque ou n'a pas une valeur utilisable."""


def lire_secret(nom: str) -> str:
    valeur = os.environ.get(nom)
    if not valeur:
        raise ErreurConfiguration(f"{nom} absent : complétez .env à partir de .env.example")
    return valeur


def lire_port(nom: str, defaut: int) -> int:
    valeur = os.environ.get(nom, str(defaut))
    if not valeur.isdigit() or not 1 <= int(valeur) <= 65_535:
        raise ErreurConfiguration(f"{nom} doit être un numéro de port entre 1 et 65535")
    return int(valeur)


def creer_moteur(utilisateur: str, variable_mot_de_passe: str, application: str) -> Engine:
    """Connexion à la base source. application_name permet de reconnaître le script dans pg_stat_activity."""
    return create_engine(
        URL.create(
            "postgresql+psycopg",
            username=utilisateur,
            password=lire_secret(variable_mot_de_passe),
            host=HOTE,
            port=lire_port("PG_PORT", 5434),
            database=BASE,
        ),
        connect_args={"connect_timeout": DELAI_CONNEXION_S, "application_name": application},
    )


def diagnostiquer_connexion(erreur: OperationalError) -> tuple[str, str]:
    """Renvoie l'événement à journaliser et ce que la personne doit faire."""
    if "password authentication failed" in str(erreur.orig):
        return (
            "authentification_refusee",
            "Mot de passe refusé : si .env a changé depuis la création de la base, "
            "lancez make reset (efface les données) puis make up",
        )
    return "base_injoignable", "Base injoignable : lancez make up et vérifiez .env"


class FormatJson(logging.Formatter):
    """Une ligne JSON par événement, en UTC, avec les champs passés par extra={"champs": {...}}."""

    def format(self, record: logging.LogRecord) -> str:
        ligne = {
            "horodatage": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "niveau": record.levelname,
            "journal": record.name,
            "evenement": record.getMessage(),
        }
        for cle, valeur in getattr(record, "champs", {}).items():
            ligne[cle] = "***" if any(indice in cle.lower() for indice in INDICES_SECRET) else valeur
        if record.exc_info:
            type_erreur, erreur, _ = record.exc_info
            ligne["exception"] = f"{type_erreur.__name__}: {erreur}"
        return json.dumps(ligne, ensure_ascii=False, default=str)


def configurer_journaux() -> None:
    sortie = logging.StreamHandler(sys.stdout)
    sortie.setFormatter(FormatJson())
    logging.basicConfig(level=logging.INFO, handlers=[sortie], force=True)
