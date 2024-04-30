from django.db import models

from django.db.models.functions import Now
from Login.models import Utilisateur


def upload_to_compteur(instance, filename):
    return f'compteurs/{instance.num_compteur_id}/{filename}'


class Compteur(models.Model):
    num_compteur = models.CharField(max_length=255, primary_key=True, blank=False)
    marque_compteur = models.CharField(max_length=30, blank=False)
    modele_compteur = models.CharField(max_length=30, blank=False)
    DN_compteur = models.CharField(max_length=5, blank=False)
    origin_compteur = models.CharField(max_length=20, blank=False)


class ReleveCompteur(models.Model):
    id_releve = models.BigAutoField(primary_key=True)
    date_releve = models.DateField(blank=True, null=True)
    volume = models.IntegerField(blank=True, null=True)
    conso = models.IntegerField(blank=True, null=True)
    image_compteur = models.ImageField(upload_to=upload_to_compteur, blank=True)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.PROTECT, blank=True, null=True)
    num_compteur = models.ForeignKey(Compteur, blank=False, related_name='relevecompteurs', on_delete=models.CASCADE)


class Syncronisation(models.Model):
    id_syncro = models.BigAutoField(primary_key=True)
    date_syncro = models.DateField(db_default=Now(), blank=True, null=True)
    relevercompteur = models.ForeignKey(ReleveCompteur, on_delete=models.CASCADE, blank=True, null=True)

