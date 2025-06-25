#!/bin/bash

NAME="eatc_ranoo"
DJANGODIR=/home/eatc/eatc_ranoo
USER=eatc
GROUP=www-data
WORKERS=3
TIMEOUT=300  # Augmenté à 5 minutes
GRACEFUL_TIMEOUT=320  # 5 minutes + 20 secondes
KEEPALIVE=5
MAX_REQUESTS=1000
MAX_REQUESTS_JITTER=50
BIND="0.0.0.0:8000"  # Pour écouter sur toutes les interfaces
DJANGO_SETTINGS_MODULE=Rel_Compteur.settings
DJANGO_WSGI_MODULE=Rel_Compteur.wsgi
LOG_LEVEL=debug

# shellcheck disable=SC2006
echo "Starting $NAME as `whoami`"

# Activation de l'environnement virtuel
echo "Activating virtual environment..."
# shellcheck disable=SC2164
cd $DJANGODIR
source /home/eatc/myenv/bin/activate

# Configuration de l'environnement
echo "Setting environment variables..."
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
export PYTHONPATH=$DJANGODIR:$PYTHONPATH

# Création du répertoire logs
echo "Creating log directory..."
mkdir -p ${DJANGODIR}/logs

# Vérification de Gunicorn
echo "Checking Gunicorn installation..."
which gunicorn || { echo "Gunicorn not found. Please install it with pip install gunicorn"; exit 1; }

echo "Starting Gunicorn..."
# Démarrage de Gunicorn
exec /home/eatc/myenv/bin/gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --workers $WORKERS \
  --user=$USER \
  --group=$GROUP \
  --bind=$BIND \
  --log-level=$LOG_LEVEL \
  --log-file=${DJANGODIR}/logs/gunicorn.log \
  --access-logfile=${DJANGODIR}/logs/access.log \
  --error-logfile=${DJANGODIR}/logs/error.log \
  --timeout=$TIMEOUT \
  --graceful-timeout=$GRACEFUL_TIMEOUT \
  --keep-alive=$KEEPALIVE \
  --max-requests=$MAX_REQUESTS \
  --max-requests-jitter=$MAX_REQUESTS_JITTER \
  --capture-output \
  --enable-stdio-inheritance \
  --preload
