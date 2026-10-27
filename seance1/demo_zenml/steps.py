"""Étapes du pipeline Titanic : chaque fonction décorée par @step est une étape ZenML.

ZenML enregistre l'entrée et la sortie de chaque étape (les artefacts), ce qui rend
chaque exécution traçable et rejouable.
"""

import logging
from typing import Annotated, Tuple

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from zenml import get_step_context, log_metadata, step
from zenml.enums import ModelStages

logger = logging.getLogger(__name__)

TARGET = "Survived"
EXPECTED = {"Pclass", "Name", "Sex", "Age", "SibSp", "Parch", "Fare", "Embarked"}
NUMERIC = ["Age", "Fare", "FamilySize"]
CATEGORICAL = ["Pclass", "Sex", "Embarked", "Title", "IsAlone"]
TITLES = ["Mr", "Mrs", "Miss", "Master"]


def log_scores(metadata: dict) -> None:
    """Rattache les scores à l'étape (visible dans le DAG) et à la version du modèle."""
    log_metadata(metadata)
    log_metadata(metadata, infer_model=True)


def split_xy(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """Sépare les variables (X) de la cible (y)."""
    return df.drop(columns=TARGET), df[TARGET]


def make_preprocessor() -> ColumnTransformer:
    """Imputation, mise à l'échelle et encodage, appris sur l'entraînement seulement."""
    numeric = make_pipeline(SimpleImputer(strategy="median"), StandardScaler())
    categorical = make_pipeline(SimpleImputer(strategy="most_frequent"),
                                OneHotEncoder(handle_unknown="ignore"))
    return ColumnTransformer([("num", numeric, NUMERIC), ("cat", categorical, CATEGORICAL)])


@step(enable_cache=False)
def load_data(path: str) -> Annotated[pd.DataFrame, "raw_data"]:
    """Ingestion : lit le CSV et vérifie qu'il contient les colonnes attendues."""
    df = pd.read_csv(path)
    missing = EXPECTED - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes : {sorted(missing)}")
    if (df["Fare"] < 0).any():
        raise ValueError("Tarif négatif : fichier rejeté")
    return df


@step
def prepare_data(df: pd.DataFrame) -> Annotated[pd.DataFrame, "clean_data"]:
    """Prépare les variables en conservant une ligne par observation et son identifiant."""
    # PassengerId reste disponible pour rattacher chaque prédiction à son passager.
    # Le ColumnTransformer l'exclut des variables utilisées par le modèle.
    df = df.drop(columns=["Cabin", "Ticket"], errors="ignore").copy()
    df["Embarked"] = df["Embarked"].str.strip().str.upper()
    return df


@step
def engineer_features(df: pd.DataFrame) -> Annotated[pd.DataFrame, "features"]:
    """Construit des variables disponibles au moment de prédire, sans statistique globale."""
    df = df.copy()
    title = df["Name"].str.extract(r",\s*([^.]+)\.", expand=False)
    df["Title"] = title.where(title.isin(TITLES), "Rare")
    df["FamilySize"] = df["SibSp"] + df["Parch"] + 1
    df["IsAlone"] = (df["FamilySize"] == 1).astype(int)
    return df.drop(columns=["Name", "SibSp", "Parch"])


@step
def split_data(df: pd.DataFrame) -> Tuple[
    Annotated[pd.DataFrame, "train"],
    Annotated[pd.DataFrame, "validation"],
    Annotated[pd.DataFrame, "test"],
]:
    """Découpage stratifié : 60 % entraînement, 20 % validation, 20 % test."""
    train, rest = train_test_split(df, test_size=0.4, stratify=df[TARGET], random_state=42)
    validation, test = train_test_split(rest, test_size=0.5, stratify=rest[TARGET],
                                        random_state=42)
    return train, validation, test


@step
def train_model(train: pd.DataFrame, validation: pd.DataFrame) -> Annotated[Pipeline, "model"]:
    """Entraîne deux candidats sur l'entraînement, garde le meilleur sur la validation."""
    candidates = {
        "logistic_regression": LogisticRegression(max_iter=1000),
        "random_forest": RandomForestClassifier(n_estimators=300, max_depth=6, random_state=42),
    }
    models, scores = {}, {}
    for name, classifier in candidates.items():
        models[name] = Pipeline([("prep", make_preprocessor()), ("clf", classifier)])
        models[name].fit(*split_xy(train))
        scores[name] = float(models[name].score(*split_xy(validation)))
    best = max(scores, key=scores.get)
    log_scores({"validation_accuracy": scores, "selected": best})
    return models[best]


@step
def evaluate_model(model: Pipeline, test: pd.DataFrame) -> Annotated[float, "test_accuracy"]:
    """Score final, mesuré une seule fois sur le jeu de test."""
    accuracy = float(model.score(*split_xy(test)))
    log_scores({"test_accuracy": accuracy})
    return accuracy


@step(enable_cache=False)
def deploy_model(accuracy: float, threshold: float) -> Annotated[bool, "deployed"]:
    """Porte de qualité : passe la version du modèle en production si le score dépasse le seuil."""
    if accuracy <= threshold:
        logger.warning("Accuracy %.3f <= %.2f : modèle non déployé", accuracy, threshold)
        return False
    get_step_context().model.set_stage(ModelStages.PRODUCTION, force=True)
    logger.info("Accuracy %.3f > %.2f : modèle passé en production", accuracy, threshold)
    return True


@step
def predict(model: Pipeline, df: pd.DataFrame) -> Annotated[pd.DataFrame, "predictions"]:
    """Inférence : probabilité de survie pour chaque nouveau passager."""
    result = df.copy()
    result["proba_survie"] = model.predict_proba(df)[:, 1].round(2)
    logger.info("Prédictions :\n%s", result.to_string())
    return result
