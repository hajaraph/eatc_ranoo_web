from django.db import models

from Clients.models import TypeClient


class ConfigBranchement(models.Model):
    id_config_branchement = models.BigAutoField(primary_key=True)
    type_client = models.ForeignKey(TypeClient, on_delete=models.CASCADE)
    tva_applique = models.BooleanField(default=False)
