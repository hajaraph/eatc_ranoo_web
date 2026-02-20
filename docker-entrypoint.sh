#!/bin/sh

# Attendre que la base de données soit prête
if [ "$DB_HOST" = "db" ]; then
    echo "Waiting for postgres..."

    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# Appliquer les migrations
python manage.py migrate

# Collecter les fichiers statiques (optionnel, décommentez si nécessaire)
python manage.py collectstatic --noinput

# Démarrer l'application
# Note: La commande "command" dans docker-compose remplacera "$@" s'il est utilisé à la fin,
# mais ici nous utilisons exec pour passer la main à la commande spécifiée dans le Dockerfile ou docker-compose.
exec "$@"
