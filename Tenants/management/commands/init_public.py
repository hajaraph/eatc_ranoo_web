import os
from django.core.management.base import BaseCommand
from django.conf import settings
from Tenants.models import Entreprise, Domain, Utilisateur

class Command(BaseCommand):
    help = 'Initialize the Public Tenant, Domain, and Superuser for a fresh database.'

    def add_arguments(self, parser):
        parser.add_argument('--domain', type=str, default='localhost', help='Domain for the public tenant')
        parser.add_argument('--port', type=str, default='8000', help='Port for the domain (optional)')

    def handle(self, *args, **options):
        # Interactive Domain Selection
        default_domain = options['domain']
        self.stdout.write("--- Configuration du Domaine Public ---")
        user_input = input(f"Entrez le domaine [{default_domain}]: ").strip()
        
        domain_name = user_input if user_input else default_domain

        
        # 1. Create Public Tenant
        tenant_name = "Public"
        schema_name = "public"
        
        tenant, created = Entreprise.objects.get_or_create(
            schema_name=schema_name,
            defaults={
                'nom_entreprise': tenant_name,
                'nom_mvola': 'Public', # Required fields based on model? checking models.py... 
                # nom_mvola is blank=True, null=True. But check just in case.
                # All blanks seem allowed except nom_entreprise and schema_name.
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Public Tenant: {tenant.nom_entreprise}'))
        else:
            self.stdout.write(self.style.WARNING(f'Public Tenant already exists: {tenant.nom_entreprise}'))

        # 2. Create Domain
        # If using port with localhost, usually it's just 'localhost' in django-tenants unless strict
        # But commonly dev is localhost or 127.0.0.1
        
        domain_obj, created = Domain.objects.get_or_create(
            domain=domain_name,
            defaults={
                'tenant': tenant,
                'is_primary': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Domain: {domain_obj.domain}'))
        else:
            self.stdout.write(self.style.WARNING(f'Domain already exists: {domain_obj.domain} associated with {domain_obj.tenant}'))

        # 3. Create Superuser (if none exists)
        if not Utilisateur.objects.exists():
            self.stdout.write("No users found. Creating default superuser...")
            admin_user = Utilisateur.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin',
                entreprise=tenant
            )
            self.stdout.write(self.style.SUCCESS('Created Superuser: admin / admin'))
        else:
            self.stdout.write(self.style.WARNING('Users already exist. Skipping superuser creation.'))
