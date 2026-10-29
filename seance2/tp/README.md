# Séance 2 : TP d'ingestion

Quatre TP, sur trois sources réelles : un CSV (accidents corporels 2024, data.gouv.fr), une API JSON (API Géo) et
une base PostgreSQL (Pagila), lancée avec Docker Compose.

| TP | Support | Durée | Sujet |
|---|---|---|---|
| 1 | `TP1_csv_enonce.ipynb` | 35 min | Lire un CSV réel, contrôles d'import, vitesse et mémoire |
| 2 | `TP2_json_enonce.ipynb` | 25 min | Appeler une API, aplatir du JSON, vérifier une jointure, vectoriser |
| 3 | `tp3_postgres/` | 35 min | Ingestion complète puis incrémentale depuis PostgreSQL |
| 4 | `tp4_script/` | en autonomie | Assembler les trois ingestions en scripts réutilisables |

## Avant la séance

1. Installer [uv](https://docs.astral.sh/uv/) comme indiqué dans le [README du module](../../README.md), puis, depuis la racine du dépôt :
   ```bash
   uv sync
   cd seance2/tp
   uv run --with-requirements requirements.txt jupyter lab
   ```
   `uv` gère l'environnement Python et les dépendances supplémentaires des TP. Aucune activation manuelle de l'environnement n'est nécessaire. Dans JupyterLab, ouvrir le notebook du TP 1 ou du TP 2 et choisir le noyau Python de cet environnement.
2. Docker Desktop installé et lancé, puis les images téléchargées à l'avance :
   ```bash
   cd tp3_postgres
   docker compose pull
   ```

## Lancer la base du TP 3

```bash
cd tp3_postgres
cp .env.example .env               # puis changer les deux mots de passe
docker compose up -d               # premier démarrage : chargement de Pagila, environ 10 s
docker compose ps                  # attendre l'état « healthy »
```

Interface web facultative : `docker compose --profile outils up -d`, puis http://localhost:8080
(système PostgreSQL, serveur `postgres`, utilisateur `lecteur`).

Pour simuler de l'activité entre deux ingestions incrémentales :

```bash
docker exec -i tp3_pagila psql -U postgres -d pagila < maj_locations.sql
```

Pour repartir d'une base neuve : `docker compose down -v`, puis `docker compose up -d`.

## Arborescence

```
data/raw/        copies intactes des sources (voir data/raw/SOURCES.md) ; ne jamais les modifier
data/clean/      fichiers Parquet produits par les TP (non versionnés)
data/state/      repère de l'ingestion incrémentale (non versionné)
tp3_postgres/    docker-compose.yml, scripts d'initialisation, squelettes du TP 3
tp4_script/      squelettes du TP 4 et verifier.py
```

Les commandes Python se lancent avec `uv`, depuis le dossier du script. Par exemple, depuis `seance2/tp` :

```bash
cd tp3_postgres
uv run --with-requirements ../requirements.txt python ingest_postgres.py
```

Pour le TP 4, utiliser la même forme depuis `tp4_script` : `uv run --with-requirements ../requirements.txt python run_all.py`.
