import pytest
from django.test import TestCase
from django.utils import timezone
from Recette.models import Recette, TypeRecette


@pytest.mark.django_db
class TestRecetteModel(TestCase):
    """Tests pour le modèle Recette"""

    def test_creation_recette(self):
        """Test la création d'une recette"""
        type_recette = TypeRecette.objects.create(
            nom_type='Test Type',
            description='Type de recette test'
        )
        recette = Recette.objects.create(
            montant=1000,
            date_encaissement=timezone.now().date(),
            type_recette=type_recette
        )
        self.assertEqual(recette.montant, 1000)
        self.assertEqual(recette.type_recette, type_recette)
