"""Lance les trois ingestions dans l'ordre et affiche un compte rendu.

Copiez d'abord votre ingest_postgres.py du TP 3 dans ce dossier.

Usage : python run_all.py
"""

import sys


def main() -> int:
    """Pour chaque source (CSV, puis API, puis PostgreSQL en mode incrémental) :
    mesurer la durée, attraper l'erreur éventuelle sans arrêter les autres sources,
    afficher une ligne « source, lignes, durée, statut ». Renvoyer 1 si une source a échoué, 0 sinon.
    """
    raise NotImplementedError("À compléter")


if __name__ == "__main__":
    sys.exit(main())
