# Stabilise les chemins Unicode pour Compose (macOS).
unexport PWD
.DEFAULT_GOAL := help
COMPOSE := docker compose --env-file .env -f infra/docker-compose.yml
PYTHON := uv run --no-project --with-requirements requirements.txt python

.PHONY: help init pull up up-local build down reset logs ps generate verify bronze
help:
	@echo "init | pull | up | up-local | build | down | reset | logs | ps | generate | verify | bronze"
# docker compose --env-file .env -f infra/docker-compose.yml test -f .env || cp .env.example .env
init:
	@test -f .env || cp .env.example .env

pull:
	$(COMPOSE) pull

up:
	$(COMPOSE) up --no-build --pull always --wait --wait-timeout 300 -d

build:
	$(COMPOSE) build

up-local: build
	$(COMPOSE) up --no-build --pull never --wait --wait-timeout 300 -d

down:
	$(COMPOSE) down

reset:
	@printf 'Supprimer toutes les données de cette pile ? Tapez yes : '; read answer; test "$$answer" = yes
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps -a

generate:
	$(PYTHON) scripts/generer_commandes.py

verify:
	$(PYTHON) scripts/verifier_infra.py

bronze:
	$(COMPOSE) exec namenode hdfs dfs -ls -R /bronze
