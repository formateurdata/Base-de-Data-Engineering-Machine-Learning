"""Génère les notebooks des TP 1 et 2, énoncé et correction, à partir d'une seule description.

Chaque cellule est l'un de :
  ("md", texte)                cellule de texte, identique dans les deux versions
  ("code", source)             cellule de code fournie, identique dans les deux versions
  ("ex", solution, squelette)  exercice : la solution dans la correction, le squelette dans l'énoncé
  ("rep", texte)               réponse à une question : dans la correction seulement

Usage, depuis seance2/tp : python build_notebooks.py
"""

import json
from pathlib import Path

HERE = Path(__file__).parent
A_COMPLETER = "*Votre réponse :*"


def notebook(cells, solution):
    out = []
    for cell in cells:
        kind = cell[0]
        if kind == "md":
            out.append(("markdown", cell[1]))
        elif kind == "code":
            out.append(("code", cell[1]))
        elif kind == "ex":
            out.append(("code", cell[1] if solution else cell[2]))
        elif kind == "rep":
            out.append(("markdown", "**Réponse.** " + cell[1] if solution else A_COMPLETER))
    return {
        "cells": [
            {"cell_type": t, "metadata": {}, "source": s.strip("\n").splitlines(keepends=True)}
            | ({"execution_count": None, "outputs": []} if t == "code" else {})
            for t, s in out
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def write(name, cells):
    for suffix, solution in [("enonce", False), ("correction", True)]:
        path = HERE / f"{name}_{suffix}.ipynb"
        path.write_text(json.dumps(notebook(cells, solution), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(path.name)


# ----------------------------------------------------------------------------
# TP 1 : CSV

TP1 = [
    ("md", """
# TP 1 : ingérer un CSV réel, les accidents corporels de 2024

**Durée : 35 minutes, en binôme.**

Les données sont celles de l'Observatoire national interministériel de la sécurité routière (ONISR), publiées sur
[data.gouv.fr](https://www.data.gouv.fr/datasets/bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2024)
sous Licence Ouverte. Chaque année comporte quatre fichiers reliés par l'identifiant d'accident `Num_Acc` :
caractéristiques, lieux, véhicules et usagers. La description des colonnes est sur la page du jeu de données.

À la fin du TP, vous saurez :
- déposer un fichier dans la zone brute sans le retélécharger à chaque exécution ;
- lire un CSV avec des paramètres explicites, et vérifier que les types lus sont les bons ;
- écrire des contrôles d'import qui refusent un fichier défectueux ;
- mesurer et réduire le temps de lecture et la mémoire occupée.

Après chaque exercice, une cellule `assert` vérifie votre résultat. Si elle ne lève pas d'erreur, passez à la suite.
Tant qu'un exercice n'est pas rempli, il s'arrête sur le message « Exercice à compléter ».
"""),
    ("code", """
import time
from pathlib import Path

import pandas as pd
import requests

RAW = Path("data/raw/accidents_2024")
CLEAN = Path("data/clean/accidents")
TMP = Path("data/tmp")
TMP.mkdir(parents=True, exist_ok=True)

BASE = (
    "https://static.data.gouv.fr/resources/bases-de-donnees-annuelles-des-accidents-corporels-de-la-"
    "circulation-routiere-annees-de-2005-a-2024"
)
URL_CARACT = f"{BASE}/20251021-115900/caract-2024.csv"
print("pandas", pd.__version__)


# Appelée par les cellules d'exercice tant que vous ne les avez pas remplies
def a_completer():
    raise NotImplementedError("Exercice à compléter : remplacez a_completer() par votre code")
"""),
    ("md", """
## Partie 1 : déposer le fichier dans la zone brute (5 min)

Écrivez `telecharger(url, dest)` :
- si `dest` existe déjà, ne rien faire et renvoyer `dest` : relancer le notebook ne doit pas retélécharger ;
- sinon, télécharger avec `requests.get`, **avec un `timeout`**, et lever une erreur si le code HTTP n'est pas 200
  (`raise_for_status`) ;
- créer le dossier si besoin, écrire le contenu, renvoyer `dest`.

Une copie des quatre fichiers est déjà dans `data/raw/accidents_2024` : la fonction ne retéléchargera donc rien là.
Pour vérifier qu'elle télécharge vraiment, on l'appelle sur un dossier de test.
"""),
    ("ex", """
def telecharger(url: str, dest: Path, timeout: int = 60) -> Path:
    if dest.exists():
        return dest
    reponse = requests.get(url, timeout=timeout)
    reponse.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(reponse.content)
    return dest
""", """
def telecharger(url: str, dest: Path, timeout: int = 60) -> Path:
    a_completer()  # À compléter
"""),
    ("code", """
try:
    essai = telecharger(URL_CARACT, TMP / "telechargement" / "caract-2024.csv")
    assert essai.stat().st_size == (RAW / "caract-2024.csv").stat().st_size
    print("Téléchargement vérifié :", essai)
except requests.RequestException as erreur:
    print("Pas de réseau, on continue avec la copie locale :", erreur)

assert telecharger(URL_CARACT, RAW / "caract-2024.csv") == RAW / "caract-2024.csv"
"""),
    ("md", """
## Partie 2 : lire les caractéristiques des accidents (12 min)

### 2.1 La lecture naïve
"""),
    ("code", """
try:
    pd.read_csv(RAW / "caract-2024.csv")
except Exception as erreur:
    print(type(erreur).__name__, ":", erreur)
"""),
    ("md", "Avant de changer un paramètre au hasard, on regarde le fichier brut."),
    ("code", """
print((RAW / "caract-2024.csv").read_text(encoding="utf-8")[:500])
"""),
    ("md", "**Question.** Pourquoi la lecture naïve échoue-t-elle à la ligne 618 seulement, et pas dès la première ?"),
    ("rep", """
Sans `sep`, pandas coupe sur les virgules. La première ligne n'en contient aucune : pandas croit à une seule colonne.
Les coordonnées s'écrivent avec une virgule décimale (`47,56277000`) : chaque ligne de données en contient deux,
d'où trois champs. La ligne 618, à Tahiti, contient une virgule de plus dans l'adresse
(`Avenue Aratia Nelson Mandela,`) : le nombre de champs change et pandas abandonne. Le séparateur réel est le
point-virgule.
"""),
    ("md", "### 2.2 Le séparateur seul ne suffit pas"),
    ("code", """
pd.read_csv(RAW / "caract-2024.csv", sep=";").dtypes
"""),
    ("md", "**Question.** Citez trois colonnes dont le type lu ne convient pas, et dites pourquoi."),
    ("rep", """
`lat` et `long` sont lues en texte à cause de la virgule décimale. `Num_Acc` est lu en entier alors que c'est un
identifiant : on ne fait pas de calcul dessus, il se lit en texte. Les codes comme `col` contiennent `-1`, qui
signifie « non renseigné » dans la documentation : lu comme un nombre, `-1` fausserait une moyenne ou un comptage.
Enfin, la date est éclatée en `jour`, `mois`, `an` et `hrmn`. `dep` est bien en texte ici, mais seulement parce que
la Corse (`2A`, `2B`) empêche la conversion : sur un extrait sans la Corse, `01` deviendrait `1`.
"""),
    ("md", """
### 2.3 La lecture explicite

Complétez `lire_caract` pour que :
- `lat` et `long` soient des nombres (`decimal`) ;
- `Num_Acc`, `dep`, `com`, `hrmn` et `adr` soient du texte (`dtype`) ;
- les codes `lum`, `agg`, `int`, `atm` et `col` soient des entiers `Int8`, qui acceptent les valeurs manquantes ;
- `-1` soit lu comme une valeur manquante (`na_values`), qu'il soit écrit `-1` ou avec une espace devant.
"""),
    ("ex", """
CODES_CARACT = ["lum", "agg", "int", "atm", "col"]
NON_RENSEIGNE = ["-1", " -1"]


def lire_caract(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        sep=";",
        decimal=",",
        encoding="utf-8",
        na_values=NON_RENSEIGNE,
        dtype={"Num_Acc": "str", "dep": "str", "com": "str", "hrmn": "str", "adr": "str"}
        | {c: "Int8" for c in CODES_CARACT},
    )


caract = lire_caract(RAW / "caract-2024.csv")
caract.dtypes
""", """
CODES_CARACT = ["lum", "agg", "int", "atm", "col"]
NON_RENSEIGNE = ["-1", " -1"]


def lire_caract(path: Path) -> pd.DataFrame:
    # À compléter : decimal, encoding, na_values, dtype
    return pd.read_csv(path, sep=";")


caract = lire_caract(RAW / "caract-2024.csv")
caract.dtypes
"""),
    ("code", """
assert caract["lat"].dtype == "float64", "lat doit être un nombre : pensez à decimal"
assert caract["Num_Acc"].dtype == "str", "un identifiant se lit en texte"
assert caract["dep"].dtype == "str" and caract["com"].dtype == "str"
assert str(caract["lum"].dtype) == "Int8"
assert caract["col"].isna().sum() == 6, "-1 signifie non renseigné : pensez à na_values"
print(len(caract), "accidents lus correctement")
"""),
    ("md", """
### 2.4 Une vraie date

Écrivez `ajouter_date_heure(df)`, qui ajoute une colonne `date_heure` de type `datetime64` à partir de `an`, `mois`,
`jour` et `hrmn` (format `07:40`), puis supprime ces quatre colonnes. Donnez un `format` explicite à
`pd.to_datetime` : sans lui, pandas devine, et peut confondre jour et mois.

La fonction s'enchaîne ensuite avec `pipe` : chaque étape reste une fonction courte, testable seule.
"""),
    ("ex", """
def ajouter_date_heure(df: pd.DataFrame) -> pd.DataFrame:
    texte = df["an"].astype("str") + "-" + df["mois"].astype("str") + "-" + df["jour"].astype("str") + " " + df["hrmn"]
    return df.assign(date_heure=pd.to_datetime(texte, format="%Y-%m-%d %H:%M")).drop(
        columns=["jour", "mois", "an", "hrmn"]
    )


caract = lire_caract(RAW / "caract-2024.csv").pipe(ajouter_date_heure)
caract[["Num_Acc", "date_heure"]].head()
""", """
def ajouter_date_heure(df: pd.DataFrame) -> pd.DataFrame:
    a_completer()  # À compléter


caract = lire_caract(RAW / "caract-2024.csv").pipe(ajouter_date_heure)
caract[["Num_Acc", "date_heure"]].head()
"""),
    ("code", """
assert str(caract["date_heure"].dtype).startswith("datetime64")
assert caract["date_heure"].min() >= pd.Timestamp("2024-01-01")
assert caract["date_heure"].max() < pd.Timestamp("2025-01-01")
assert "hrmn" not in caract.columns
"""),
    ("md", """
## Partie 3 : les usagers, et le lien avec les accidents (6 min)

Complétez `lire_usagers` : identifiants en texte, `actp` en `category`, `an_nais` en `Int16`, les autres codes en
`Int8`, et `-1` comme valeur manquante. Regardez ensuite `id_usager` : à quoi servent les espaces ?
"""),
    ("ex", """
CODES_USAGERS = ["place", "catu", "grav", "sexe", "trajet", "secu1", "secu2", "secu3", "locp", "etatp"]
TYPES_USAGERS = {
    "Num_Acc": "str",
    "id_usager": "str",
    "id_vehicule": "str",
    "num_veh": "str",
    "actp": "category",
    "an_nais": "Int16",
} | {c: "Int8" for c in CODES_USAGERS}


def lire_usagers(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="utf-8", na_values=NON_RENSEIGNE, dtype=TYPES_USAGERS)


usagers = lire_usagers(RAW / "usagers-2024.csv")
usagers.head(3)
""", """
CODES_USAGERS = ["place", "catu", "grav", "sexe", "trajet", "secu1", "secu2", "secu3", "locp", "etatp"]
TYPES_USAGERS = {}  # À compléter


def lire_usagers(path: Path) -> pd.DataFrame:
    a_completer()  # À compléter


usagers = lire_usagers(RAW / "usagers-2024.csv")
usagers.head(3)
"""),
    ("code", """
assert usagers["Num_Acc"].dtype == "str"
assert str(usagers["grav"].dtype) == "Int8" and str(usagers["an_nais"].dtype) == "Int16"
print(repr(usagers["id_usager"].iloc[0]))
"""),
    ("rep", """
L'espace est une espace insécable (`\\xa0`), utilisée comme séparateur de milliers : `203 988 581`. C'est un
identifiant, on le garde en texte tel quel. On ne le convertira jamais en nombre.
"""),
    ("md", """
Chaque usager doit se rattacher à un accident connu. Calculez le nombre d'usagers orphelins, puis le nombre moyen
d'usagers par accident.
"""),
    ("ex", """
orphelins = (~usagers["Num_Acc"].isin(caract["Num_Acc"])).sum()
par_accident = usagers.groupby("Num_Acc").size().mean()
print(orphelins, "orphelins ;", round(par_accident, 2), "usagers par accident en moyenne")
""", """
orphelins = a_completer()  # À compléter
par_accident = a_completer()  # À compléter
print(orphelins, "orphelins ;", round(par_accident, 2), "usagers par accident en moyenne")
"""),
    ("code", """
assert orphelins == 0
assert 2 < par_accident < 3
"""),
    ("md", """
## Partie 4 : les contrôles d'import (4 min)

Un fichier défectueux doit arrêter l'ingestion avec un message clair, au lieu de produire un résultat faux en
silence. Complétez `check_import`, qui applique les cinq contrôles d'import :
1. le fichier existe ;
2. il n'est pas vide ;
3. les colonnes attendues sont présentes, après lecture avec la fonction `lire` ;
4. le nombre de lignes est plausible ;
5. les types lus commencent par le type attendu, par exemple `"float"` pour `float64`.

Chaque échec lève une `ErreurImport`. La qualité des valeurs (domaines, doublons) viendra en séance 3.
"""),
    ("ex", """
class ErreurImport(Exception):
    pass


def check_import(path: Path, lire, colonnes: list[str], min_lignes: int, types: dict[str, str]) -> pd.DataFrame:
    if not path.exists():
        raise ErreurImport(f"{path} : fichier absent")
    if path.stat().st_size == 0:
        raise ErreurImport(f"{path} : fichier vide")
    df = lire(path)
    manquantes = sorted(set(colonnes) - set(df.columns))
    if manquantes:
        raise ErreurImport(f"{path.name} : colonnes manquantes {manquantes}")
    if len(df) < min_lignes:
        raise ErreurImport(f"{path.name} : {len(df)} lignes, au moins {min_lignes} attendues")
    for colonne, attendu in types.items():
        if not str(df[colonne].dtype).startswith(attendu):
            raise ErreurImport(f"{path.name} : {colonne} lu en {df[colonne].dtype}, {attendu} attendu")
    return df
""", """
class ErreurImport(Exception):
    pass


def check_import(path: Path, lire, colonnes: list[str], min_lignes: int, types: dict[str, str]) -> pd.DataFrame:
    # À compléter : les cinq contrôles, dans l'ordre, puis renvoyer le DataFrame lu
    a_completer()
"""),
    ("md", "On fabrique trois fichiers défectueux à partir du vrai, puis on vérifie que chacun est refusé."),
    ("code", """
lignes = (RAW / "caract-2024.csv").read_text(encoding="utf-8").splitlines()
(TMP / "vide.csv").write_text("", encoding="utf-8")
renommee = [lignes[0].replace('"lat"', '"latitude"')] + lignes[1:]
(TMP / "colonne_renommee.csv").write_text("\\n".join(renommee), encoding="utf-8")
(TMP / "tronque.csv").write_text("\\n".join(lignes[:101]), encoding="utf-8")

lire = lambda path: lire_caract(path).pipe(ajouter_date_heure)  # noqa: E731
COLONNES = ["Num_Acc", "dep", "com", "lat", "long", "date_heure"]
TYPES = {"dep": "str", "lat": "float", "long": "float", "date_heure": "datetime64"}


def est_refuse(path: Path) -> bool:
    try:
        check_import(path, lire, COLONNES, 40_000, TYPES)
    except ErreurImport as erreur:
        print("Refusé :", erreur)
        return True
    return False


assert all(est_refuse(TMP / nom) for nom in ["absent.csv", "vide.csv", "colonne_renommee.csv", "tronque.csv"])
assert len(check_import(RAW / "caract-2024.csv", lire, COLONNES, 40_000, TYPES)) == 54_402
"""),
    ("md", """
## Partie 5 : optimiser la vitesse et la mémoire (10 min)

On travaille sur le plus gros fichier, les usagers. Deux outils de mesure sont fournis : `mesurer` garde le meilleur
de trois essais, `memoire` compte la mémoire réelle, contenu des chaînes compris (`deep=True`).
"""),
    ("code", """
USAGERS = RAW / "usagers-2024.csv"
UTILES = ["Num_Acc", "id_vehicule", "catu", "grav", "sexe", "an_nais", "trajet", "secu1"]


def mesurer(fonction, essais: int = 3) -> float:
    temps = []
    for _ in range(essais):
        debut = time.perf_counter()
        fonction()
        temps.append(time.perf_counter() - debut)
    return min(temps)


def memoire(df: pd.DataFrame) -> float:
    return df.memory_usage(deep=True).sum() / 1e6
"""),
    ("md", """
Complétez les trois lectures manquantes :
- **explicite** : celle de `lire_usagers` ;
- **colonnes utiles** : seulement les colonnes de `UTILES` (`usecols`), avec leurs types de `TYPES_USAGERS` ;
- **pyarrow** : la lecture explicite, avec `engine="pyarrow"`.
"""),
    ("ex", """
lectures = {
    "implicite (sep seul)": lambda: pd.read_csv(USAGERS, sep=";"),
    "explicite": lambda: lire_usagers(USAGERS),
    "colonnes utiles": lambda: pd.read_csv(
        USAGERS,
        sep=";",
        usecols=UTILES,
        na_values=NON_RENSEIGNE,
        dtype={c: t for c, t in TYPES_USAGERS.items() if c in UTILES},
    ),
    "explicite, pyarrow": lambda: pd.read_csv(
        USAGERS, sep=";", na_values=NON_RENSEIGNE, dtype=TYPES_USAGERS, engine="pyarrow"
    ),
}
""", """
lectures = {
    "implicite (sep seul)": lambda: pd.read_csv(USAGERS, sep=";"),
    "explicite": lambda: a_completer(),  # À compléter
    "colonnes utiles": lambda: a_completer(),  # À compléter
    "explicite, pyarrow": lambda: a_completer(),  # À compléter
}
"""),
    ("code", """
resultats = pd.DataFrame(
    [{"lecture": nom, "temps_s": mesurer(lire), "memoire_mo": memoire(lire())} for nom, lire in lectures.items()]
).set_index("lecture")
resultats.round(3)
"""),
    ("md", """
Une fois le CSV lu correctement, on ne le relit plus : on l'écrit en Parquet, un format en colonnes, compressé, qui
conserve les types. Écrivez `usagers` en Parquet dans `TMP`, puis comparez la taille des deux fichiers et le temps de
relecture.
"""),
    ("ex", """
parquet = TMP / "usagers.parquet"
usagers.to_parquet(parquet, index=False)
print(f"CSV : {USAGERS.stat().st_size / 1e6:.1f} Mo ; Parquet : {parquet.stat().st_size / 1e6:.1f} Mo")
resultats.loc["relecture Parquet"] = [mesurer(lambda: pd.read_parquet(parquet)), memoire(pd.read_parquet(parquet))]
resultats.round(3)
""", """
parquet = TMP / "usagers.parquet"
# À compléter : écrire, comparer les tailles, puis ajouter la ligne « relecture Parquet » à resultats
a_completer()
resultats.round(3)
"""),
    ("code", """
assert resultats.loc["colonnes utiles", "memoire_mo"] < resultats.loc["implicite (sep seul)", "memoire_mo"] / 2
assert resultats.loc["explicite, pyarrow", "temps_s"] < resultats.loc["explicite", "temps_s"]
assert pd.read_parquet(parquet)["an_nais"].dtype == usagers["an_nais"].dtype, "Parquet conserve les types"
"""),
    ("md", """
**Question.** La lecture explicite est-elle plus rapide que la lecture implicite ? Qu'en concluez-vous ?
"""),
    ("rep", """
Non, elle est souvent plus lente : convertir `-1` en valeur manquante et vérifier chaque type a un coût. On ne
choisit pas la lecture explicite pour la vitesse, mais parce qu'elle est juste, et elle occupe aussi moins de
mémoire. La vitesse se gagne ailleurs : le moteur pyarrow, ne lire que les colonnes utiles, et surtout ne lire le CSV
qu'une fois avant de passer au Parquet.
"""),
    ("md", """
## Écrire le résultat

Les fichiers propres vont dans `data/clean`. Le TP 2 en a besoin.
"""),
    ("code", """
CLEAN.mkdir(parents=True, exist_ok=True)
caract.to_parquet(CLEAN / "caract.parquet", index=False)
usagers.to_parquet(CLEAN / "usagers.parquet", index=False)
sorted(p.name for p in CLEAN.iterdir())
"""),
    ("md", """
## Bonus 1 : la même lecture avec Polars

Mesurez `pl.read_csv(USAGERS, separator=";")` avec `mesurer`, puis regardez le schéma : Polars devine-t-il mieux les
types que pandas ?
"""),
    ("ex", """
import polars as pl

print(f"Polars : {mesurer(lambda: pl.read_csv(USAGERS, separator=';')):.3f} s")
pl.read_csv(USAGERS, separator=";").schema
""", """
import polars as pl

# À compléter
"""),
    ("rep", """
Polars est très rapide, mais il devine lui aussi : `secu2`, `secu3`, `locp` et `etatp` deviennent du texte à cause de
`" -1"`, et `Num_Acc` un entier. La règle « jamais de lecture implicite » vaut pour toutes les bibliothèques.
"""),
    ("md", """
## Bonus 2 : le fichier des lieux

Lisez `lieux-2024.csv`. Trois pièges vous attendent : la valeur `#VALEURMULTI` dans `nbv`, la virgule décimale de
`larrout`, et des points de repère `pr` écrits `3 900`, avec une espace insécable. Essayez `thousands="\\xa0"` :
que constatez-vous ?
"""),
    ("ex", """
lieux = pd.read_csv(
    RAW / "lieux-2024.csv",
    sep=";",
    decimal=",",
    thousands="\\xa0",
    na_values=NON_RENSEIGNE + ["#VALEURMULTI"],
    dtype={"Num_Acc": "str", "voie": "str", "v2": "str", "pr": "str", "pr1": "str"},
)
print(lieux["pr"].dtype, "->", lieux.loc[lieux["pr"].str.contains("\\xa0", na=False), "pr"].head(3).tolist())

# thousands est ignoré en silence : l'espace insécable occupe deux octets en UTF-8, et le lecteur C de pandas
# n'accepte qu'un caractère d'un octet. On nettoie donc après la lecture.
lieux = lieux.assign(
    pr=lambda d: pd.to_numeric(d["pr"].str.replace("\\xa0", ""), errors="raise"),
    pr1=lambda d: pd.to_numeric(d["pr1"].str.replace("\\xa0", ""), errors="raise"),
)
lieux[["nbv", "larrout", "pr", "pr1"]].dtypes
""", """
# À compléter
"""),
]


# ----------------------------------------------------------------------------
# TP 2 : JSON et API

TP2 = [
    ("md", """
# TP 2 : ingérer du JSON depuis une API, les communes de France

**Durée : 25 minutes, en binôme.**

L'[API Géo](https://geo.api.gouv.fr), publiée par l'État, renvoie en JSON les communes, leur population, leurs codes
postaux et les coordonnées de leur centre. Elle est gratuite et sans clé. On s'en sert pour enrichir les accidents
du TP 1.

À la fin du TP, vous saurez :
- appeler une API proprement : paramètres, `timeout`, code HTTP, réponse brute sauvegardée ;
- aplatir un JSON imbriqué avec `pd.json_normalize` ;
- enchaîner des appels, et reprendre là où l'on s'était arrêté ;
- vérifier une jointure, et remplacer une boucle par un calcul vectorisé.

Comme au TP 1, une cellule `assert` suit chaque exercice, et un exercice non rempli s'arrête sur « Exercice à
compléter ».
"""),
    ("code", """
import json
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests

API = "https://geo.api.gouv.fr/communes"
CLEAN = Path("data/clean")

# Sans réseau, remplacez par JOUR = "2026-10-25" : c'est la copie de secours fournie
JOUR = date.today().isoformat()
RAW_API = Path("data/raw/api_geo") / JOUR


# Appelée par les cellules d'exercice tant que vous ne les avez pas remplies
def a_completer():
    raise NotImplementedError("Exercice à compléter : remplacez a_completer() par votre code")
"""),
    ("md", "Les accidents viennent du TP 1. S'il n'est pas terminé, la cellule les relit depuis le CSV."),
    ("code", """
if (CLEAN / "accidents" / "caract.parquet").exists():
    caract = pd.read_parquet(CLEAN / "accidents" / "caract.parquet")
else:
    caract = pd.read_csv(
        "data/raw/accidents_2024/caract-2024.csv",
        sep=";",
        decimal=",",
        dtype={"Num_Acc": "str", "dep": "str", "com": "str"},
    )
print(len(caract), "accidents,", caract["dep"].nunique(), "départements")
"""),
    ("md", """
## Partie 1 : un appel (5 min)

Appelez l'API pour les communes de Corse-du-Sud (`codeDepartement=2A`), avec les champs
`nom,code,population,centre,codesPostaux`. Passez les paramètres par `params` plutôt que dans l'URL, ajoutez un
`timeout`, et levez une erreur si le code HTTP n'est pas 200.
"""),
    ("ex", """
reponse = requests.get(
    API, params={"codeDepartement": "2A", "fields": "nom,code,population,centre,codesPostaux"}, timeout=10
)
reponse.raise_for_status()
communes_2a = reponse.json()
print(reponse.status_code, reponse.headers["content-type"], len(communes_2a), "communes")
print(json.dumps(communes_2a[1], ensure_ascii=False, indent=2))
""", """
reponse = a_completer()  # À compléter
communes_2a = reponse.json()
print(reponse.status_code, reponse.headers["content-type"], len(communes_2a), "communes")
print(json.dumps(communes_2a[1], ensure_ascii=False, indent=2))
"""),
    ("code", """
assert isinstance(communes_2a, list) and len(communes_2a) > 100
assert {"nom", "code", "population", "centre", "codesPostaux"} <= set(communes_2a[0])
"""),
    ("md", """
**Règle :** on sauvegarde la réponse brute avant de la transformer. Si la transformation a un défaut, on la corrige et
on la relance sans rappeler l'API. Sauvegardez `communes_2a` dans `RAW_API / "essai_2A.json"`.
"""),
    ("ex", """
RAW_API.mkdir(parents=True, exist_ok=True)
(RAW_API / "essai_2A.json").write_text(json.dumps(communes_2a, ensure_ascii=False), encoding="utf-8")
""", """
a_completer()  # À compléter
"""),
    ("code", """
assert json.loads((RAW_API / "essai_2A.json").read_text(encoding="utf-8")) == communes_2a
"""),
    ("md", """
## Partie 2 : aplatir le JSON (6 min)

`pd.json_normalize` transforme les objets imbriqués en colonnes séparées par un point. Regardez le résultat, puis
remplacez la colonne `centre.coordinates`, une liste `[longitude, latitude]`, par deux colonnes `lon` et `lat`.
Supprimez les colonnes `centre.*`.
"""),
    ("code", """
pd.json_normalize(communes_2a).head(3)
"""),
    ("ex", """
def aplatir_communes(records: list[dict]) -> pd.DataFrame:
    df = pd.json_normalize(records)
    coordonnees = pd.DataFrame(df["centre.coordinates"].tolist(), columns=["lon", "lat"], index=df.index)
    return df.join(coordonnees).drop(columns=["centre.type", "centre.coordinates"])


communes_2a_df = aplatir_communes(communes_2a)
communes_2a_df.head(3)
""", """
def aplatir_communes(records: list[dict]) -> pd.DataFrame:
    a_completer()  # À compléter


communes_2a_df = aplatir_communes(communes_2a)
communes_2a_df.head(3)
"""),
    ("code", """
assert {"lon", "lat"} <= set(communes_2a_df.columns)
assert not any(c.startswith("centre") for c in communes_2a_df.columns)
assert communes_2a_df["lat"].between(41, 43).all(), "la Corse-du-Sud est entre 41 et 43 degrés de latitude"
"""),
    ("md", """
Une commune peut avoir plusieurs codes postaux. Avec `record_path="codesPostaux"` et `meta=["code", "nom"]`,
`json_normalize` produit une ligne par code postal. Construisez cette table et renommez la colonne `0` en
`code_postal`.
"""),
    ("ex", """
codes_postaux = pd.json_normalize(communes_2a, record_path="codesPostaux", meta=["code", "nom"]).rename(
    columns={0: "code_postal"}
)
codes_postaux.head()
""", """
codes_postaux = a_completer()  # À compléter
codes_postaux.head()
"""),
    ("code", """
assert len(codes_postaux) == sum(len(c["codesPostaux"]) for c in communes_2a)
assert list(codes_postaux.columns) == ["code_postal", "code", "nom"]
"""),
    ("md", """
## Partie 3 : tous les départements des accidents (6 min)

Écrivez `extraire(departements, dossier)` :
- une seule `requests.Session` pour tous les appels : la connexion est réutilisée, c'est plus rapide ;
- pour chaque département, le fichier brut `dossier / f"communes_{dep}.json"` ;
- **si le fichier existe déjà, on ne rappelle pas l'API** : relancer après une coupure reprend où l'on s'était arrêté ;
- une pause de 0,1 seconde entre deux appels, par politesse envers le service.

On demande aussi les arrondissements municipaux (`type`) : la partie 4 montre pourquoi. Le premier passage prend
de 20 à 40 secondes selon le réseau. Le second, presque rien.
"""),
    ("code", """
CHAMPS = "nom,code,codeDepartement,population,centre,codesPostaux,type"
TYPES = "commune-actuelle,arrondissement-municipal"
departements = sorted(caract["dep"].unique())
"""),
    ("ex", """
def extraire(departements: list[str], dossier: Path, pause: float = 0.1) -> list[Path]:
    dossier.mkdir(parents=True, exist_ok=True)
    paths = []
    with requests.Session() as session:
        for dep in departements:
            path = dossier / f"communes_{dep}.json"
            if not path.exists():
                reponse = session.get(
                    API, params={"codeDepartement": dep, "fields": CHAMPS, "type": TYPES}, timeout=10
                )
                reponse.raise_for_status()
                path.write_text(json.dumps(reponse.json(), ensure_ascii=False), encoding="utf-8")
                time.sleep(pause)
            paths.append(path)
    return paths


debut = time.perf_counter()
paths = extraire(departements, RAW_API)
print(f"{len(paths)} fichiers en {time.perf_counter() - debut:.1f} s")
""", """
def extraire(departements: list[str], dossier: Path, pause: float = 0.1) -> list[Path]:
    a_completer()  # À compléter


debut = time.perf_counter()
paths = extraire(departements, RAW_API)
print(f"{len(paths)} fichiers en {time.perf_counter() - debut:.1f} s")
"""),
    ("md", """
Relancez la cellule précédente : le temps doit tomber sous la seconde. Construisez ensuite **une seule fois** le
DataFrame de toutes les communes : une liste de tous les enregistrements, puis `aplatir_communes`. Ajouter les lignes
une à une dans une boucle recopierait le tableau à chaque tour. Renommez `codeDepartement` en `dep` et `codesPostaux`
en `codes_postaux`, et passez `population` en `Int64`.
"""),
    ("ex", """
records = [commune for path in paths for commune in json.loads(path.read_text(encoding="utf-8"))]
communes = (
    aplatir_communes(records)
    .rename(columns={"codeDepartement": "dep", "codesPostaux": "codes_postaux"})
    .astype({"population": "Int64"})
)
communes.head()
""", """
records = a_completer()  # À compléter
communes = a_completer()  # À compléter
communes.head()
"""),
    ("code", """
assert len(communes) > 34_000
assert {"code", "nom", "dep", "population", "type", "lon", "lat"} <= set(communes.columns)
assert str(communes["population"].dtype) == "Int64"
"""),
    ("md", """
## Partie 4 : vérifier la jointure (4 min)

Avant d'enrichir les accidents, on mesure quelle part d'entre eux retrouve sa commune. Calculez ce taux d'abord avec
les seules communes (`type == "commune-actuelle"`), puis avec toutes les lignes. Pour le premier calcul, affichez les
cinq départements qui concentrent les accidents sans correspondance.
"""),
    ("ex", """
seules = communes[communes["type"] == "commune-actuelle"]
trouve = caract["com"].isin(seules["code"])
print(f"Communes seules : {trouve.mean():.2%}")
print(caract.loc[~trouve, "dep"].value_counts().head(5))
taux_tout = caract["com"].isin(communes["code"]).mean()
print(f"Avec les arrondissements : {taux_tout:.2%}")
""", """
taux_tout = a_completer()  # À compléter : les deux taux, puis les départements
"""),
    ("code", """
assert taux_tout > 0.998
"""),
    ("md", "**Question.** Que s'est-il passé avec les communes seules ? Que faire des accidents encore sans commune ?"),
    ("rep", """
Les accidents de Paris, Marseille et Lyon sont codés par arrondissement (`75116`, `13208`, `69383`), alors que
l'API renvoie par défaut une seule commune (`75056` pour Paris). Sans les arrondissements, plus de 10 % des
accidents perdaient leur commune, sans aucune erreur affichée. Il reste une soixantaine d'accidents dont le code
commune est inconnu de l'API : on les compte et on les signale, la séance 3 traitera ce type d'anomalie.
"""),
    ("md", """
## Partie 5 : accidents pour 10 000 habitants (2 min)

Calculez, par département, le nombre d'accidents pour 10 000 habitants, et affichez les cinq premiers. Attention à
la population : Paris figure à la fois comme commune et comme somme de ses arrondissements.
"""),
    ("ex", """
population = communes[communes["type"] == "commune-actuelle"].groupby("dep")["population"].sum()
taux = (caract.groupby("dep").size() / population * 10_000).sort_values(ascending=False)
taux.head()
""", """
population = a_completer()  # À compléter
taux = a_completer()  # À compléter
taux.head()
"""),
    ("code", """
assert population["75"] < 2_500_000, "Paris est-il compté deux fois ?"
"""),
    ("md", """
## Partie 6 : remplacer une boucle par un calcul vectorisé (7 min)

Quelle distance sépare chaque accident du centre de sa commune ? La fonction `haversine` est fournie. Elle accepte des
nombres comme des tableaux NumPy. On compare trois façons de l'appliquer :
1. `iterrows`, fournie ;
2. `apply` ligne par ligne, à compléter ;
3. un seul appel sur les colonnes entières, à compléter.
"""),
    ("code", """
def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


acc = caract.merge(communes[["code", "lat", "lon"]], left_on="com", right_on="code", suffixes=("", "_centre"))


def avec_iterrows(df):
    return [haversine(r["lat"], r["long"], r["lat_centre"], r["lon"]) for _, r in df.iterrows()]
"""),
    ("ex", """
def avec_apply(df):
    return df.apply(lambda r: haversine(r["lat"], r["long"], r["lat_centre"], r["lon"]), axis=1)


def vectorise(df):
    return haversine(df["lat"], df["long"], df["lat_centre"], df["lon"])
""", """
def avec_apply(df):
    a_completer()  # À compléter


def vectorise(df):
    a_completer()  # À compléter
"""),
    ("code", """
temps = {}
for fonction in [avec_iterrows, avec_apply, vectorise]:
    debut = time.perf_counter()
    distances = np.asarray(fonction(acc), dtype=float)
    temps[fonction.__name__] = time.perf_counter() - debut
    assert np.allclose(distances, vectorise(acc))
print({nom: f"{t:.4f} s" for nom, t in temps.items()})
print(f"Vectorisé {temps['avec_iterrows'] / temps['vectorise']:.0f} fois plus rapide que iterrows")
"""),
    ("code", """
acc["distance_km"] = vectorise(acc)
acc["distance_km"].describe().round(1)
"""),
    ("md", """
**Question.** Certains accidents sont à plus de 50 km du centre de leur commune. Faut-il corriger ces lignes dans le
script d'ingestion ?
"""),
    ("rep", """
Non. L'ingestion lit fidèlement ce que la source contient, et ses contrôles portent sur la forme : présence,
colonnes, types. Une coordonnée improbable est une question de qualité des valeurs : on la détectera et on décidera
quoi en faire avec les contrôles de la séance 3.
"""),
    ("md", "## Écrire le résultat"),
    ("code", """
(CLEAN / "api_geo").mkdir(parents=True, exist_ok=True)
communes.to_parquet(CLEAN / "api_geo" / "communes.parquet", index=False)
"""),
]


if __name__ == "__main__":
    write("TP1_csv", TP1)
    write("TP2_json", TP2)
