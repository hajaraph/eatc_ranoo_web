import os
from datetime import timedelta
from pathlib import Path
from decouple import config, Csv

from django.contrib import messages

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)

# Applications partagées entre tous les tenants (public schema)
SHARED_APPS = (
    'django_tenants',  # Doit être en premier
    'Tenants',  # Votre application tenant
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django_extensions',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'drf_spectacular',
    'Acommune',
    'Login',
    'django_celery_results',
)

# Applications spécifiques aux tenants
TENANT_APPS = (
    'Clients',
    'Compteurs',
    'Recette',
    'Depense',
    'Facturation',
    'Main_Courante',
    'Parametre',
    'Ranoo_Config',
    'Rubrique',
    'Tableau_Bord',
)

# Combinaison des applications
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

# Configuration pour django-tenants
TENANT_MODEL = "Tenants.Entreprise"
TENANT_DOMAIN_MODEL = "Tenants.Domain"
DATABASE_ENGINE = 'django_tenants.postgresql_backend'
PUBLIC_SCHEMA_NAME = 'public'
PUBLIC_SCHEMA_URLCONF = 'Rel_Compteur.urls'
ROOT_URLCONF = 'Rel_Compteur.urls'

# Configuration des middlewares (TenantMainMiddleware doit être en premier)
MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django_tenants.middleware.main.TenantMainMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'django_browser_reload.middleware.BrowserReloadMiddleware',
]


ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='app.eatc.me,www.app.eatc.me,localhost,127.0.0.1', cast=Csv())


CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    'https://app.eatc.me',
    'https://www.app.eatc.me',
    'http://127.0.0.1:8000',
    'http://localhost:8000'
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    'https://app.eatc.me',
    'https://www.app.eatc.me',
    'http://127.0.0.1:8000',
    'http://localhost:8000'
]

CSRF_TRUSTED_ORIGINS = [
    'https://app.eatc.me',
    'https://www.app.eatc.me',
    'http://127.0.0.1:8000',
    'http://localhost:8000'
]

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Traefik termine TLS puis proxie en HTTP vers Gunicorn.
# Ces settings permettent a Django de reconstruire les URLs
# en HTTPS via build_absolute_uri() (corrige le blocage
# Chrome/Edge "can't download file securely").
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True



TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': [BASE_DIR / 'Templates'],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'Compteurs.context_processors.alertes_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'Rel_Compteur.wsgi.application'

DATABASE_ROUTERS = [
    'django_tenants.routers.TenantSyncRouter'
]

DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default=5432, cast=int),
    }
}


# Cache configuration - Centralisé sur Redis pour synchronisation inter-workers
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_CACHE_URL', default='redis://redis:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 300,  # 5 minutes
    }
}

# Session configuration - Optimisée via Redis
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'fr-FR'

TIME_ZONE = 'Indian/Antananarivo'

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
]

MESSAGE_TAGS = {
    messages.DEBUG: 'danger',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": os.path.join(BASE_DIR, 'static/media'),
            "base_url": MEDIA_URL,
        }
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        "OPTIONS": {
            "location": STATIC_ROOT,
            "base_url": STATIC_URL,
        }
    },
}

APPEND_SLASH = True

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Configuration drf-spectacular pour OpenAPI/Swagger
SPECTACULAR_SETTINGS = {
    'TITLE': 'EATC API',
    'DESCRIPTION': 'API pour le système de gestion de compteurs d eau EATC',
    'VERSION': '1.0.0',
    'SERVE_INCLUDES': [
        {'url': 'http://localhost:8000/api/', 'description': 'Development server'},
    ],
    'SCHEMA_PATH_PREFIX': '/api',
    'COMPONENT_SPLIT_REQUEST': True,
    'TAGS': [
        {'name': 'Authentification', 'description': 'Endpoints d authentification'},
        {'name': 'Compteurs', 'description': 'Gestion des compteurs et relevés'},
        {'name': 'Clients', 'description': 'Gestion des clients et contrats'},
        {'name': 'Facturation', 'description': 'Gestion des factures et paiements'},
        {'name': 'Synchronisation', 'description': 'Synchronisation mobile offline-first'},
        {'name': 'Anomalies', 'description': 'Gestion des anomalies et incidents'},
        {'name': 'Tableau de Bord', 'description': 'Statistiques et KPIs'},
    ],
}

# Configuration JWT - Optimisée pour applications mobiles offline
SIMPLE_JWT = {
    # Access token court (15 min) - Sécurité maximale
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    
    # Refresh token long (30 jours) - Permet travail offline
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    
    # Rotation activée - Sécurité : nouveau refresh token à chaque usage
    'ROTATE_REFRESH_TOKENS': True,
    
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id_utilisateur',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
}

# Configurations de Celery
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Indian/Antananarivo'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 600  # 10 minutes max par tâche

# Configuration Flower (monitoring Celery)
FLOWER_PORT = 5555
FLOWER_BASIC_AUTH = config('FLOWER_BASIC_AUTH', default='')
FLOWER_UNAUTHENTICATED = config('FLOWER_UNAUTHENTICATED', default='False')

# Configuration Sentry (monitoring et alertes)
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment=config('ENVIRONMENT', default='production'),
    )
AUTH_USER_MODEL = "Tenants.Utilisateur"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'debug.log'),
            'formatter': 'simple',
        },
    },
    'loggers': {
        '': {  # Root logger
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'django': {
            'handlers': ['console', 'file'],
            'level': config('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'gunicorn.error': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': True,
        },
        'gunicorn.access': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

# Création du dossier logs s'il n'existe pas
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)
