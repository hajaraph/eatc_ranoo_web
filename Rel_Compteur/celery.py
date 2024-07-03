from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Définir le module de configuration par défaut de Django pour Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Rel_Compteur.settings')

app = Celery('Rel_Compteur')

# Charger les paramètres de configuration de Django dans Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
