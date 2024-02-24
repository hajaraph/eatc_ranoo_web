from django.apps import AppConfig

from Compteurs.schedule.tasks import scheduler


class VotreAppConfig(AppConfig):
    name = 'Compteurs.schedule'

    def ready(self):
        scheduler.start()
