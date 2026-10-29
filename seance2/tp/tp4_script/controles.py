"""Contrôles d'import partagés par les trois ingestions.

Reprenez la fonction check_import écrite dans le TP 1 et découpez-la en deux.
"""

from pathlib import Path

import pandas as pd


class ErreurImport(Exception):
    """Levée dès qu'un contrôle d'import échoue."""


def controler_fichier(path: Path) -> None:
    """Contrôles 1 et 2 : le fichier existe et n'est pas vide. Sinon, lever ErreurImport."""
    raise NotImplementedError("À compléter")


def controler_table(
    df: pd.DataFrame, nom: str, colonnes: list[str], min_lignes: int, types: dict[str, str] | None = None
) -> None:
    """Contrôles 3 à 5 : colonnes attendues, nombre de lignes plausible, types lus.

    `types` associe une colonne au début du nom de type attendu, par exemple {"lat": "float"}.
    """
    raise NotImplementedError("À compléter")
