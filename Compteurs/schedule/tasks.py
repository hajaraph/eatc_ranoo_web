from apscheduler.schedulers.background import BackgroundScheduler
# from apscheduler.triggers.interval import IntervalTrigger
from django_apscheduler.jobstores import DjangoJobStore

from Compteurs.models import ReleveCompteur, Utilisateur, Compteur

scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")


def creer_releve_compteur_auto():
    utilisateurs = Utilisateur.objects.filter(role_id=3)

    for utilisateur in utilisateurs:
        compteurs = Compteur.objects.filter(relevecompteurs__utilisateur_id=utilisateur.id_utilisateur)
        for compteur in compteurs:
            ReleveCompteur.objects.create(
                utilisateur_id=utilisateur.id_utilisateur,
                num_compteur=compteur,
                date_releve=None,
                volume=None,
                conso=None,
                image_compteur=None
            )
#

# scheduler.add_job(
#     creer_releve_compteur_auto,
#     trigger=IntervalTrigger(seconds=1),
#     id="creer_releve_compteur_auto",
#     name="Créer relevé compteur automatiquement toutes les 2 secondes",
#     replace_existing=True,
# )
