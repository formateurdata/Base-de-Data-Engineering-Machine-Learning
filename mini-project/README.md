# Mission Data Engineering — Boutique

Une entreprise de vente en ligne de matériel informatique vous recrute pour une mission de Data Engineering.
Elle vend des claviers, souris, écrans, casques et accessoires. Son application enregistre les commandes dans une
base PostgreSQL : le produit acheté, la quantité, le montant et le statut de la commande.

La responsable commerciale souhaite disposer chaque matin d'un dashboard pour suivre l'activité : nombre de
commandes, montants par produit et répartition des statuts. Aujourd'hui, les données restent dans la base de
l'application. Votre mission est de préparer leur exploitation analytique sans recopier toute la base chaque jour.

## Le besoin métier

Vous devez construire une alimentation quotidienne qui récupère les nouvelles commandes et les commandes
modifiées depuis la dernière ingestion réussie. Une commande payée peut ensuite être expédiée, annulée ou remboursée :
il faut donc prendre en compte les mises à jour, pas seulement les nouveaux identifiants.

L'objectif final est un dashboard journalier fiable. La première étape, réalisée en classe, consiste à déposer les
données brutes dans une zone **bronze** sur HDFS. La préparation des indicateurs et le dashboard viendront ensuite ;
ils ne sont pas fournis dans ce dossier.

Avant de calculer un chiffre d'affaires, il faudra préciser avec le métier quels statuts retenir et comment traiter
les remboursements. La table ne contient ni date de vente ni historique complet des changements de statut :
`updated_at` est une date technique de modification, pas une date de vente. Elle permet l'ingestion incrémentale,
mais ne suffit pas à reconstituer un chiffre d'affaires historique par jour de vente.

## La source à votre disposition

La base `boutique` contient une table `commandes`, avec une ligne par commande simplifiée :

| Colonne | Signification |
|---|---|
| `id` | Identifiant unique de la commande |
| `client_id` | Identifiant du client |
| `produit` | Produit commandé |
| `quantite` | Quantité achetée |
| `montant` | Montant total de la ligne, de type décimal |
| `statut` | `payee`, `expediee`, `annulee` ou `remboursee` |
| `updated_at` | Date de dernière modification, avec fuseau horaire |

La base met automatiquement à jour `updated_at` lors d'une modification. Les données de l'atelier sont fictives :
un générateur insère 1 000 commandes au premier lancement, puis 500 à chaque lancement suivant.
Il ajoute des lignes ; les mises à jour seront testées séparément pendant l'atelier.

## L'infrastructure proposée

```text
Générateur → PostgreSQL (boutique.commandes)
                          ↓ extraction incrémentale orchestrée par Airflow
                       HDFS /bronze/commandes (Parquet)
                          ↓ étapes suivantes de la mission
                  Préparation des indicateurs → Dashboard
```

| Service | Utilité | Accès depuis votre machine |
|---|---|---|
| PostgreSQL `source` | Base de l'application | `127.0.0.1:5434`, base `boutique` |
| HDFS `namenode` et `datanode` | Stockage des fichiers bronze | http://localhost:9870 |
| Airflow | Orchestration et journaux des ingestions | http://localhost:8081 |
| PostgreSQL `airflow-db` | Métadonnées internes d'Airflow | Non exposé |

Les connexions Airflow `source_postgres` et `bronze_hdfs` sont préconfigurées. L'extraction utilise le rôle
`lecteur`, en lecture seule. Le rôle `generateur` peut lire et insérer ; le rôle `postgres` administre la base.
Les mots de passe correspondants sont dans votre fichier local `.env`.

## Préparer votre poste

Installez Docker Desktop, `uv` et GNU Make. Sous Windows, utilisez **Ubuntu dans WSL2**, avec l'intégration Docker
Desktop activée, puis exécutez les commandes dans ce terminal. Sur macOS et Linux, utilisez votre terminal habituel.
Allouez au moins 6 Go de mémoire à Docker et prévoyez de l'espace pour les images et les volumes.

Depuis la racine du dépôt :

```bash
cd mini-project
make init
```

Ouvrez `.env` et remplacez les **cinq mots de passe** d'exemple par vos propres valeurs, composées uniquement de
lettres sans accent et de chiffres. Ne partagez pas ce fichier.

```bash
make pull
make up
make verify
```

`make pull` télécharge les images. `make up` démarre la pile et attend les services ; il ne compile aucune image.
`make verify` doit afficher `OK` pour `secrets`, `source`, `hdfs` et `airflow`. Si Airflow vient de démarrer,
relancez la vérification après quelques instants.

Les images personnalisées Airflow et Hadoop sont configurées sous `ghcr.io/formateurdata/bac4-*`, pour Intel/AMD
et Apple Silicon. Leur publication doit avoir été effectuée par l'enseignant avant cette préparation.
Si elles ne sont pas encore disponibles, utilisez `make up-local` pour les construire sur votre machine
(le premier lancement est plus long). Cette commande nécessite aussi Internet pour les images de base et les dépendances.

## Commencer la mission

```bash
make generate
```

Vérifiez l'événement `lot_insere` dans le terminal : il indique le nombre de lignes insérées et le total en base.
Ouvrez Airflow sur http://localhost:8081 et connectez-vous avec `admin` et la valeur de `AIRFLOW_ADMIN_PASSWORD`.

Le fichier [dags/ingestion_commandes.py](dags/ingestion_commandes.py) est volontairement sans implémentation.
**Aucun DAG ne doit apparaître au premier démarrage.** Nous construirons ensemble :

1. La lecture du repère de la dernière ingestion réussie.
2. L'extraction des lignes nouvelles ou modifiées vers des fichiers Parquet dans HDFS.
3. Le contrôle des fichiers écrits.
4. La publication du nouveau repère uniquement après validation.
5. La planification quotidienne, après les premiers essais manuels.

L'infrastructure et les scripts dans `scripts/` sont fournis. Le code du pipeline se construit dans `dags/`.
L'objectif est de pouvoir expliquer quelles lignes sont extraites et comment reprendre après une interruption.

## Vérifier le comportement attendu

Sur une base neuve, le scénario de validation sera le suivant :

| Action | Résultat attendu une fois le DAG implémenté |
|---|---|
| Générer, puis ingérer | 1 000 lignes dans un premier fichier Parquet |
| Relancer l'ingestion sans générer | Aucune ligne extraite, aucun nouveau fichier |
| Générer, puis ingérer de nouveau | Seulement les 500 nouvelles commandes |
| Modifier une commande existante, puis ingérer | La version modifiée est extraite |
| Interrompre l'écriture du repère | Le dernier repère validé reste utilisable |

Consultez les journaux des tâches dans Airflow pour suivre les volumes et les erreurs. `make bronze` liste les
fichiers HDFS ; l'explorateur http://localhost:9870/explorer.html#/bronze permet de parcourir les dossiers.
Le téléchargement depuis cette interface peut échouer : le DataNode est accessible seulement dans le réseau Docker.

La zone bronze conserve les versions reçues. Une reprise peut réextraire un lot : il faudra gérer les doublons et
retenir la bonne version de chaque commande dans les étapes analytiques. Un filtre sur `updated_at` ne capture pas
les suppressions physiques. Pour cet atelier, les écritures du générateur sont sérialisées ; une source avec des
transactions concurrentes longues demanderait une stratégie de reprise plus robuste.

## Commandes utiles

| Commande | Action |
|---|---|
| `make help` | Afficher les commandes disponibles |
| `make ps` | Voir l'état des services |
| `make logs` | Suivre les journaux ; `Ctrl+C` quitte leur affichage |
| `make generate` | Ajouter un lot de commandes |
| `make verify` | Vérifier les services, les secrets et les droits |
| `make bronze` | Lister les fichiers dans HDFS |
| `make down` | Arrêter la pile en conservant les données |
| `make up` | Redémarrer la pile avec les images du registre |
| `make reset` | Supprimer tous les volumes, après confirmation `yes` |

## En cas de problème

| Symptôme | Solution |
|---|---|
| `make: command not found` | Installer GNU Make ; sous Windows, travailler dans Ubuntu/WSL2 |
| `Cannot connect to the Docker daemon` | Démarrer Docker Desktop et vérifier son intégration WSL2 |
| `denied` ou `manifest unknown` au téléchargement GHCR | Demander à l'enseignant de publier les images et rendre les packages publics ; sinon `make up-local` |
| Un secret manque ou garde sa valeur d'exemple | Compléter les cinq mots de passe dans `.env` |
| Mot de passe PostgreSQL refusé après modification de `.env` | La base conserve ses anciens mots de passe. Sur les données d'exercice, `make reset`, puis `make up` recrée la base et efface les données précédentes |
| Connexion `admin` refusée | Vérifier `AIRFLOW_ADMIN_PASSWORD`, puis relancer `make up` |
| Port déjà utilisé | Modifier `PG_PORT`, `AIRFLOW_PORT` ou `HDFS_UI_PORT` dans `.env`, puis `make up` et utiliser les nouveaux ports |
| Un service s'arrête ou le démarrage expire | Consulter `make ps` et `make logs`, puis vérifier la mémoire disponible |

Cette infrastructure est destinée au travail local : ports limités à votre machine, données persistées dans des
volumes Docker, identités HDFS déclaratives et échanges sans TLS. Elle ne constitue pas une configuration de production.
