from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Now
from django.template.defaultfilters import slugify
from django_tenants.models import TenantMixin, DomainMixin

from Acommune.models import Commune


class Entreprise(TenantMixin):
    nom_entreprise = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)


class Domain(DomainMixin):
    pass


def upload_to_utilisateur(instance, filename):
    return f'utilisateur/{instance.id_utilisateur}/{filename}'


class Role(models.Model):
    id_role = models.BigAutoField(primary_key=True)
    role = models.CharField(max_length=30, blank=False)


class Utilisateur(AbstractUser):
    id_utilisateur = models.BigAutoField(primary_key=True)
    nom_utilisateur = models.CharField(max_length=30, blank=False)
    prenom_utilisateur = models.CharField(max_length=50, blank=False)
    num_utilisateur = models.TextField(max_length=10, blank=False)
    photo_utilisateur = models.ImageField(upload_to=upload_to_utilisateur, blank=True, null=True)
    cree_le = models.DateField(db_default=Now())
    statut = models.BooleanField(db_default=True, blank=False, null=False)
    cp_commune = models.ForeignKey(Commune, on_delete=models.CASCADE, blank=True, null=True)
    role = models.ForeignKey('Role', blank=True, on_delete=models.PROTECT, null=True)
    entreprise = models.ForeignKey('Entreprise', on_delete=models.PROTECT, blank=True, null=True)
    last_token = models.CharField(max_length=255, blank=True, null=True)

    username = models.CharField(max_length=100, blank=True, null=True, unique=True, verbose_name='Pseudo')
    first_name = 'nom_utilisateur'
    last_name = 'prenom_utilisateur'
    IS_ACTIVE_FIELD = 'statut'
    DATE_JOINED_FIELD = 'cree_le'

    def save(self, *args, **kwargs):
        if not self.username:
            username_suggestion = f"{self.prenom_utilisateur}".lower()
            username = slugify(username_suggestion)

            counter = 1
            original_username = username
            while Utilisateur.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1

            self.username = username

        super().save(*args, **kwargs)


class Initial(models.Model):
    id_initial = models.BigAutoField(primary_key=True)
    utilisateur_createur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE,
                                             related_name='initials', blank=False, null=True)
    utilisateur_cree = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, blank=False, null=True)
