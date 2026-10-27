# Bases de Data Engineering et Machine Learning

Supports pratiques du module (BAC4, 2026-2027) : démonstrations et TP de chaque séance.

## Préparer l'environnement

Un seul environnement Python pour tout le module, géré avec [uv](https://docs.astral.sh/uv/).

1. Installer uv :

```bash
# Mac
brew install uv
# ou, Mac et Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

uv --version
```

2. Cloner le dépôt puis, à sa racine :

```bash
uv sync    # crée .venv et installe les dépendances de uv.lock (Python 3.13)
```

Les commandes se lancent ensuite avec `uv run ...`, depuis n'importe quel dossier du dépôt.

## Séances

- [Séance 1 : démo ZenML, pipeline ML Titanic](seance1/demo_zenml/README.md)
