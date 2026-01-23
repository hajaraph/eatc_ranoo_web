# Projet Ranoo Web

## Structure du Projet

```
.
├── .git
├── .github
├── .gitignore
├── .idea
├── .scripts
├── .venv
├── Acommune
│   ├── admin.py : Configuration de l'interface d'administration.
│   ├── apps.py : Configuration de l'application.
│   ├── migrations/ : Contient les fichiers de migration de la base de données.
│   ├── models.py : Définitions des modèles de données.
│   ├── tests.py : Tests unitaires pour l'application.
│   ├── urls.py : Routes de l'application.
│   └── views.py : Logique des vues de l'application.
├── Clients
│   ├── admin.py : Configuration de l'interface d'administration.
│   ├── apps.py : Configuration de l'application.
│   ├── migrations/ : Contient les fichiers de migration de la base de données.
│   ├── models.py : Définitions des modèles de données.
│   ├── tests.py : Tests unitaires pour l'application.
│   ├── urls.py : Routes de l'application.
│   └── views.py : Logique des vues de l'application.
├── Compteurs
│   ├── admin.py : Configuration de l'interface d'administration.
│   ├── apps.py : Configuration de l'application.
│   ├── migrations/ : Contient les fichiers de migration de la base de données.
│   ├── models.py : Définitions des modèles de données.
│   ├── tests.py : Tests unitaires pour l'application.
│   ├── urls.py : Routes de l'application.
│   └── views.py : Logique des vues de l'application.
├── Dockerfile
├── Facturation
│   ├── admin.py : Configuration de l'interface d'administration.
│   ├── apps.py : Configuration de l'application.
│   ├── migrations/ : Contient les fichiers de migration de la base de données.
│   ├── models.py : Définitions des modèles de données.
│   ├── tests.py : Tests unitaires pour l'application.
│   ├── urls.py : Routes de l'application.
│   └── views.py : Logique des vues de l'application.
├── Login
│   ├── admin.py : Configuration de l'interface d'administration.
│   ├── apps.py : Configuration de l'application.
│   ├── migrations/ : Contient les fichiers de migration de la base de données.
│   ├── models.py : Définitions des modèles de données.
│   ├── tests.py : Tests unitaires pour l'application.
│   ├── urls.py : Routes de l'application.
│   └── views.py : Logique des vues de l'application.
├── Main_Courante
│   ├── admin.py : Configuration de l'interface d'administration.
│   ├── apps.py : Configuration de l'application.
│   ├── migrations/ : Contient les fichiers de migration de la base de données.
│   ├── models.py : Définitions des modèles de données.
│   ├── tests.py : Tests unitaires pour l'application.
│   ├── urls.py : Routes de l'application.
│   └── views.py : Logique des vues de l'application.
├── Parametre
│   ├── admin.py : Configuration de l'interface d'administration.
│   ├── apps.py : Configuration de l'application.
│   ├── migrations/ : Contient les fichiers de migration de la base de données.
│   ├── models.py : Définitions des modèles de données.
│   ├── tests.py : Tests unitaires pour l'application.
│   ├── urls.py : Routes de l'application.
│   └── views.py : Logique des vues de l'application.
├── Ranoo_Config
│   ├── admin.py : Configuration de l'interface d'administration.
│   ├── apps.py : Configuration de l'application.
│   ├── migrations/ : Contient les fichiers de migration de la base de données.
│   ├── models.py : Définitions des modèles de données.
│   ├── tests.py : Tests unitaires pour l'application.
│   ├── urls.py : Routes de l'application.
│   └── views.py : Logique des vues de l'application.
├── Rel_Compteur
│   ├── asgi.py : Configuration ASGI pour l'application.
│   ├── settings.py : Configuration des paramètres de l'application.
│   ├── urls.py : Routes de l'application.
│   └── wsgi.py : Configuration WSGI pour l'application.
├── Tableau_Bord
│   ├── admin.py : Configuration de l'interface d'administration.
│   ├── apps.py : Configuration de l'application.
│   ├── migrations/ : Contient les fichiers de migration de la base de données.
│   ├── models.py : Définitions des modèles de données.
│   ├── tests.py : Tests unitaires pour l'application.
│   ├── urls.py : Routes de l'application.
│   └── views.py : Logique des vues de l'application.
├── Tasks
│   ├── celery.py : Configuration de Celery pour la gestion des tâches.
│   ├── tasks.py : Définition des tâches à exécuter.
│   └── urls.py : Routes de l'application.
├── Templates
│   ├── admin/ : Modèles pour l'interface d'administration.
│   ├── all_page/ : Modèles pour les pages générales.
│   ├── login/ : Modèles pour la page de connexion.
│   └── navbar/ : Modèles pour la barre de navigation.
├── Tenants
│   ├── admin.py : Configuration de l'interface d'administration.
│   ├── apps.py : Configuration de l'application.
│   ├── migrations/ : Contient les fichiers de migration de la base de données.
│   ├── models.py : Définitions des modèles de données.
│   ├── tests.py : Tests unitaires pour l'application.
│   └── views.py : Logique des vues de l'application.
├── docker-compose.yml
├── entrypoint.sh
└── manage.py
```

## Explication des Structures

- **.git** : Répertoire contenant les fichiers de versionnement de Git.
- **.github** : Contient les fichiers de configuration pour GitHub, comme les actions et les modèles de pull request.
- **.gitignore** : Fichier qui spécifie les fichiers et répertoires à ignorer par Git.
- **.idea** : Répertoire créé par JetBrains IDEs (comme PyCharm) pour stocker les configurations du projet.
- **.scripts** : Contient des scripts utiles pour le développement ou le déploiement.
- **.venv** : Environnement virtuel Python pour gérer les dépendances.
- **Acommune, Clients, Compteurs, Facturation, Login, Main_Courante, Parametre, Ranoo_Config, Rel_Compteur, Tableau_Bord, Tasks, Templates, Tenants** : Répertoires pour différentes fonctionnalités et modules de l'application.
- **Dockerfile** : Fichier de configuration pour créer une image Docker du projet.
- **docker-compose.yml** : Fichier de configuration pour Docker Compose, permettant de définir et d'exécuter des applications multi-conteneurs.
- **entrypoint.sh** : Script d'entrée pour le conteneur Docker.
- **manage.py** : Script principal pour interagir avec le projet Django.

## Installation

Pour installer les dépendances, exécutez les commandes suivantes :

```bash
# Cloner le dépôt
git clone <URL_DU_DEPOT>

# Accéder au répertoire du projet
cd ranoo_web

# Installer les dépendances
pip install -r requirements.txt
```

## Configuration

Ce projet utilise des variables d'environnement pour la configuration sensible.
Créez un fichier `.env` à la racine du projet (au même niveau que `manage.py`) avec le contenu suivant :

```env
SECRET_KEY=votre_cle_secrete_ici
DEBUG=True
DB_NAME=rel_compteur
DB_USER=xxxxx
DB_PASSWORD=xxxxxx
DB_HOST=localhost
DB_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1
```

## Initialisation

Pour initialiser le projet (création du locataire Public, du domaine et du Super Admin), utilisez la commande suivante :

```bash
python manage.py init_public
```

Cette commande va créer :
- Le locataire "Public".
- Le domaine `localhost` (ou celui spécifié).
- Un super utilisateur par défaut (`admin` / `admin`).

## Utilisation

Pour démarrer le serveur de développement, utilisez la commande suivante :

```bash
python manage.py runserver
```

Accédez à l'application via `http://127.0.0.1:8000/`.

## Contributions

Les contributions sont les bienvenues ! Pour contribuer :
1. Fork le projet
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/YourFeature`)
3. Commitez vos modifications (`git commit -m 'Add some feature'`)
4. Poussez vers la branche (`git push origin feature/YourFeature`)
5. Ouvrez une Pull Request

## Licence

Ce projet est sous licence MIT. Consultez le fichier `LICENSE` pour plus de détails.
