from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token
from Tenants.models import Utilisateur
import secrets


class Command(BaseCommand):
    help = 'Créer un token de service pour GitHub Actions ou autres services externes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='github_actions',
            help='Nom d\'utilisateur pour le service (défaut: github_actions)'
        )
        parser.add_argument(
            '--revoke',
            action='store_true',
            help='Révoquer le token existant avant d\'en créer un nouveau'
        )

    def handle(self, *args, **options):
        username = options.get('username')
        revoke = options.get('revoke', False)
        
        # Créer utilisateur service s'il n'existe pas
        user, created = Utilisateur.objects.get_or_create(
            num_utilisateur=f'service_{username}',
            defaults={
                'nom_utilisateur': 'Service',
                'prenom_utilisateur': username.replace('_', ' ').title(),
                'email': f'{username}@service.eatc.local',
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
            }
        )
        
        if created:
            # Définir un mot de passe aléatoire (non utilisé car authentification par token)
            random_password = secrets.token_urlsafe(32)
            user.set_password(random_password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Utilisateur de service créé: service_{username}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠ Utilisateur existe déjà: service_{username}')
            )
        
        # Révoquer ancien token si demandé
        if revoke:
            old_tokens = Token.objects.filter(user=user)
            if old_tokens.exists():
                old_tokens.delete()
                self.stdout.write(
                    self.style.WARNING('⚠ Anciens tokens révoqués')
                )
        
        # Créer nouveau token
        token, created = Token.objects.get_or_create(user=user)
        
        if not created:
            self.stdout.write(
                self.style.WARNING('⚠ Token existant récupéré (utilisez --revoke pour régénérer)')
            )
        
        # Afficher le token avec un formatage clair
        token_key = token.key
        
        self.stdout.write(self.style.SUCCESS(''))
        self.stdout.write(self.style.SUCCESS('┌──────────────────────────────────────────────────────────────┐'))
        self.stdout.write(self.style.SUCCESS(f'│  TOKEN GÉNÉRÉ POUR service_{username:<38} │'))
        self.stdout.write(self.style.SUCCESS('├──────────────────────────────────────────────────────────────┤'))
        self.stdout.write(self.style.SUCCESS(f'│                                                              │'))
        self.stdout.write(self.style.SUCCESS(f'│  Token: {token_key:<43} │'))
        self.stdout.write(self.style.SUCCESS(f'│                                                              │'))
        self.stdout.write(self.style.SUCCESS(f'│  API Upload: POST /api/upload-apk/                          │'))
        self.stdout.write(self.style.SUCCESS(f'│  API Version:  GET  /api/version/                           │'))
        self.stdout.write(self.style.SUCCESS(f'│                                                              │'))
        self.stdout.write(self.style.SUCCESS(f'│          COPIEZ CE TOKEN DANS GITHUB SECRETS !                   │'))
        self.stdout.write(self.style.SUCCESS(f'│     GitHub → Settings → Secrets → DJANGO_SERVICE_TOKEN       │'))
        self.stdout.write(self.style.SUCCESS('│                                                              │'))
        self.stdout.write(self.style.SUCCESS('└──────────────────────────────────────────────────────────────┘'))
        self.stdout.write(self.style.SUCCESS(''))
