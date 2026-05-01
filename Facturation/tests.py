import pytest
from django.test import TestCase
from django.utils import timezone
from Facturation.models import Facture, Paiement, Avoir, Restant
from Clients.models import Client, Contrat
from Compteurs.models import Compteur


@pytest.mark.django_db
class TestFactureModel(TestCase):
    """Tests pour le modèle Facture"""

    def setUp(self):
        """Configuration initiale pour les tests"""
        self.client = Client.objects.create(
            nom_client='Test Client',
            type_client_id=1
        )
        self.compteur = Compteur.objects.create(
            num_compteur='CP001',
            marque_compteur='Test'
        )
        self.contrat = Contrat.objects.create(
            num_contrat='CTR001',
            client=self.client,
            num_compteur=self.compteur,
            cp_commune='001'
        )

    def test_creation_facture(self):
        """Test la création d'une facture"""
        facture = Facture.objects.create(
            num_facture='FAC001',
            num_contrat=self.contrat,
            montant_total_ttc=1000,
            date_facture=timezone.now().date()
        )
        self.assertEqual(facture.num_facture, 'FAC001')
        self.assertEqual(facture.montant_total_ttc, 1000)
        self.assertFalse(facture.statut)


@pytest.mark.django_db
class TestPaiement(TestCase):
    """Tests pour le modèle Paiement"""

    def setUp(self):
        """Configuration initiale pour les tests"""
        self.client = Client.objects.create(
            nom_client='Test Client',
            type_client_id=1
        )
        self.compteur = Compteur.objects.create(
            num_compteur='CP001',
            marque_compteur='Test'
        )
        self.contrat = Contrat.objects.create(
            num_contrat='CTR001',
            client=self.client,
            num_compteur=self.compteur,
            cp_commune='001'
        )
        self.facture = Facture.objects.create(
            num_facture='FAC001',
            num_contrat=self.contrat,
            montant_total_ttc=1000,
            date_facture=timezone.now().date()
        )

    def test_creation_paiement(self):
        """Test la création d'un paiement"""
        paiement = Paiement.objects.create(
            facture=self.facture,
            montant_payer=500,
            date_paiement=timezone.now()
        )
        self.assertEqual(paiement.montant_payer, 500)
        self.assertEqual(paiement.facture, self.facture)


@pytest.mark.django_db
class TestRestant(TestCase):
    """Tests pour le modèle Restant"""

    def setUp(self):
        """Configuration initiale pour les tests"""
        self.client = Client.objects.create(
            nom_client='Test Client',
            type_client_id=1
        )
        self.compteur = Compteur.objects.create(
            num_compteur='CP001',
            marque_compteur='Test'
        )
        self.contrat = Contrat.objects.create(
            num_contrat='CTR001',
            client=self.client,
            num_compteur=self.compteur,
            cp_commune='001'
        )

    def test_creation_restant(self):
        """Test la création d'un restant"""
        restant = Restant.objects.create(
            num_contrat=self.contrat,
            restant=200,
            date_restant=timezone.now()
        )
        self.assertEqual(restant.restant, 200)
        self.assertEqual(restant.num_contrat, self.contrat)
