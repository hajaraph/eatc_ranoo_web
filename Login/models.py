from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Now

from Clients.communes import Commune


def upload_to_utilisateur(instance, filename):
    return f'utilisateur/{instance.id_utilisateur}/{filename}'


class Role(models.Model):
    id_role = models.BigAutoField(primary_key=True)
    role = models.CharField(max_length=30, blank=False)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    id_utilisateur = models.BigAutoField(primary_key=True)
    nom_utilisateur = models.CharField(max_length=30, blank=False)
    prenom_utilisateur = models.CharField(max_length=50, blank=False)
    num_utilisateur = models.TextField(max_length=10, blank=False)
    password = models.TextField(max_length=200, blank=False)
    photo_utilisateur = models.ImageField(upload_to=upload_to_utilisateur, blank=True, null=True)
    cree_le = models.DateField(db_default=Now())
    statut = models.BooleanField(db_default=True, blank=False, null=False)
    cp_commune = models.ForeignKey(Commune, on_delete=models.CASCADE, blank=False, null=True)
    role = models.ForeignKey(Role, blank=False, on_delete=models.PROTECT)
    last_token = models.CharField(max_length=255, blank=True, null=True)  # Nouvelle colonne pour le dernier token

    USERNAME_FIELD = 'id_utilisateur'


class Initial(models.Model):
    id_initial = models.BigAutoField(primary_key=True)
    utilisateur_createur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE,
                                             related_name='initials', blank=False, null=True)
    utilisateur_cree = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, blank=False, null=True)
