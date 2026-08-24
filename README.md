# PHENIX MANAGEMENT

Application Flask de gestion des stagiaires, dossiers et présences.

## Installation locale

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copier `.env.example` vers `.env`, puis renseigner au minimum `SECRET_KEY` et `ADMIN_PASSWORD`.

Initialiser la base :

```powershell
python init_db.py
```

Démarrer en local :

```powershell
python run.py
```

## Déploiement

### Vercel

Le fichier `vercel.json` utilise `api/index.py` comme fonction serverless Flask.
Dans les variables d'environnement du projet Vercel, définir :

```text
VERCEL=1
FLASK_CONFIG=production
SECRET_KEY=une-valeur-longue-et-aleatoire
ADMIN_PASSWORD=un-mot-de-passe-admin-long-et-unique
DATABASE_URL=postgresql://utilisateur:mot_de_passe@hote:5432/base
```

SQLite et les fichiers locaux ne sont pas persistants sur Vercel. Les documents
envoyés dans `/tmp` peuvent disparaître entre deux exécutions. Pour conserver les
documents, connecter un stockage objet (par exemple Vercel Blob ou S3) et remplacer
la sauvegarde locale dans `app/routes.py`.

Définir ces variables sur l’hébergeur :

```text
FLASK_CONFIG=production
SECRET_KEY=une-valeur-longue-et-aleatoire
ADMIN_PASSWORD=un-mot-de-passe-admin-long-et-unique
DATABASE_URL=postgresql://utilisateur:mot_de_passe@hote:5432/base
```

La commande de démarrage est fournie par `Procfile` :

```text
gunicorn --bind 0.0.0.0:$PORT run:app
```

Les fichiers téléversés doivent être stockés sur un volume persistant si l’hébergeur utilise un système de fichiers éphémère.
