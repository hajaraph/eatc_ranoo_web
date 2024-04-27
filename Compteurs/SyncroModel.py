from django.db import models
from django.db.models.functions import Now

from Compteurs.models import ReleveCompteur
from Facturation.models import Facture, Paiement
from Main_Courante.models import MainCourante


class SyncroModel(models.Model):
    id_syncro = models.BigIntegerField(primary_key=True)
    relever = models.ForeignKey(ReleveCompteur, on_delete=models.CASCADE, null=True, blank=True)
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, null=True, blank=True)
    paiement = models.ForeignKey(Paiement, on_delete=models.CASCADE, null=True, blank=True)
    main_courante = models.ForeignKey(MainCourante, on_delete=models.CASCADE, null=True, blank=True)
    date_syncro = models.DateTimeField(db_default=Now(), editable=False, blank=False, null=False)
