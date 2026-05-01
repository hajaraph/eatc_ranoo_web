import pytest
from django.test import TestCase
from django.utils import timezone
from Clients.models import Client, Contrat, TypeClient, PieceClient
from Compteurs.models import Compteur


@pytest.mark.django_db
class TestClientModel(TestCase):
    """Tests pour le modèle Client"""

    def test_creation_client(self):
        """Test la création d'un client"""
        client = Client.objects.create(
            nom_client='Test Client',
            prenom_client='Test',
            adresse_client='Test Address',
            telephone_client='0341234567',
            type_client_id=1
        )
        self.assertEqual(client.nom_client, 'Test Client')
        self.assertEqual(client.telephone_client, '0341234567')


@pytest.mark.django_db
class TestContratModel(TestCase):
    """Tests pour le modèle Contrat"""

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

    def test_creation_contrat(self):
        """Test la création d'un contrat"""
        contrat = Contrat.objects.create(
            num_contrat='CTR001',
            client=self.client,
            num_compteur=self.compteur,
            cp_commune='001',
            date_contrat=timezone.now().date()
        )
        self.assertEqual(contrat.num_contrat, 'CTR001')
        self.assertEqual(contrat.client, self.client)
        self.assertEqual(contrat.num_compteur, self.compteur)


@pytest.mark.django_db
class TestPieceClient(TestCase):
    """Tests pour le modèle PieceClient"""

    def setUp(self):
        """Configuration initiale pour les tests"""
        self.client = Client.objects.create(
            nom_client='Test Client',
            type_client_id=1
        )

    def test_creation_piece_client(self):
        """Test la création d'une pièce client"""
        piece = PieceClient.objects.create(
            client=self.client,
            type_piece='CIN',
            description_piece='Piece test'
        )
        self.assertEqual(piece.type_piece, 'CIN')
        self.assertEqual(piece.client, self.client)
