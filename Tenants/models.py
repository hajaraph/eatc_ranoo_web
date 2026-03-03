from asyncio.log import logger

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.template.defaultfilters import slugify
from django_tenants.models import TenantMixin, DomainMixin

from Acommune.models import Commune


class Entreprise(TenantMixin):
    nom_entreprise = models.CharField(max_length=100)
    schema_name = models.CharField(max_length=100, verbose_name="Base de donnée")
    numero_mvola = models.CharField(max_length=10, blank=True, null=True, verbose_name='Numéro Mvola')
    nom_mvola = models.CharField(max_length=256, blank=True, null=True, verbose_name='Nom Mvola')
    nif = models.CharField(max_length=100, verbose_name="NIF", blank=True, null=True)
    stat = models.CharField(max_length=100, verbose_name="STAT", blank=True, null=True)
    logo_entreprise = models.ImageField(upload_to='logo/entreprise', blank=True, verbose_name='Logo')
    signature_entreprise = models.ImageField(upload_to='signature/entreprise', blank=True, verbose_name='Signature')
    siege_social = models.CharField(max_length=255, blank=True, null=True, verbose_name='Siège social')
    representant_legal = models.CharField(max_length=100, blank=True, null=True, verbose_name='Représentant légal')
    created_on = models.DateTimeField(auto_now_add=True, verbose_name='Date de creation')
    
    def __str__(self):
        return self.nom_entreprise


class Domain(DomainMixin):
    pass


def upload_to_utilisateur(instance, filename):
    return f'utilisateur/{instance.id_utilisateur}/{filename}'


class Role(models.Model):
    id_role = models.BigAutoField(primary_key=True)
    role = models.CharField(max_length=30, blank=False)

    def __str__(self):
        return self.role


class Utilisateur(AbstractUser):
    id_utilisateur = models.BigAutoField(primary_key=True)
    nom_utilisateur = models.CharField(max_length=30, blank=False, verbose_name='Nom')
    prenom_utilisateur = models.CharField(max_length=50, blank=False, verbose_name='Prénom')
    num_utilisateur = models.CharField(max_length=10, blank=False, verbose_name='Contact', unique=True)
    photo_utilisateur = models.ImageField(upload_to=upload_to_utilisateur, blank=True, null=True)
    cree_le = models.DateField(auto_now_add=True)
    statut = models.BooleanField(db_default=True, blank=False, null=False, verbose_name='Active')
    cp_commune = models.ForeignKey(Commune, on_delete=models.CASCADE, blank=True, null=True, verbose_name='Commune')
    role = models.ForeignKey('Role', blank=True, on_delete=models.PROTECT, null=True)
    entreprise = models.ForeignKey('Entreprise', on_delete=models.PROTECT, blank=True, null=True)
    last_token = models.CharField(max_length=255, blank=True, null=True)

    username = models.CharField(max_length=100, blank=True, null=True, unique=True, verbose_name='Pseudo')
    # first_name et last_name sont des champs de AbstractUser, on ne doit pas les écraser avec des strings
    # On les laisse vides ou on ne les utilise pas.
    
    DATE_JOINED_FIELD = 'cree_le'

    @property
    def is_active(self):
         return self.statut
         
    @is_active.setter
    def is_active(self, value):
         self.statut = value

    @property
    def first_name(self):
        return self.nom_utilisateur

    @first_name.setter
    def first_name(self, value):
        self.nom_utilisateur = value

    @property
    def last_name(self):
        return self.prenom_utilisateur

    @last_name.setter
    def last_name(self, value):
        self.prenom_utilisateur = value

    def get_full_name(self):
        return f"{self.nom_utilisateur} {self.prenom_utilisateur}".strip()

    def get_short_name(self):
        return self.prenom_utilisateur

    def __str__(self):
        return self.username or self.num_utilisateur

    def save(self, *args, **kwargs):
        logger.info(f"Commencement sauvegarde utilisateur: {self.num_utilisateur}")
        utilisateur_createur = kwargs.pop('utilisateur_createur', None)

        if not self.username:
            username_suggestion = f"{self.prenom_utilisateur}".lower()
            username = slugify(username_suggestion)
            counter = 1
            original_username = username
            while Utilisateur.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1
            self.username = username

        is_new_user = self.pk is None
        if is_new_user:
            self.set_password(self.password)
        else:
            original = Utilisateur.objects.get(pk=self.pk)
            if self.password != original.password:
                self.set_password(self.password)

        super().save(*args, **kwargs)

        if is_new_user and utilisateur_createur:
            Initial.objects.create(
                utilisateur_createur=utilisateur_createur,
                utilisateur_cree=self
            )


class Initial(models.Model):
    id_initial = models.BigAutoField(primary_key=True)
    utilisateur_createur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE,
                                             related_name='initials', blank=False, null=True)
    utilisateur_cree = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, blank=False, null=True)
