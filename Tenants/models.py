from django.contrib.auth.models import AbstractUser
from django.db import models
from django.template.defaultfilters import slugify
from django_tenants.models import TenantMixin, DomainMixin

from Acommune.models import Commune


class Entreprise(TenantMixin):
    nom_entreprise = models.CharField(max_length=100)
    schema_name = models.CharField(max_length=100, verbose_name="Base de donnée")
    created_on = models.DateTimeField(auto_now_add=True, verbose_name='Date de creation')


class Domain(DomainMixin):
    pass


def upload_to_utilisateur(instance, filename):
    return f'utilisateur/{instance.id_utilisateur}/{filename}'


class Role(models.Model):
    id_role = models.BigAutoField(primary_key=True)
    role = models.CharField(max_length=30, blank=False)


class Utilisateur(AbstractUser):
    id_utilisateur = models.BigAutoField(primary_key=True)
    nom_utilisateur = models.CharField(max_length=30, blank=False, verbose_name='Nom')
    prenom_utilisateur = models.CharField(max_length=50, blank=False, verbose_name='Prénom')
    num_utilisateur = models.CharField(max_length=10, blank=False, verbose_name='Contact')
    photo_utilisateur = models.ImageField(upload_to=upload_to_utilisateur, blank=True, null=True)
    cree_le = models.DateField(auto_now_add=True)
    statut = models.BooleanField(db_default=True, blank=False, null=False, verbose_name='Active')
    cp_commune = models.ForeignKey(Commune, on_delete=models.CASCADE, blank=True, null=True, verbose_name='Commune')
    role = models.ForeignKey('Role', blank=True, on_delete=models.PROTECT, null=True)
    entreprise = models.ForeignKey('Entreprise', on_delete=models.PROTECT, blank=True, null=True)
    last_token = models.CharField(max_length=255, blank=True, null=True)

    username = models.CharField(max_length=100, blank=True, null=True, unique=True, verbose_name='Pseudo')
    first_name = 'nom_utilisateur'
    last_name = 'prenom_utilisateur'
    is_active = 'statut'
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

        # Si l'utilisateur est nouveau ou son mot de passe a changé, on le hache
        if self.pk is None or not Utilisateur.objects.filter(pk=self.pk).exists():
            self.set_password(self.password)
            return True
        else:
            original_password = Utilisateur.objects.get(pk=self.pk).password
            if self.password != original_password:
                self.set_password(self.password)
            return False


class Initial(models.Model):
    id_initial = models.BigAutoField(primary_key=True)
    utilisateur_createur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE,
                                             related_name='initials', blank=False, null=True)
    utilisateur_cree = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, blank=False, null=True)
