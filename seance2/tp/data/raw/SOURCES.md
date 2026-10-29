# Sources des copies de secours

Ces fichiers sont des copies intactes des sources, téléchargées le 25 octobre 2026. Les TP les utilisent si le
réseau de la salle ne permet pas de les retélécharger. On ne les modifie jamais.

| Dossier | Source | Licence |
|---|---|---|
| `accidents_2024/` | ONISR, [Bases de données annuelles des accidents corporels de la circulation routière, 2005 à 2024](https://www.data.gouv.fr/datasets/bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2024), fichiers 2024 : `caract`, `lieux`, `vehicules`, `usagers` | Licence Ouverte / Open Licence |
| `api_geo/2026-10-25/` | [API Géo](https://geo.api.gouv.fr), `GET /communes?codeDepartement=<dep>&fields=nom,code,codeDepartement,population,centre,codesPostaux,type&type=commune-actuelle,arrondissement-municipal`, une réponse par département présent dans les accidents | Voir les [mentions légales](https://geo.api.gouv.fr/cgu) du service |

La base PostgreSQL du TP 3 est [Pagila](https://github.com/xzilla/pagila), commit `fc7a867` du 26 mars 2026, sous
licence BSD. Les scripts `tp3_postgres/init/01_pagila_schema.sql` et `02_pagila_data.sql` en sont des copies
intactes.
