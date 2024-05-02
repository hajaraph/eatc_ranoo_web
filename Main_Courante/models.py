from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

from Clients.communes import Commune
from Clients.models import Client
from Login.models import Utilisateur


def upload_to_mc(instance, filename):
    return f'mc/{instance.main_courante.pk}/{filename}'


class MainCourante(models.Model):
    id_mc = models.BigAutoField(primary_key=True)
    date_mc = models.DateField(default=timezone.now, blank=False)
    type_anomalie = models.CharField(max_length=50, blank=False)
    longitude_mc = models.CharField(max_length=50, blank=True, null=True)
    latitude_mc = models.CharField(max_length=50, blank=True, null=True)
    description_mc = models.CharField(max_length=255, blank=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True)
    cp_commune = models.ForeignKey(Commune, on_delete=models.CASCADE, null=True, blank=True)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.PROTECT, blank=False)


class StatutMC(models.Model):
    id_statut = models.BigAutoField(primary_key=True)
    en_cours = models.BooleanField(default=False, blank=False)
    realise = models.BooleanField(default=False, blank=False)
    non_traite = models.BooleanField(default=True, blank=False)
    date_status = models.DateField(db_default=Now(), blank=True, null=True)
    main_courante = models.ForeignKey(MainCourante, on_delete=models.CASCADE, related_name='statuts')


class PhotoMC(models.Model):
    id_photos = models.BigAutoField(primary_key=True)
    photo_anomalie = models.ImageField(upload_to=upload_to_mc, blank=True)
    main_courante = models.ForeignKey(MainCourante, on_delete=models.CASCADE, blank=True, related_name='photomcs')


class SuivieMC(models.Model):
    id_suivie = models.BigAutoField(primary_key=True)
    date_suivie = models.DateTimeField(db_default=Now(), blank=False)
    commentaire_suivie = models.CharField(max_length=200, blank=False)
    main_courante = models.ForeignKey(MainCourante, on_delete=models.CASCADE, blank=False, related_name='suiviemcs')
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.PROTECT)
