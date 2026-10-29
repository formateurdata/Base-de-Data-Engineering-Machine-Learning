#!/bin/bash
# Crée l'utilisateur « lecteur », en lecture seule : c'est lui qu'utilise le script d'ingestion.
set -euo pipefail
psql -v ON_ERROR_STOP=1 -v pwd="$LECTEUR_PASSWORD" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
CREATE ROLE lecteur LOGIN PASSWORD :'pwd';
GRANT CONNECT ON DATABASE pagila TO lecteur;
GRANT USAGE ON SCHEMA public TO lecteur;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO lecteur;
SQL
