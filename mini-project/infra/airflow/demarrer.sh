#!/bin/bash
# Secrets internes d'Airflow : générés une seule fois sur chaque machine et conservés dans un volume, jamais dans le
# dépôt. Une clé stable permet de relire les données chiffrées après la recréation du conteneur.
set -euo pipefail
umask 077
SECRETS=/opt/airflow/secrets

# end="" : Airflow utilise la sortie de « cat » telle quelle, un retour à la ligne ferait partie du secret
[ -s "$SECRETS/fernet_key" ] || python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode(), end="")' > "$SECRETS/fernet_key"
[ -s "$SECRETS/jwt_secret" ] || python -c 'import secrets; print(secrets.token_urlsafe(64), end="")' > "$SECRETS/jwt_secret"
python -c 'import json, os; print(json.dumps({"admin": os.environ["AIRFLOW_ADMIN_PASSWORD"]}))' > "$SECRETS/mots_de_passe.json"

# Le code des DAG hérite de cet environnement et n'a pas besoin du mot de passe de l'interface
unset AIRFLOW_ADMIN_PASSWORD
exec airflow standalone
