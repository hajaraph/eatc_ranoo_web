#!/bin/bash

NAME="ranoo_web"
DJANGODIR=/home/eatc/eatc_ranoo
USER=eatc
GROUP=eatc
NUM_WORKERS=3
TIMEOUT=300
DJANGO_WSGI_MODULE=Rel_Compteur.wsgi
# shellcheck disable=SC2034
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
export DJANGO_SETTINGS_MODULE=Rel_Compteur.settings
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
  --workers $NUM_WORKERS \
  --timeout $TIMEOUT \
  --user=$USER \
  --group=$GROUP \
  --bind=0.0.0.0:8000 \
  --log-level=debug \
  --log-file=${DJANGODIR}/logs/gunicorn.log \
  --worker-class=sync \
  --max-requests=1000 \
  --max-requests-jitter=50 \
  --graceful-timeout=180
