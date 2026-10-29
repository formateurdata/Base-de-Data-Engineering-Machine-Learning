-- Simule l'activité du magasin entre deux ingestions, à lancer en administrateur :
--   docker exec -i tp3_pagila psql -U postgres -d pagila < maj_locations.sql
-- Le déclencheur last_updated de Pagila met last_update à jour sur chaque ligne modifiée.

-- Trois locations rendues : la date de retour est corrigée
UPDATE rental
SET rental_period = tsrange(lower(rental_period), lower(rental_period) + interval '3 days')
WHERE rental_id IN (2, 3, 4);

-- Une nouvelle location, encore en cours
INSERT INTO rental (inventory_id, customer_id, staff_id, rental_period)
VALUES (1525, 459, 1, tsrange(now()::timestamp, NULL));
