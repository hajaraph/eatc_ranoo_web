from django.db import models
from django.db.models.functions import Now

from Compteurs.models import ReleveCompteur
from Facturation.models import Facture, Paiement
from Main_Courante.models import MainCourante


class Syncronisation(models.Model):
    id_syncro = models.BigAutoField(primary_key=True)
    date_syncro = models.DateField(db_default=Now(), blank=True, null=True)
    relevercompteur = models.ForeignKey(ReleveCompteur, on_delete=models.CASCADE, blank=True, null=True)
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, blank=True, null=True)
    paiement = models.ForeignKey(Paiement, on_delete=models.CASCADE, blank=True, null=True)
    main_courante = models.ForeignKey(MainCourante, on_delete=models.CASCADE, blank=True, null=True)
    message_serveur = models.CharField(max_length=30, blank=True, null=True)
