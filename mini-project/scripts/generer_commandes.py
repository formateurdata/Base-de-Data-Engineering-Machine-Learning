"""Génère des commandes fictives dans la base source : 1000 lignes si la table est vide, 500 lignes sinon.

Usage depuis la racine du projet : make generate
Code de sortie : 0 si le lot est inséré, 1 si la base refuse ou ne répond pas, 2 si .env est incomplet.
"""

import logging
import random
import sys
import time
import uuid
from decimal import Decimal

from socle import ErreurConfiguration, configurer_journaux, creer_moteur, diagnostiquer_connexion
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

JOURNAL = logging.getLogger("generer_commandes")

TAILLE_INITIALE = 1_000
TAILLE_LOT = 500
STATUTS = ["payee", "expediee", "annulee", "remboursee"]
POIDS_STATUTS = [50, 35, 10, 5]
PRIX = {
    "clavier": Decimal("49.90"),
    "souris": Decimal("24.50"),
    "ecran": Decimal("189.00"),
    "casque": Decimal("79.99"),
    "webcam": Decimal("59.00"),
    "station d'accueil": Decimal("129.00"),
}
NB_CLIENTS = 200

INSERTION = text("""
    INSERT INTO commandes (client_id, produit, quantite, montant, statut)
    VALUES (:client_id, :produit, :quantite, :montant, :statut)
""")


def connecter() -> Engine:
    """Connexion avec le rôle generateur, qui peut seulement lire et insérer."""
    return creer_moteur("generateur", "GENERATEUR_PASSWORD", "generer_commandes")


def taille_du_lot(deja_presentes: int) -> int:
    return TAILLE_INITIALE if deja_presentes == 0 else TAILLE_LOT


def generer_lignes(n: int, rng: random.Random) -> list[dict]:
    lignes = []
    for _ in range(n):
        produit = rng.choice(list(PRIX))
        quantite = rng.randint(1, 5)
        lignes.append(
            {
                "client_id": rng.randint(1, NB_CLIENTS),
                "produit": produit,
                "quantite": quantite,
                "montant": PRIX[produit] * quantite,
                "statut": rng.choices(STATUTS, weights=POIDS_STATUTS)[0],
            }
        )
    return lignes


def generer(engine: Engine, rng: random.Random | None = None) -> dict:
    """Insère un lot en une seule transaction : en cas d'échec, aucune ligne du lot n'est conservée."""
    debut = time.perf_counter()
    with engine.begin() as conn:
        # Un seul générateur à la fois, libéré à la fin de la transaction ; les lectures ne sont pas bloquées
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtext('generer_commandes'))"))
        deja_presentes = conn.execute(text("SELECT count(*) FROM commandes")).scalar_one()
        # Données fictives : un générateur non cryptographique convient
        lignes = generer_lignes(taille_du_lot(deja_presentes), rng or random.Random())  # noqa: S311
        conn.execute(INSERTION, lignes)
    resultat = {"table": "commandes", "inserees": len(lignes), "total": deja_presentes + len(lignes)}
    champs = resultat | {"lot_id": str(uuid.uuid4()), "duree_ms": round((time.perf_counter() - debut) * 1000)}
    JOURNAL.info("lot_insere", extra={"champs": champs})
    return resultat


def main() -> int:
    configurer_journaux()
    try:
        generer(connecter())
    except ErreurConfiguration as erreur:
        JOURNAL.error("configuration_invalide", extra={"champs": {"message": str(erreur)}})
        return 2
    except OperationalError as erreur:
        evenement, message = diagnostiquer_connexion(erreur)
        JOURNAL.error(evenement, extra={"champs": {"message": message}})
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
