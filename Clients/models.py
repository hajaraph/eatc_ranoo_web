from django.db import models

from Compteurs.models import Compteur
from Tenants.models import Utilisateur
from Acommune.models import Commune

def upload_to_client(instance, filename):
    return f'clients/{instance.client.id_client}/{filename}'


class TypeClient(models.Model):
    id_type_client = models.BigAutoField(primary_key=True)
    designation_client = models.CharField(max_length=20, blank=False)


class Client(models.Model):
    id_client = models.BigAutoField(primary_key=True)
    nom_client = models.CharField(max_length=50, blank=False)
    prenom_client = models.CharField(max_length=30, blank=True, null=True)
    tel1_client = models.CharField(max_length=10, blank=False, null=True)
    tel2_client = models.CharField(max_length=10, blank=False, null=True)
    email_client = models.TextField(max_length=60, blank=False, null=True)
    adresse_client = models.TextField(max_length=100, blank=False)
    pays_client = models.CharField(max_length=30, blank=False)
    compte_actif = models.BooleanField(default=False, blank=False)
    cp_commune = models.ForeignKey(Commune, on_delete=models.PROTECT, related_name='clients', blank=False)
    type_client = models.ForeignKey(TypeClient, on_delete=models.PROTECT, related_name='clients', blank=False)


class PieceClient(models.Model):
    id_piece = models.BigAutoField(primary_key=True)
    pieces_client = models.FileField(upload_to=upload_to_client, blank=True)
    designation = models.CharField(max_length=20, blank=False)
    client = models.ForeignKey(Client, related_name='piececlients', on_delete=models.CASCADE, blank=False)


class Contrat(models.Model):
    num_contrat = models.CharField(max_length=30, primary_key=True, blank=False)
    date_debut = models.DateField(blank=False)
    date_fin = models.DateField(null=True, blank=True)
    adresse_contrat = models.CharField(max_length=100, blank=False)
    pays_contrat = models.CharField(max_length=50, blank=False)
    cp_commune = models.ForeignKey(Commune, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, related_name='contrats', on_delete=models.CASCADE)
    num_compteur = models.ForeignKey(Compteur, on_delete=models.CASCADE, related_name='contrats')
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.PROTECT, related_name='contrats', null=True)
