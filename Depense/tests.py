import pytest
from django.test import TestCase
from django.utils import timezone
from Depense.models import Depense, Categories


@pytest.mark.django_db
class TestDepenseModel(TestCase):
    """Tests pour le modèle Depense"""

    def test_creation_depense(self):
        """Test la création d'une dépense"""
        categorie = Categories.objects.create(
            nom_categorie='Test Categorie',
            description='Categorie de test'
        )
        depense = Depense.objects.create(
            montant=500,
            date_depense=timezone.now().date(),
            categorie=categorie
        )
        self.assertEqual(depense.montant, 500)
        self.assertEqual(depense.categorie, categorie)
