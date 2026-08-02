# Deploiement du frontend sur EC2

## Repo Docker Hub requis

Le workflow publie l'image frontend dans ce repo Docker Hub :

```text
tezzosyris666/fanflight-frontend
```

Le repo Docker Hub doit exister avant de lancer le workflow. Le plus simple est de le creer en public, car l'EC2 pourra tirer l'image sans `docker login`.

Tags pousses par GitHub Actions :

- `tezzosyris666/fanflight-frontend:latest` : tag suivi par l'EC2 et Watchtower.
- `tezzosyris666/fanflight-frontend:<git-sha>` : tag immutable pour retrouver une version precise.

Pour que l'auto-update fonctionne sans modifier le compose a chaque release, il faut que le frontend de production suive le tag stable `latest`.

## Secrets GitHub requis

Dans `Settings > Secrets and variables > Actions`, ajouter :

```text
DOCKERHUB_USERNAME=tezzosyris666
DOCKERHUB_TOKEN=<token Docker Hub>
RSA=<contenu complet de la cle privee RSA pour l'EC2>
```

Le secret `RSA` doit contenir toute la cle privee, avec les lignes `-----BEGIN ...-----` et `-----END ...-----`.
Si la cle est collee sur une seule ligne avec des `\n` litteraux, le workflow la reconvertit automatiquement en cle multiligne.

Si l'etape `Configure SSH key` echoue sur `ssh-keygen -y`, alors le secret `RSA` ne contient probablement pas la bonne cle privee. A verifier :

- utiliser la cle privee, pas la cle `.pub` ;
- garder les lignes `-----BEGIN OPENSSH PRIVATE KEY-----` ou `-----BEGIN RSA PRIVATE KEY-----` ;
- ne pas ajouter de guillemets autour de la cle dans GitHub Secrets ;
- si la cle locale a une passphrase, creer une cle sans passphrase pour GitHub Actions ou utiliser une autre strategie SSH.

## Fonctionnement

Le workflow `.github/workflows/frontend-deploy.yml` se lance :

- a chaque push sur `main` ou `master` qui touche le dossier `frontend/` ;
- manuellement via `workflow_dispatch`.

Il fait ensuite :

1. build de l'image Docker du frontend Next.js ;
2. push vers Docker Hub ;
3. connexion SSH a l'EC2 `ubuntu@35.181.62.34` ;
4. installation de Docker si necessaire ;
5. creation de `/opt/fanflight/docker-compose.yml` ;
6. creation d'un `/opt/fanflight/.env` par defaut s'il n'existe pas encore ;
7. copie de la configuration monitoring dans `/opt/fanflight/monitoring` ;
8. lancement de Postgres, Spark master, Spark worker, API, frontend, Prometheus, Grafana, exporters et Watchtower ;
9. execution de health checks locaux sur le frontend, l'API, Prometheus et Grafana ;
10. lancement de Watchtower, qui surveille Docker Hub toutes les 60 secondes.

## Variables EC2

Le fichier `/opt/fanflight/.env` est conserve entre les deploys. Le workflow en cree un par defaut s'il n'existe pas encore :

```text
DB_NAME=airline_data
DB_USER=root
DB_PASSWORD=password_test
DB_HOST=db
DB_PORT=5432
API_KEY_SERAPI=
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=fanflight-admin
```

Apres le premier deploy, se connecter a l'EC2 pour mettre les vraies valeurs si besoin :

```bash
ssh -i project.pem ubuntu@35.181.62.34
sudo nano /opt/fanflight/.env
cd /opt/fanflight
sudo docker compose up -d
```

## Monitoring Grafana / Prometheus

Le deploy EC2 lance aussi une stack d'observabilite Docker Compose :

- `prometheus` collecte les metriques et les resultats de probes.
- `alertmanager` recoit les alertes de Prometheus (regles dans `monitoring/prometheus/rules/fanflight-alerts.yml`) et les envoie par email (config dans `monitoring/alertmanager/alertmanager.yml`).
- `grafana` expose un dashboard pre-provisionne sur le port `3001`.
- `blackbox-exporter` teste les endpoints HTTP internes.
- `node-exporter` remonte la sante de l'EC2 : CPU, memoire, disque.
- `cadvisor` remonte la sante des conteneurs Docker.
- `postgres-exporter` remonte l'etat de Postgres.

Cette meme stack (sans Watchtower) est aussi disponible directement dans le `docker-compose.yml` principal pour le developpement local — plus besoin de reseau externe ni de compose separe.

Endpoints testes en continu par Prometheus :

```text
http://frontend:3000/
http://backend-api:8000/ready
http://spark-master:8080/
http://spark-worker:8081/
```

Grafana est accessible sur :

```text
http://35.181.62.34:3001
```

Les identifiants par defaut viennent de `/opt/fanflight/.env` :

```text
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=fanflight-admin
```

Changer `GRAFANA_ADMIN_PASSWORD` apres le premier deploy, puis relancer Grafana :

```bash
ssh -i project.pem ubuntu@35.181.62.34
sudo nano /opt/fanflight/.env
cd /opt/fanflight
sudo docker compose up -d grafana
```

Prometheus est volontairement bind en local sur l'EC2 (`127.0.0.1:9090`) pour ne pas l'exposer publiquement. Pour y acceder ponctuellement :

```bash
ssh -i project.pem -L 9090:127.0.0.1:9090 ubuntu@35.181.62.34
```

Puis ouvrir :

```text
http://localhost:9090
```

## Test local avant prod

Un compose local prod-like est disponible dans `docker-compose.local.yml`. Il build les memes images depuis le code local, lance Postgres, Spark master, Spark worker, API, frontend, Prometheus, Grafana et les exporters, mais sans Watchtower.

Preparation :

```bash
cp .env.example .env
```

Adapter `.env` si besoin, notamment `API_KEY_SERAPI`.

Lancer tout en local :

```bash
docker compose -f docker-compose.local.yml up --build
```

Tester les services :

```bash
curl http://localhost:3000
curl http://localhost:8000/docs
curl http://localhost:8000/ready
curl http://localhost:9090/-/ready
curl http://localhost:3001/api/health
docker compose -f docker-compose.local.yml ps
```

Voir les logs utiles :

```bash
docker compose -f docker-compose.local.yml logs -f db
docker compose -f docker-compose.local.yml logs -f backend-api
docker compose -f docker-compose.local.yml logs -f spark-master
docker compose -f docker-compose.local.yml logs -f prometheus
docker compose -f docker-compose.local.yml logs -f grafana
```

Nettoyer le test local, y compris la base locale :

```bash
docker compose -f docker-compose.local.yml down -v
```

## Verifications sur l'EC2

```bash
ssh -i project.pem ubuntu@35.181.62.34
sudo docker compose -f /opt/fanflight/docker-compose.yml ps
sudo docker logs fanflight_frontend
sudo docker logs backend_api
sudo docker logs spark-master
sudo docker logs spark-worker
sudo docker logs fanflight_prometheus
sudo docker logs fanflight_grafana
sudo docker logs fanflight_watchtower
```

Le frontend doit etre accessible sur :

```text
http://35.181.62.34
```

Il faut aussi que le security group AWS de l'EC2 autorise l'entree TCP `80` depuis Internet.
Pour acceder a Grafana depuis l'exterieur, autoriser aussi l'entree TCP `3001` uniquement depuis les IP d'administration.
Les autres ports exposes par le compose sont `8000` pour l'API, `8080` pour Spark master, `8081` pour Spark worker, `7077` pour Spark et `5432` pour Postgres. Ne les ouvrir dans AWS que si vous en avez vraiment besoin.
Prometheus est disponible seulement depuis l'EC2 sur `127.0.0.1:9090`.

Postgres est volontairement pinne sur `postgres:17`. Ne pas utiliser `postgres:latest` en production : un changement de version majeure peut rendre le volume existant incompatible sans migration `pg_upgrade`.
