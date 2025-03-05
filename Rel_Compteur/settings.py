import os
from datetime import timedelta
from pathlib import Path

from django.contrib import messages

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-iy)pk3bxm664w4$_vxm)$0$9&!grq0h%f*8!^sshd(f53uo25b'

DEBUG = True

# Applications partagées entre tous les tenants
SHARED_APPS = [
    'django_tenants',
    'Tenants',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django_extensions',
    'django_browser_reload',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_celery_results',
    'Acommune',
    'Login'
]

# Applications spécifiques aux tenants
TENANT_APPS = [
    'Clients',
    'Compteurs',
    'Facturation',
    'Main_Courante',
    'Parametre',
    'Tableau_Bord'
]

INSTALLED_APPS = SHARED_APPS + TENANT_APPS


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_browser_reload.middleware.BrowserReloadMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django_tenants.middleware.main.TenantMainMiddleware',
    'Tenants.middleware.AdminSchemaMiddleware'
]


ALLOWED_HOSTS = [
    'app.eatc.me',
    'www.app.eatc.me',
    '89.116.38.149',
    '10.0.2.2',
    'localhost'
]

CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    'https://app.eatc.me',
    'https://www.app.eatc.me',
    'http://89.116.38.149:8000',
    'http://127.0.0.1:8000',
    'http://localhost:3000',
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    'http://89.116.38.149:8000',
    'http://127.0.0.1:8000',
]

CSRF_TRUSTED_ORIGINS = [
    'https://app.eatc.me',
    'https://www.app.eatc.me',
]

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'Lax'

ROOT_URLCONF = 'Rel_Compteur.urls'

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
        'NAME': 'rel_compteur',
        'USER': 'postgres',
        'PASSWORD': '12121212',
        # 'USER': 'eatcrano',
        # 'PASSWORD': 'eatc301',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}


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

STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

MEDIA_URL = '/media/'

MEDIA_ROOT = os.path.join(BASE_DIR, 'static/media')

APPEND_SLASH = True

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ]
}

# Configuration JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id_utilisateur',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# Configurations de Celery
CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'django-db'

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

TENANT_MODEL = "Tenants.Entreprise"
TENANT_DOMAIN_MODEL = "Tenants.Domain"
PUBLIC_SCHEMA_NAME = "public"
AUTH_USER_MODEL = "Tenants.Utilisateur"
SITE_ID = 1


# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'console': {
#             'class': 'logging.StreamHandler',
#         },
#     },
#     'loggers': {
#         'django': {
#             'handlers': ['console'],
#             'level': 'INFO',
#             'propagate': True,
#         },
#         'Tenants.middleware': {
#             'handlers': ['console'],
#             'level': 'DEBUG',
#             'propagate': False,
#         },
#     },
# }
