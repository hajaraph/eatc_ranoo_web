from datetime import datetime

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from Acommune.models import Commune
from Tenants.models import Utilisateur


class DebitEau(models.Model):
    id_debit = models.BigAutoField(primary_key=True)
    debit = models.FloatField(null=False, blank=False)
    date_creation = models.DateField(auto_now_add=True)
    date_modification = models.DateField(auto_now=True)
    cp_commune = models.ForeignKey(Commune, on_delete=models.CASCADE, blank=False, null=False)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.date_modification = datetime.now()
        super().save(*args, **kwargs)


class Marnage(models.Model):
    id_marnage = models.BigAutoField(primary_key=True)
    marnage = models.IntegerField(null=False, blank=False, validators=[MinValueValidator(0), MaxValueValidator(100)])
    date_creation = models.CharField(max_length=16, null=True, blank=True)
    date_modification = models.DateField(auto_now=True)
    cp_commune = models.ForeignKey(Commune, on_delete=models.CASCADE, blank=False, null=False)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.date_modification = datetime.now()
        super().save(*args, **kwargs)

