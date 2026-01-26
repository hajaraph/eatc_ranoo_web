# Utiliser une image Python officielle légère avec la version 3.12.5
FROM python:3.12.5-slim

# Définir les variables d'environnement
# Empêche Python d'écrire des fichiers .pyc
ENV PYTHONDONTWRITEBYTECODE=1
# Affiche les logs dans la console sans buffer
ENV PYTHONUNBUFFERED=1

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Installer les dépendances système nécessaires
# libpq-dev est nécessaire pour psycopg2 (PostgreSQL)
# gcc est nécessaire pour compiler certains paquets Python
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Copier le fichier des dépendances
COPY requirements.txt /app/

# Installer les dépendances Python
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copier le reste du code de l'application
COPY . /app/

# Copier le script d'entrée et le rendre exécutable
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Exposer le port sur lequel l'application va tourner
EXPOSE 8000

# Définir le point d'entrée
ENTRYPOINT ["/app/docker-entrypoint.sh"]
