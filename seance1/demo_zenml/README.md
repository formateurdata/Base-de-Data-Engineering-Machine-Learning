# Démo séance 1 : pipeline ML Titanic orchestré avec ZenML

Pipeline d'entraînement : ingestion, préparation, feature engineering, découpage
entraînement / validation / test, entraînement de deux candidats, évaluation sur le test,
puis passage en production si l'accuracy dépasse 0,70. Pipeline d'inférence : prédiction
sur de nouveaux passagers avec la version du modèle en production.

## Fichiers

- `steps.py` : les étapes (`@step`).
- `pipelines.py` : `training_pipeline` et `inference_pipeline`, reliés par le même `Model`
  (Model Control Plane).
- `run.py` : point d'entrée (`train` ou `predict`).
- `data/titanic.csv` : le fichier `train.csv` de la compétition Kaggle « Titanic: Machine
  Learning from Disaster » (891 passagers, 342 survivants).
- `data/nouveaux_passagers.csv` : quatre passagers fictifs pour l'inférence.
Les dépendances sont celles du module, déclarées dans le `pyproject.toml` et le `uv.lock` à
la racine du dépôt et gérées avec [uv](https://docs.astral.sh/uv/).

## Préparer l'environnement

Testé avec Python 3.13 et ZenML 0.98.0. L'environnement est géré avec uv.

1. Installer uv :

```bash
# Mac
brew install uv
# ou, Mac et Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

uv --version             # vérifie l'installation
```

2. Créer l'environnement et installer les dépendances, depuis la racine du dépôt :

```bash
uv sync                  # crée .venv à la racine et installe les dépendances de uv.lock
```

uv télécharge lui-même une version de Python compatible si aucune n'est installée.

## Lancer la démo

```bash
cd seance1/demo_zenml

# Sur Mac, obligatoire pour lancer le serveur local de ZenML
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
uv run zenml login --local   # démarre le serveur local et le dashboard (http://127.0.0.1:8237)
uv run zenml init

uv run python run.py train   # entraîne, évalue, passe en production si accuracy > 0.70
uv run python run.py predict # prédit avec la version en production

uv run zenml model version list --model titanic_survival   # versions et stages du modèle
```

Lancer les commandes depuis `seance1/demo_zenml` : les chemins `data/...` sont relatifs à ce
dossier. `uv run` remonte jusqu'au `pyproject.toml` de la racine et utilise son `.venv`,
sans avoir à activer l'environnement.

La démo utilise uniquement ZenML open source, en local : `zenml login --local` démarre un
serveur sur la machine (base SQLite dans `~/Library/Application Support/zenml`), sans compte
ZenML Pro. Toujours passer `--local` : `zenml login` sans option ouvre la connexion à ZenML
Pro.

Les scores sont enregistrés comme métadonnées, à deux endroits :

- sur les étapes `train_model` et `evaluate_model` : dans le dashboard, ouvrir le run, cliquer
  sur l'étape dans le DAG, onglet Metadata ;
- sur la version du modèle `titanic_survival` : le dashboard open source n'affiche pas les
  modèles, on les lit donc en Python :

```bash
uv run python -c 'from zenml.client import Client; print(Client().get_model_version("titanic_survival", "production").run_metadata)'
```

## Dépannage

`uv run zenml init` ou `uv run python run.py train` échoue avec `Connection refused` sur
`127.0.0.1:8237` : le client ZenML est connecté à un serveur local qui ne tourne plus
(redémarrage de la machine, par exemple). Deux solutions :

- relancer le serveur : `export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` puis
  `uv run zenml login --local` ;
- ou travailler sans serveur ni dashboard : `uv run zenml logout --local`.

uv affiche `VIRTUAL_ENV=... does not match the project environment path .venv` : un autre
environnement est activé dans le terminal (pyenv, conda, ancien venv). uv l'ignore et utilise
bien `.venv`, l'avertissement est sans effet ; `deactivate` le fait disparaître.

`uv run zenml login --local` refuse de démarrer et demande `OBJC_DISABLE_INITIALIZE_FORK_SAFETY` :
c'est une exigence de ZenML sur Mac, exporter la variable comme ci-dessus.

Résultat obtenu lors du test : régression logistique retenue sur la validation (0,848
contre 0,843 pour la forêt aléatoire), accuracy de 0,849 sur le test, modèle passé en
production.

Relancer `uv run python run.py train` relit le CSV et réexécute la promotion en production.
Ces deux étapes sont exclues du cache : le contenu d'un fichier peut changer au même
chemin, et une promotion doit s'appliquer à la version courante du modèle.
Les transformations déterministes peuvent réutiliser le cache si leurs dépendances
sont identiques. C'est l'occasion de montrer le cache de ZenML. Pour forcer une nouvelle exécution complète,
ajouter `enable_cache=False` au décorateur `@pipeline` de `training_pipeline`.
