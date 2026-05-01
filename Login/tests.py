import pytest
from django.test import TestCase
from django.utils import timezone
from Login.models import Utilisateur, Role, DownloadToken


@pytest.mark.django_db
class TestUtilisateurModel(TestCase):
    """Tests pour le modèle Utilisateur"""

    def test_creation_utilisateur(self):
        """Test la création d'un utilisateur"""
        utilisateur = Utilisateur.objects.create(
            username='testuser',
            email='test@example.com',
            nom='Test',
            prenom='User'
        )
        self.assertEqual(utilisateur.username, 'testuser')
        self.assertEqual(utilisateur.email, 'test@example.com')


@pytest.mark.django_db
class TestRoleModel(TestCase):
    """Tests pour le modèle Role"""

    def test_creation_role(self):
        """Test la création d'un rôle"""
        role = Role.objects.create(
            nom_role='Test Role',
            description='Role de test'
        )
        self.assertEqual(role.nom_role, 'Test Role')


@pytest.mark.django_db
class TestDownloadToken(TestCase):
    """Tests pour le modèle DownloadToken"""

    def test_creation_download_token(self):
        """Test la création d'un token de téléchargement"""
        token = DownloadToken.objects.create(
            token='test-token-123',
            fichier='test.pdf',
            date_expiration=timezone.now() + timezone.timedelta(days=1)
        )
        self.assertEqual(token.token, 'test-token-123')
        self.assertEqual(token.fichier, 'test.pdf')
