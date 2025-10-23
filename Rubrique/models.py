from django.db import models

from Acommune.models import Commune


class DebitEau(models.Model):
    id_debit = models.BigAutoField(primary_key=True)
    debit = models.IntegerField(null=False, blank=False)
    date_creation = models.DateField(auto_now_add=True)
    cp_commune = models.ForeignKey(Commune, on_delete=models.CASCADE, blank=False, null=False)


class Marnage(models.Model):
    id_marnage = models.BigAutoField(primary_key=True)
    marnage = models.IntegerField(null=False, blank=False)
    date_creation = models.DateField(auto_now_add=True)
    cp_commune = models.ForeignKey(Commune, on_delete=models.CASCADE, blank=False, null=False)

