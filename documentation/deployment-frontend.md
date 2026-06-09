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
6. lancement du frontend sur le port HTTP `80` ;
7. lancement de Watchtower, qui surveille Docker Hub toutes les 60 secondes.

## Verifications sur l'EC2

```bash
ssh -i project.pem ubuntu@35.181.62.34
sudo docker compose -f /opt/fanflight/docker-compose.yml ps
sudo docker logs fanflight_frontend
sudo docker logs fanflight_watchtower
```

Le frontend doit etre accessible sur :

```text
http://35.181.62.34
```

Il faut aussi que le security group AWS de l'EC2 autorise l'entree TCP `80` depuis Internet.
