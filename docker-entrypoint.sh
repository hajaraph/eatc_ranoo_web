#!/bin/sh

echo "=== Waiting for PostgreSQL to be ready..."

MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "=== PostgreSQL is ready!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "PostgreSQL not ready yet... retry $RETRY_COUNT/$MAX_RETRIES"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "=== ERROR: PostgreSQL did not become ready in time. Exiting."
    exit 1
fi

# Appliquer les migrations
echo "=== Starting migration"
python manage.py migrate

# Collecter les fichiers statiques
python manage.py collectstatic --noinput

# Démarrer l'application
exec "$@"
