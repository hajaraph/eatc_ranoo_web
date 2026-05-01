import pytest
from django.test import TestCase
from Tenants.models import Entreprise, Domain, Utilisateur


@pytest.mark.django_db
class TestEntrepriseModel(TestCase):
    """Tests pour le modèle Entreprise"""

    def test_creation_entreprise(self):
        """Test la création d'une entreprise"""
        entreprise = Entreprise.objects.create(
            nom_entreprise='Test Entreprise',
            schema_name='test_entreprise'
        )
        self.assertEqual(entreprise.nom_entreprise, 'Test Entreprise')
        self.assertEqual(entreprise.schema_name, 'test_entreprise')


@pytest.mark.django_db
class TestDomainModel(TestCase):
    """Tests pour le modèle Domain"""

    def setUp(self):
        """Configuration initiale pour les tests"""
        self.entreprise = Entreprise.objects.create(
            nom_entreprise='Test Entreprise',
            schema_name='test_entreprise'
        )

    def test_creation_domain(self):
        """Test la création d'un domaine"""
        domain = Domain.objects.create(
            domain='test.example.com',
            tenant=self.entreprise,
            is_primary=True
        )
        self.assertEqual(domain.domain, 'test.example.com')
        self.assertEqual(domain.tenant, self.entreprise)
