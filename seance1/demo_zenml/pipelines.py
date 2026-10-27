"""Pipelines ZenML : entraînement, puis inférence avec le modèle en production.

Les deux pipelines partagent le même Model (Model Control Plane) : le pipeline
d'entraînement crée une nouvelle version du modèle, le pipeline d'inférence lit
la version passée en production.
"""

from zenml import Model, get_pipeline_context, pipeline
from zenml.enums import ModelStages

from steps import (deploy_model, engineer_features, evaluate_model, load_data, predict,
                   prepare_data, split_data, train_model)

MODEL_NAME = "titanic_survival"


@pipeline(model=Model(name=MODEL_NAME))
def training_pipeline(path: str = "data/titanic.csv", threshold: float = 0.70):
    df = load_data(path)
    df = prepare_data(df)
    df = engineer_features(df)
    train, validation, test = split_data(df)
    model = train_model(train, validation)
    accuracy = evaluate_model(model, test)
    deploy_model(accuracy, threshold)


@pipeline(model=Model(name=MODEL_NAME, version=ModelStages.PRODUCTION))
def inference_pipeline(path: str = "data/nouveaux_passagers.csv"):
    model = get_pipeline_context().model.get_model_artifact("model")
    df = engineer_features(prepare_data(load_data(path)))
    predict(model, df)
