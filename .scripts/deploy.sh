#!/bin/bash
set -e

echo "========================================"
echo "🚀  Démarrage du déploiement..."
echo "========================================"

# Récupération de la dernière version de l'application
echo "🔄 Récupération des dernières modifications depuis la branche main..."
git pull origin main --no-rebase
echo "✅ Nouvelles modifications copiées sur le serveur !"

# Activation de l'environnement virtuel
echo "🔌 Activation de l'environnement virtuel 'myenv'..."
source /home/eatc/myenv/bin/activate

# Déplacement vers le répertoire du projet
echo "📂 Déplacement vers le répertoire du projet..."
cd /home/eatc/eatc_ranoo/

# Installation des dépendances
echo "📦 Installation des dépendances..."
pip install --no-deps -r requirements.txt --no-input

# Définition des permissions d'exécution pour gunicorn_start.sh
echo "🔒 Définition des permissions d'exécution pour gunicorn_start.sh..."
chmod +x /home/eatc/eatc_ranoo/gunicorn_start.sh

# Collecte des fichiers statiques
echo "🖼️  Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# Exécution des migrations de base de données
echo "💾 Exécution des migrations de base de données..."
python manage.py makemigrations
python manage.py migrate_schemas

# Vérification du statut de Gunicorn
echo "🔍 Vérification du statut de Gunicorn..."
systemctl status gunicorn --no-pager

# Désactivation de l'environnement virtuel
echo "🔌 Désactivation de l'environnement virtuel 'myenv'..."
deactivate

echo "========================================"
echo "✅ Déploiement terminé avec succès !"
echo "========================================"
