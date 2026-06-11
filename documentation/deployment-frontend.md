# Deploiement Docker sur EC2

## Repos Docker Hub requis

Le workflow publie les images internes dans ces repos Docker Hub :

```text
tezzosyris666/fanflight-frontend
tezzosyris666/fanflight-backend-api
tezzosyris666/fanflight-spark
```

Ces repos Docker Hub doivent exister avant de lancer le workflow. Le plus simple est de les creer en public, car l'EC2 pourra tirer les images sans `docker login`.

Tags pousses par GitHub Actions :

- `tezzosyris666/fanflight-frontend:latest` : tag suivi par l'EC2 et Watchtower.
- `tezzosyris666/fanflight-backend-api:latest` : tag suivi par l'EC2 et Watchtower.
- `tezzosyris666/fanflight-spark:latest` : tag suivi par l'EC2 et Watchtower.
- `tezzosyris666/fanflight-frontend:<git-sha>` : tag immutable pour retrouver une version precise.
- `tezzosyris666/fanflight-backend-api:<git-sha>` : tag immutable pour retrouver une version precise.
- `tezzosyris666/fanflight-spark:<git-sha>` : tag immutable pour retrouver une version precise.

Pour que l'auto-update fonctionne sans modifier le compose a chaque release, les services de production suivent le tag stable `latest`.

## Secrets GitHub requis

Dans `Settings > Secrets and variables > Actions`, ajouter :

```text
DOCKERHUB_USERNAME=tezzosyris666
DOCKERHUB_TOKEN=<token Docker Hub>
RSA=<contenu complet de la cle privee RSA pour l'EC2>
```

Le secret `RSA` doit contenir toute la cle privee, avec les lignes `-----BEGIN ...-----` et `-----END ...-----`.
Si la cle est collee sur une seule ligne avec des `\n` litteraux, le workflow la reconvertit automatiquement en cle multiligne.

Si le log affiche `SSH_PRIVATE_KEY:` vide, alors le secret `RSA` n'est pas disponible pour le workflow. A verifier :

- le secret s'appelle exactement `RSA` ;
- il est cree dans le meme repository GitHub que celui qui lance l'action ;
- il est dans `Settings > Secrets and variables > Actions`, pas seulement dans un autre environnement ;
- le workflow n'est pas lance depuis un fork, car GitHub ne transmet pas les secrets aux workflows de forks non approuves.

Si l'etape `Configure SSH key` echoue sur `ssh-keygen -y`, alors le secret `RSA` ne contient probablement pas la bonne cle privee. A verifier :

- utiliser la cle privee, pas la cle `.pub` ;
- garder les lignes `-----BEGIN OPENSSH PRIVATE KEY-----` ou `-----BEGIN RSA PRIVATE KEY-----` ;
- ne pas ajouter de guillemets autour de la cle dans GitHub Secrets ;
- si la cle locale a une passphrase, creer une cle sans passphrase pour GitHub Actions ou utiliser une autre strategie SSH.

## Fonctionnement

Le workflow `.github/workflows/frontend-deploy.yml` se lance :

- a chaque push sur `main` ou `master` qui touche `frontend/`, `API/` ou `data-pipeline/spark/` ;
- manuellement via `workflow_dispatch`.

Il fait ensuite :

1. build des images Docker `frontend`, `backend-api` et `spark` ;
2. push des images vers Docker Hub ;
3. connexion SSH a l'EC2 `ubuntu@35.181.62.34` ;
4. installation de Docker si necessaire ;
5. creation de `/opt/fanflight/docker-compose.yml` ;
6. creation d'un `/opt/fanflight/.env` par defaut s'il n'existe pas encore ;
7. lancement de Postgres, Spark master, Spark worker, API, frontend et Watchtower ;
8. lancement de Watchtower, qui surveille Docker Hub toutes les 60 secondes.

## Variables EC2

Le fichier `/opt/fanflight/.env` est conserve entre les deploys. Le workflow en cree un par defaut s'il n'existe pas encore :

```text
DB_NAME=airline_data
DB_USER=root
DB_PASSWORD=password_test
DB_HOST=db
DB_PORT=5432
API_KEY_SERAPI=
```

Apres le premier deploy, se connecter a l'EC2 pour mettre les vraies valeurs si besoin :

```bash
ssh -i project.pem ubuntu@35.181.62.34
sudo nano /opt/fanflight/.env
cd /opt/fanflight
sudo docker compose up -d
```

## Verifications sur l'EC2

```bash
ssh -i project.pem ubuntu@35.181.62.34
sudo docker compose -f /opt/fanflight/docker-compose.yml ps
sudo docker logs fanflight_frontend
sudo docker logs backend_api
sudo docker logs spark-master
sudo docker logs spark-worker
sudo docker logs fanflight_watchtower
```

Le frontend doit etre accessible sur :

```text
http://35.181.62.34
```

Il faut aussi que le security group AWS de l'EC2 autorise l'entree TCP `80` depuis Internet.
Les autres ports exposes par le compose sont `8000` pour l'API, `8080` pour Spark master, `8081` pour Spark worker, `7077` pour Spark et `5432` pour Postgres. Ne les ouvrir dans AWS que si vous en avez vraiment besoin.
