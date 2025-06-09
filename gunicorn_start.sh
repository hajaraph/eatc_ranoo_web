#!/bin/bash

NAME="eatc_ranoo"
DJANGODIR=/home/eatc/eatc_ranoo
USER=eatc
GROUP=eatc
WORKERS=3
BIND=unix:/home/eatc/eatc_ranoo/run/gunicorn.sock
DJANGO_SETTINGS_MODULE=Rel_Compteur.settings
DJANGO_WSGI_MODULE=Rel_Compteur.wsgi
LOG_LEVEL=debug

cd $DJANGODIR
source /home/eatc/myenv/bin/activate

export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
export PYTHONPATH=$DJANGODIR:$PYTHONPATH

# Création du répertoire run si n'existe pas
mkdir -p /home/eatc/eatc_ranoo/run/

# Démarrage de Gunicorn
exec /home/eatc/myenv/bin/gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --workers $WORKERS \
  --user=$USER \
  --group=$GROUP \
  --bind=$BIND \
  --log-level=$LOG_LEVEL \
  --log-file=/home/eatc/eatc_ranoo/logs/gunicorn.log \
  --access-logfile=/home/eatc/eatc_ranoo/logs/access.log
