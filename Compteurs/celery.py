from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Réglage de l'environnement Django pour que Celery puisse trouver les paramètres de votre projet
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Rel_Compteur.settings')

# Création de l'application Celery
app = Celery('Rel_Compteur/Compteur')

# Chargement des configurations de votre projet Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-découverte des tâches dans tous les modules `tasks.py` de votre projet Django
app.autodiscover_tasks()
