#!/bin/bash
set -e

echo "Déploiement en cours ..."

# Pull the latest version of the app
echo "Récupération des dernières modifications de la branche principale..."
git pull origin main --no-rebase
echo "Nouveaux changements copiés sur le serveur !"

# Activate Virtual Env
echo "Activation de l'environnement virtuel 'myenv'..."
source /home/eatc/myenv/bin/activate

# Move to the project directory
echo "Déplacement vers le répertoire du projet..."
cd /home/eatc/eatc_ranoo/

# Install dependencies
echo "Installation des dépendances..."
pip install -r requirements.txt --no-input

# Set executable permissions for gunicorn_start.sh
echo "Configuration des permissions d'exécution pour gunicorn_start.sh..."
chmod +x /home/eatc/eatc_ranoo/gunicorn_start.sh

# Serve Static Files
echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# Run Database migration
echo "Exécution des migrations de la base de données..."
python manage.py makemigrations
python manage.py migrate_schemas

# Restart Gunicorn
echo "Redémarrage du service Gunicorn..."
sudo systemctl daemon-reload
sudo systemctl restart gunicorn

# Check Gunicorn status
echo "Vérification du statut de Gunicorn..."
systemctl status gunicorn --no-pager

# Deactivate Virtual Env
echo "Désactivation de l'environnement virtuel 'myenv'..."
deactivate

echo "Déploiement terminé !"
