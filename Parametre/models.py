from django.db import models
from django.db.models.functions import Now

from Tenants.models import Utilisateur


class Historique(models.Model):
    id_historique = models.BigAutoField(primary_key=True)
    date_historique = models.DateTimeField(db_default=Now(), blank=False)
    type_historique = models.CharField(max_length=100, blank=False)
    utilisateur = models.ForeignKey(Utilisateur, blank=False, on_delete=models.PROTECT)
