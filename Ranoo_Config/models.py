from django.db import models

from Clients.models import TypeClient


class ConfigBranchement(models.Model):
    id_config_branchement = models.BigAutoField(primary_key=True)
    type_client = models.ForeignKey(TypeClient, on_delete=models.PROTECT, related_name='config_branchement')
    tva_applique = models.BooleanField(default=False)
    taxe_applique = models.BooleanField(default=False)
