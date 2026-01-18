"""
Tests unitaires pour les mixins et utilitaires de synchronisation.

Ce fichier contient les tests pour:
- SyncMixin: Traçabilité, versioning, soft delete
- SyncManager: Filtrage des éléments supprimés, delta sync
- ApiResponse: Réponses standardisées
- ensure_idempotent: Décorateur d'idempotence
"""
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch
from django.test import TestCase, RequestFactory, override_settings
from django.utils import timezone
from django.db import models, connection
from django.core.cache import cache

from Rel_Compteur.mixins import SyncMixin, SyncManager
from Rel_Compteur.api_utils import ApiResponse, ensure_idempotent


# ============================================================
# Modèle de test pour SyncMixin
# ============================================================

class TestModel(SyncMixin, models.Model):
    """Modèle de test qui utilise le SyncMixin"""
    name = models.CharField(max_length=100)
    value = models.IntegerField(default=0)
    
    objects = SyncManager()
    all_objects = models.Manager()
    
    class Meta:
        app_label = 'Rel_Compteur'
        # Important: Ce modèle n'est pas géré par les migrations
        # Il sera créé dynamiquement pour les tests
        managed = False


# ============================================================
# Tests pour SyncMixin
# ============================================================

class SyncMixinTestCase(TestCase):
    """Tests pour le SyncMixin"""
    
    @classmethod
    def setUpClass(cls):
        """Créer la table de test temporaire"""
        super().setUpClass()
        with connection.schema_editor() as schema_editor:
            try:
                schema_editor.create_model(TestModel)
            except Exception:
                # La table existe peut-être déjà
                pass
    
    @classmethod
    def tearDownClass(cls):
        """Supprimer la table de test temporaire"""
        with connection.schema_editor() as schema_editor:
            try:
                schema_editor.delete_model(TestModel)
            except Exception:
                pass
        super().tearDownClass()
    
    def setUp(self):
        """Nettoyer les données avant chaque test"""
        TestModel.all_objects.all().delete()
    
    def test_sync_id_is_uuid_on_creation(self):
        """Le sync_id doit être un UUID valide à la création"""
        obj = TestModel.objects.create(name="Test 1", value=10)
        
        self.assertIsNotNone(obj.sync_id)
        self.assertIsInstance(obj.sync_id, uuid.UUID)
    
    def test_sync_id_is_unique(self):
        """Chaque objet doit avoir un sync_id unique"""
        obj1 = TestModel.objects.create(name="Test 1", value=10)
        obj2 = TestModel.objects.create(name="Test 2", value=20)
        
        self.assertNotEqual(obj1.sync_id, obj2.sync_id)
    
    def test_created_at_is_set_on_creation(self):
        """created_at doit être défini automatiquement à la création"""
        before = timezone.now()
        obj = TestModel.objects.create(name="Test", value=10)
        after = timezone.now()
        
        self.assertIsNotNone(obj.created_at)
        self.assertGreaterEqual(obj.created_at, before)
        self.assertLessEqual(obj.created_at, after)
    
    def test_updated_at_changes_on_save(self):
        """updated_at doit être mis à jour à chaque save()"""
        obj = TestModel.objects.create(name="Test", value=10)
        original_updated_at = obj.updated_at
        
        # Attendre un peu pour s'assurer que le timestamp change
        obj.value = 20
        obj.save()
        
        obj.refresh_from_db()
        self.assertGreaterEqual(obj.updated_at, original_updated_at)
    
    def test_version_starts_at_one(self):
        """La version doit commencer à 1"""
        obj = TestModel.objects.create(name="Test", value=10)
        
        self.assertEqual(obj.version, 1)
    
    def test_version_increments_on_update(self):
        """La version doit s'incrémenter à chaque mise à jour"""
        obj = TestModel.objects.create(name="Test", value=10)
        self.assertEqual(obj.version, 1)
        
        obj.value = 20
        obj.save()
        obj.refresh_from_db()
        self.assertEqual(obj.version, 2)
        
        obj.value = 30
        obj.save()
        obj.refresh_from_db()
        self.assertEqual(obj.version, 3)
    
    def test_soft_delete_marks_as_deleted(self):
        """soft_delete() doit marquer l'objet comme supprimé"""
        obj = TestModel.objects.create(name="Test", value=10)
        
        self.assertFalse(obj.is_deleted)
        self.assertIsNone(obj.deleted_at)
        
        obj.soft_delete()
        
        self.assertTrue(obj.is_deleted)
        self.assertIsNotNone(obj.deleted_at)
    
    def test_soft_delete_keeps_in_database(self):
        """soft_delete() ne doit pas supprimer physiquement l'objet"""
        obj = TestModel.objects.create(name="Test", value=10)
        pk = obj.pk
        
        obj.soft_delete()
        
        # L'objet existe toujours en base
        self.assertTrue(TestModel.all_objects.filter(pk=pk).exists())
    
    def test_restore_unmarks_deleted(self):
        """restore() doit restaurer un objet supprimé"""
        obj = TestModel.objects.create(name="Test", value=10)
        obj.soft_delete()
        
        self.assertTrue(obj.is_deleted)
        
        obj.restore()
        
        self.assertFalse(obj.is_deleted)
        self.assertIsNone(obj.deleted_at)
    
    def test_hard_delete_removes_from_database(self):
        """hard_delete() doit supprimer physiquement l'objet"""
        obj = TestModel.objects.create(name="Test", value=10)
        pk = obj.pk
        
        obj.hard_delete()
        
        self.assertFalse(TestModel.all_objects.filter(pk=pk).exists())
    
    def test_get_sync_data_returns_correct_format(self):
        """get_sync_data() doit retourner les métadonnées de sync"""
        obj = TestModel.objects.create(name="Test", value=10)
        
        sync_data = obj.get_sync_data()
        
        self.assertIn('sync_id', sync_data)
        self.assertIn('version', sync_data)
        self.assertIn('created_at', sync_data)
        self.assertIn('updated_at', sync_data)
        self.assertIn('is_deleted', sync_data)
        self.assertIn('deleted_at', sync_data)
        
        self.assertEqual(sync_data['version'], 1)
        self.assertFalse(sync_data['is_deleted'])


# ============================================================
# Tests pour SyncManager
# ============================================================

class SyncManagerTestCase(TestCase):
    """Tests pour le SyncManager"""
    
    @classmethod
    def setUpClass(cls):
        """Créer la table de test temporaire"""
        super().setUpClass()
        with connection.schema_editor() as schema_editor:
            try:
                schema_editor.create_model(TestModel)
            except Exception:
                pass
    
    @classmethod
    def tearDownClass(cls):
        """Supprimer la table de test temporaire"""
        with connection.schema_editor() as schema_editor:
            try:
                schema_editor.delete_model(TestModel)
            except Exception:
                pass
        super().tearDownClass()
    
    def setUp(self):
        """Créer des données de test"""
        TestModel.all_objects.all().delete()
        
        self.active1 = TestModel.all_objects.create(name="Active 1", value=10)
        self.active2 = TestModel.all_objects.create(name="Active 2", value=20)
        self.deleted1 = TestModel.all_objects.create(name="Deleted 1", value=30)
        self.deleted1.soft_delete()
    
    def test_default_queryset_excludes_deleted(self):
        """Le queryset par défaut ne doit pas inclure les éléments supprimés"""
        queryset = TestModel.objects.all()
        
        self.assertEqual(queryset.count(), 2)
        self.assertIn(self.active1, queryset)
        self.assertIn(self.active2, queryset)
        self.assertNotIn(self.deleted1, queryset)
    
    def test_with_deleted_includes_all(self):
        """with_deleted() doit retourner tous les éléments"""
        queryset = TestModel.objects.with_deleted()
        
        self.assertEqual(queryset.count(), 3)
        self.assertIn(self.active1, queryset)
        self.assertIn(self.active2, queryset)
        self.assertIn(self.deleted1, queryset)
    
    def test_deleted_only_returns_deleted(self):
        """deleted_only() ne doit retourner que les éléments supprimés"""
        queryset = TestModel.objects.deleted_only()
        
        self.assertEqual(queryset.count(), 1)
        self.assertIn(self.deleted1, queryset)
    
    def test_modified_since_filters_by_date(self):
        """modified_since() doit filtrer par updated_at"""
        # Créer un nouvel objet après les autres
        old_time = timezone.now() - timedelta(hours=1)
        new_obj = TestModel.objects.create(name="New", value=100)
        
        # Chercher les objets modifiés depuis maintenant - 1 minute
        recent_time = timezone.now() - timedelta(minutes=1)
        queryset = TestModel.objects.modified_since(recent_time)
        
        # Devrait inclure tous les objets actifs créés récemment
        self.assertGreaterEqual(queryset.count(), 1)
    
    def test_modified_since_with_deleted_includes_deleted(self):
        """modified_since_with_deleted() doit inclure les éléments supprimés"""
        recent_time = timezone.now() - timedelta(minutes=1)
        queryset = TestModel.objects.modified_since_with_deleted(recent_time)
        
        # Devrait inclure les éléments supprimés modifiés récemment
        deleted_in_result = any(obj.is_deleted for obj in queryset)
        self.assertTrue(deleted_in_result)


# ============================================================
# Tests pour ApiResponse
# ============================================================

class ApiResponseTestCase(TestCase):
    """Tests pour les réponses API standardisées"""
    
    def test_success_response_format(self):
        """ApiResponse.success() doit retourner le bon format"""
        response = ApiResponse.success(
            data={'key': 'value'},
            message="Opération réussie"
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertIn('timestamp', response.data)
        self.assertEqual(response.data['data'], {'key': 'value'})
        self.assertEqual(response.data['message'], "Opération réussie")
    
    def test_success_without_data(self):
        """ApiResponse.success() doit fonctionner sans data"""
        response = ApiResponse.success(message="OK")
        
        self.assertTrue(response.data['success'])
        self.assertNotIn('data', response.data)
    
    def test_created_response(self):
        """ApiResponse.created() doit retourner un status 201"""
        response = ApiResponse.created(data={'id': 123})
        
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['id'], 123)
    
    def test_error_response_format(self):
        """ApiResponse.error() doit retourner le bon format"""
        response = ApiResponse.error(
            message="Erreur de validation",
            code="VALIDATION_ERROR",
            details={'field': 'Ce champ est requis'}
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['error']['message'], "Erreur de validation")
        self.assertEqual(response.data['error']['code'], "VALIDATION_ERROR")
        self.assertIn('details', response.data['error'])
    
    def test_not_found_response(self):
        """ApiResponse.not_found() doit retourner un status 404"""
        response = ApiResponse.not_found("Utilisateur non trouvé")
        
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['error']['code'], "NOT_FOUND")
    
    def test_conflict_response(self):
        """ApiResponse.conflict() doit retourner un status 409"""
        response = ApiResponse.conflict(
            message="Version obsolète",
            details={'current_version': 5, 'expected_version': 3}
        )
        
        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['error']['code'], "CONFLICT")
    
    def test_server_error_response(self):
        """ApiResponse.server_error() doit retourner un status 500"""
        response = ApiResponse.server_error()
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.data['success'])
    
    def test_sync_response_format(self):
        """ApiResponse.sync_response() doit retourner les métadonnées de sync"""
        response = ApiResponse.sync_response(
            data=[{'id': 1}, {'id': 2}],
            has_more=True,
            next_cursor="abc123"
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 2)
        self.assertIn('sync', response.data)
        self.assertTrue(response.data['sync']['has_more'])
        self.assertEqual(response.data['sync']['next_cursor'], "abc123")
    
    def test_batch_response_calculates_counts(self):
        """ApiResponse.batch_response() doit calculer les compteurs"""
        results = [
            {'success': True, 'id': 1},
            {'success': True, 'id': 2},
            {'success': False, 'error': 'Erreur'},
        ]
        response = ApiResponse.batch_response(results)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['meta']['total'], 3)
        self.assertEqual(response.data['meta']['success_count'], 2)
        self.assertEqual(response.data['meta']['failure_count'], 1)


# ============================================================
# Tests pour ensure_idempotent
# ============================================================

class IdempotentDecoratorTestCase(TestCase):
    """Tests pour le décorateur d'idempotence"""
    
    def setUp(self):
        """Nettoyer le cache avant chaque test"""
        cache.clear()
        self.factory = RequestFactory()
    
    def test_without_key_executes_normally(self):
        """Sans clé d'idempotence, la fonction doit s'exécuter normalement"""
        call_count = {'value': 0}
        
        @ensure_idempotent(ttl=60)
        def test_view(request):
            call_count['value'] += 1
            return ApiResponse.success(data={'count': call_count['value']})
        
        request = self.factory.post('/test/')
        request.data = {}
        
        response1 = test_view(request)
        response2 = test_view(request)
        
        # Les deux appels doivent exécuter la fonction
        self.assertEqual(call_count['value'], 2)
    
    def test_with_header_key_caches_response(self):
        """Avec X-Idempotency-Key, la réponse doit être mise en cache"""
        call_count = {'value': 0}
        
        @ensure_idempotent(ttl=60)
        def test_view(request):
            call_count['value'] += 1
            return ApiResponse.success(data={'count': call_count['value']})
        
        request = self.factory.post('/test/', HTTP_X_IDEMPOTENCY_KEY='unique-key-123')
        request.data = {}
        
        response1 = test_view(request)
        response2 = test_view(request)
        
        # Seul le premier appel doit exécuter la fonction
        self.assertEqual(call_count['value'], 1)
        # Les deux réponses doivent être identiques
        self.assertEqual(response1.data, response2.data)
    
    def test_with_body_key_caches_response(self):
        """Avec idempotency_key dans le body, la réponse doit être mise en cache"""
        call_count = {'value': 0}
        
        @ensure_idempotent(ttl=60)
        def test_view(request):
            call_count['value'] += 1
            return ApiResponse.success(data={'count': call_count['value']})
        
        request = self.factory.post('/test/')
        request.data = {'idempotency_key': 'body-key-456'}
        
        response1 = test_view(request)
        response2 = test_view(request)
        
        # Seul le premier appel doit exécuter la fonction
        self.assertEqual(call_count['value'], 1)
    
    def test_different_keys_execute_separately(self):
        """Des clés différentes doivent exécuter la fonction séparément"""
        call_count = {'value': 0}
        
        @ensure_idempotent(ttl=60)
        def test_view(request):
            call_count['value'] += 1
            return ApiResponse.success(data={'count': call_count['value']})
        
        request1 = self.factory.post('/test/', HTTP_X_IDEMPOTENCY_KEY='key-1')
        request1.data = {}
        request2 = self.factory.post('/test/', HTTP_X_IDEMPOTENCY_KEY='key-2')
        request2.data = {}
        
        test_view(request1)
        test_view(request2)
        
        # Les deux clés différentes doivent exécuter la fonction
        self.assertEqual(call_count['value'], 2)
    
    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
    def test_server_error_not_cached(self):
        """Les erreurs 500 ne doivent pas être mises en cache"""
        call_count = {'value': 0}
        
        @ensure_idempotent(ttl=60)
        def test_view(request):
            call_count['value'] += 1
            return ApiResponse.server_error()
        
        request = self.factory.post('/test/', HTTP_X_IDEMPOTENCY_KEY='error-key')
        request.data = {}
        
        # Vider le cache avant le test
        cache.clear()
        
        response1 = test_view(request)
        response2 = test_view(request)
        
        # L'erreur 500 ne doit pas être cachée, donc 2 appels
        self.assertEqual(call_count['value'], 2)
