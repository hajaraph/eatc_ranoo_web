from django.db import models

from Tenants.models import Utilisateur


def upload_to_compteur(instance, filename):
    return f'compteurs/{instance.num_compteur_id}/{filename}'


class Compteur(models.Model):
    num_compteur = models.CharField(max_length=255, primary_key=True, blank=False)
    marque_compteur = models.CharField(max_length=100, blank=True, null=True)
    modele_compteur = models.CharField(max_length=100, blank=True, null=True)
    DN_compteur = models.CharField(max_length=100, blank=True, null=True)
    origin_compteur = models.CharField(max_length=100, blank=True, null=True)
    hors_service = models.BooleanField(default=False)


class ReleveCompteur(models.Model):
    id_releve = models.BigAutoField(primary_key=True)
    date_releve = models.DateField(blank=True, null=True)
    volume = models.IntegerField(blank=True, null=True)
    conso = models.IntegerField(blank=True, null=True)
    image_compteur = models.ImageField(upload_to=upload_to_compteur, blank=True)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.PROTECT, blank=True, null=True)
    num_compteur = models.ForeignKey(Compteur, blank=False, related_name='relevecompteurs', on_delete=models.CASCADE)
