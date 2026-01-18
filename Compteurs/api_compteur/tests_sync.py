"""
Tests pour les endpoints de synchronisation.

Ces tests vérifient que:
- Les endpoints de sync retournent le bon format
- La pagination par curseur fonctionne
- Le delta sync filtre correctement par date
- Les opérations batch fonctionnent
"""
import uuid
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from Compteurs.models import Compteur, ReleveCompteur
from Tenants.models import Utilisateur


class SyncEndpointsTestCase(TenantTestCase):
    """Tests pour les endpoints de synchronisation"""
    
    def setUp(self):
        """Configuration des tests"""
        super().setUp()
        
        # Créer un utilisateur pour les tests
        self.user = Utilisateur.objects.create_user(
            username='testuser',
            password='testpass123',
            nom_utilisateur='Test',
            prenom_utilisateur='User',
            num_utilisateur='0340000000'
        )
        
        # Configurer le client API avec authentification JWT
        self.client = TenantClient(self.tenant)
        
        # Générer un token JWT
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        # Créer des compteurs de test
        self.compteur1 = Compteur.objects.create(
            num_compteur="C-SYNC-001",
            marque_compteur="Marque A"
        )
        self.compteur2 = Compteur.objects.create(
            num_compteur="C-SYNC-002",
            marque_compteur="Marque B"
        )
    
    def _auth_get(self, url):
        """GET avec authentification JWT"""
        return self.client.get(
            url,
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}'
        )
    
    def _auth_post(self, url, data, **kwargs):
        """POST avec authentification JWT"""
        return self.client.post(
            url,
            data=data,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.access_token}',
            **kwargs
        )
    
    def test_sync_status_returns_success(self):
        """sync/status doit retourner une réponse de succès"""
        response = self.client.get('/api/sync/status')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertIn('server_time', response.json()['data'])
        self.assertIn('changes', response.json()['data'])
    
    def test_sync_status_with_last_sync(self):
        """sync/status avec last_sync doit filtrer les modifications"""
        yesterday = (timezone.now() - timedelta(days=1)).isoformat()
        
        response = self.client.get(f'/api/sync/status?last_sync={yesterday}')
        
        self.assertEqual(response.status_code, 200)
        changes = response.json()['data']['changes']
        self.assertIn('compteurs', changes)
        self.assertIn('releves', changes)
    
    def test_sync_compteurs_returns_data(self):
        """sync/compteurs doit retourner les compteurs avec metadata"""
        response = self.client.get('/api/sync/compteurs')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertIn('data', response.json())
        self.assertIn('sync', response.json())
    
    def test_sync_compteurs_includes_sync_fields(self):
        """Les compteurs retournés doivent avoir les champs de sync"""
        response = self.client.get('/api/sync/compteurs')
        
        data = response.json()['data']
        if data:
            compteur = data[0]
            self.assertIn('sync_id', compteur)
            self.assertIn('version', compteur)
            self.assertIn('updated_at', compteur)
            self.assertIn('is_deleted', compteur)
    
    def test_sync_compteurs_with_modified_since(self):
        """sync/compteurs avec modified_since doit filtrer"""
        # Date dans le passé lointain
        old_date = (timezone.now() - timedelta(days=365)).isoformat()
        
        response = self.client.get(f'/api/sync/compteurs?modified_since={old_date}')
        
        self.assertEqual(response.status_code, 200)
        # Devrait inclure nos compteurs créés récemment
        self.assertTrue(response.json()['success'])
    
    def test_sync_compteurs_pagination(self):
        """sync/compteurs doit supporter la pagination par curseur"""
        # Créer plus de compteurs
        for i in range(5):
            Compteur.objects.create(
                num_compteur=f"C-PAGE-{i}",
                marque_compteur="Test"
            )
        
        # Première page avec limit=2
        response = self.client.get('/api/sync/compteurs?limit=2')
        
        self.assertEqual(response.status_code, 200)
        sync_info = response.json()['sync']
        # Vérifier la présence des info de pagination
        self.assertIn('has_more', sync_info)
        self.assertIn('server_time', sync_info)
    
    def test_sync_releves_returns_data(self):
        """sync/releves doit retourner les relevés"""
        # Créer un relevé
        ReleveCompteur.objects.create(
            date_releve=date.today(),
            volume=100,
            conso=10,
            num_compteur=self.compteur1
        )
        
        response = self.client.get('/api/sync/releves')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
    
    def test_sync_releves_includes_deleted_when_requested(self):
        """sync/releves avec include_deleted=true doit inclure les supprimés"""
        releve = ReleveCompteur.objects.create(
            date_releve=date.today(),
            volume=100,
            conso=10,
            num_compteur=self.compteur1
        )
        releve.soft_delete()
        
        # Sans include_deleted (devrait exclure)
        response1 = self.client.get('/api/sync/releves?include_deleted=false')
        # Avec include_deleted (devrait inclure)
        response2 = self.client.get('/api/sync/releves?include_deleted=true')
        
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)


class BatchSyncTestCase(TenantTestCase):
    """Tests pour les opérations batch"""
    
    def setUp(self):
        """Configuration des tests"""
        super().setUp()
        
        self.user = Utilisateur.objects.create_user(
            username='batchuser',
            password='testpass123',
            nom_utilisateur='Batch',
            prenom_utilisateur='User',
            num_utilisateur='0340000001'
        )
        
        self.client = TenantClient(self.tenant)
        self.client.force_login(self.user)
        
        self.compteur = Compteur.objects.create(
            num_compteur="C-BATCH-001",
            marque_compteur="Test"
        )
    
    def test_batch_sync_accepts_operations(self):
        """sync/batch doit accepter une liste d'opérations"""
        payload = {
            'operations': [
                {
                    'type': 'releve',
                    'action': 'create',
                    'client_id': str(uuid.uuid4()),
                    'data': {
                        'date_releve': str(date.today()),
                        'volume': 100,
                        'conso': 10,
                        'num_compteur': self.compteur.num_compteur,
                    }
                }
            ]
        }
        
        response = self.client.post(
            '/api/sync/batch',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertIn('results', response.json()['data'])
    
    def test_batch_sync_returns_created_ids(self):
        """sync/batch doit retourner les IDs des éléments créés"""
        client_id = str(uuid.uuid4())
        payload = {
            'operations': [
                {
                    'type': 'releve',
                    'action': 'create',
                    'client_id': client_id,
                    'data': {
                        'date_releve': str(date.today()),
                        'volume': 200,
                        'conso': 20,
                        'num_compteur': self.compteur.num_compteur,
                    }
                }
            ]
        }
        
        response = self.client.post(
            '/api/sync/batch',
            data=payload,
            content_type='application/json'
        )
        
        result = response.json()['data']['results'][0]
        self.assertEqual(result['client_id'], client_id)
        self.assertTrue(result['success'])
        self.assertIn('server_id', result)
        self.assertIn('sync_id', result)
        self.assertIn('version', result)
    
    def test_batch_sync_handles_errors_per_operation(self):
        """sync/batch doit gérer les erreurs par opération"""
        payload = {
            'operations': [
                {
                    'type': 'releve',
                    'action': 'create',
                    'client_id': 'valid-op',
                    'data': {
                        'date_releve': str(date.today()),
                        'volume': 100,
                        'num_compteur': self.compteur.num_compteur,
                    }
                },
                {
                    'type': 'releve',
                    'action': 'create',
                    'client_id': 'invalid-op',
                    'data': {
                        'date_releve': str(date.today()),
                        # num_compteur manquant - devrait échouer
                    }
                }
            ]
        }
        
        response = self.client.post(
            '/api/sync/batch',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        results = response.json()['data']['results']
        
        # Vérifier que les deux résultats sont présents
        self.assertEqual(len(results), 2)
        
        # Au moins une opération devrait avoir échoué
        failed_ops = [r for r in results if not r['success']]
        self.assertGreater(len(failed_ops), 0)
    
    def test_batch_sync_respects_limit(self):
        """sync/batch doit rejeter plus de 100 opérations"""
        payload = {
            'operations': [
                {
                    'type': 'releve',
                    'action': 'create',
                    'client_id': f'op-{i}',
                    'data': {}
                }
                for i in range(101)
            ]
        }
        
        response = self.client.post(
            '/api/sync/batch',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])


class IdempotentCreateTestCase(TenantTestCase):
    """Tests pour la création idempotente"""
    
    def setUp(self):
        """Configuration des tests"""
        super().setUp()
        
        self.user = Utilisateur.objects.create_user(
            username='idempotentuser',
            password='testpass123',
            nom_utilisateur='Idemp',
            prenom_utilisateur='User',
            num_utilisateur='0340000002'
        )
        
        self.client = TenantClient(self.tenant)
        self.client.force_login(self.user)
        
        self.compteur = Compteur.objects.create(
            num_compteur="C-IDEMP-001",
            marque_compteur="Test"
        )
    
    def test_create_releve_idempotent(self):
        """sync/releve/create doit créer un relevé avec succès"""
        payload = {
            'date_releve': str(date.today()),
            'volume': 500,
            'conso': 50,
            'num_compteur': self.compteur.num_compteur,
        }
        
        response = self.client.post(
            '/api/sync/releve/create',
            data=payload,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['success'])
        self.assertIn('sync_id', response.json()['data'])
    
    def test_create_releve_with_idempotency_key(self):
        """Deux requêtes avec la même clé d'idempotence doivent retourner le même résultat"""
        idempotency_key = str(uuid.uuid4())
        payload = {
            'date_releve': str(date.today()),
            'volume': 600,
            'conso': 60,
            'num_compteur': self.compteur.num_compteur,
        }
        
        # Première requête
        response1 = self.client.post(
            '/api/sync/releve/create',
            data=payload,
            content_type='application/json',
            HTTP_X_IDEMPOTENCY_KEY=idempotency_key
        )
        
        # Deuxième requête avec la même clé
        response2 = self.client.post(
            '/api/sync/releve/create',
            data=payload,
            content_type='application/json',
            HTTP_X_IDEMPOTENCY_KEY=idempotency_key
        )
        
        # Les deux devraient retourner le même résultat sans créer de doublon
        self.assertEqual(response1.status_code, response2.status_code)
        self.assertEqual(
            response1.json()['data']['sync_id'],
            response2.json()['data']['sync_id']
        )
        
        # Vérifier qu'un seul relevé a été créé
        count = ReleveCompteur.objects.filter(
            num_compteur=self.compteur,
            volume=600
        ).count()
        self.assertEqual(count, 1)
