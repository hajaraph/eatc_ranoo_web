#!/bin/bash

NAME="eatc_ranoo"
DJANGODIR=/home/eatc/eatc_ranoo
USER=eatc
GROUP=www-data
WORKERS=3
BIND="0.0.0.0:8000"  # Pour écouter sur toutes les interfaces
DJANGO_SETTINGS_MODULE=Rel_Compteur.settings
DJANGO_WSGI_MODULE=Rel_Compteur.wsgi
LOG_LEVEL=debug

cd $DJANGODIR
source /home/eatc/myenv/bin/activate

export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
export PYTHONPATH=$DJANGODIR:$PYTHONPATH

# Création du répertoire logs si n'existe pas
mkdir -p ${DJANGODIR}/logs

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
  --capture-output \
  --enable-stdio-inheritance \
  --reload
