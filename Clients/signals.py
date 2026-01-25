from django.dispatch import receiver
from django_tenants.signals import post_schema_sync
from django_tenants.utils import schema_context

from Clients.models import TypeClient


@receiver(post_schema_sync)
def create_default_client_types(sender, tenant, **kwargs):
    if tenant.schema_name != 'public':
        with schema_context(tenant.schema_name):
            default_types = [
                "Branchement Privé",
                "Branchement Partagé",
                "Point Eau Public",
                "Branchement Institutionnel",
                "Gros Consommateur",
            ]

            for designation in default_types:
                TypeClient.objects.get_or_create(
                    designation_client=designation
                )
