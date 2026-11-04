#!/bin/bash
# Moindre privilège : « lecteur » pour l'extraction, « generateur » pour le script de données. postgres reste réservé
# à l'administration. Les délais empêchent une requête ou une transaction oubliée de bloquer la base.
set -euo pipefail
psql -v ON_ERROR_STOP=1 -v pwd_lecteur="$LECTEUR_PASSWORD" -v pwd_generateur="$GENERATEUR_PASSWORD" \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
REVOKE ALL ON DATABASE boutique FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

CREATE ROLE lecteur LOGIN PASSWORD :'pwd_lecteur' CONNECTION LIMIT 10;
ALTER ROLE lecteur SET default_transaction_read_only = on;
ALTER ROLE lecteur SET statement_timeout = '5min';
ALTER ROLE lecteur SET idle_in_transaction_session_timeout = '1min';
GRANT CONNECT ON DATABASE boutique TO lecteur;
GRANT USAGE ON SCHEMA public TO lecteur;
GRANT SELECT ON commandes TO lecteur;

CREATE ROLE generateur LOGIN PASSWORD :'pwd_generateur' CONNECTION LIMIT 5;
ALTER ROLE generateur SET statement_timeout = '1min';
ALTER ROLE generateur SET idle_in_transaction_session_timeout = '1min';
GRANT CONNECT ON DATABASE boutique TO generateur;
GRANT USAGE ON SCHEMA public TO generateur;
GRANT SELECT, INSERT ON commandes TO generateur;
SQL
