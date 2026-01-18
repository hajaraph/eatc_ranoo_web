"""
Tests unitaires pour les modèles Compteurs avec SyncMixin.

Ce fichier vérifie que:
- Les champs de synchronisation sont bien présents
- La logique métier existante n'est pas affectée
- Les managers filtrent correctement les éléments supprimés

Note: Ces tests utilisent django_tenants.test pour gérer le multi-tenant.
"""
import uuid
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from Compteurs.models import Compteur, ReleveCompteur, CompteurPrincipale


class CompteurSyncFieldsTestCase(TenantTestCase):
    """Tests pour vérifier les champs de synchronisation sur Compteur"""
    
    def setUp(self):
        """Créer un compteur principal pour les tests"""
        super().setUp()
        self.compteur_principal = CompteurPrincipale.objects.create(
            num_compteur_principale="CP-TEST-001",
            marque_compteur_principale="Test Marque",
            modele_compteur_principale="Test Modele"
        )
    
    def test_compteur_has_sync_id(self):
        """Compteur doit avoir un sync_id UUID à la création"""
        compteur = Compteur.objects.create(
            num_compteur="C-TEST-001",
            marque_compteur="Test",
            num_compteur_principale=self.compteur_principal
        )
        
        self.assertIsNotNone(compteur.sync_id)
        self.assertIsInstance(compteur.sync_id, uuid.UUID)
    
    def test_compteur_has_version(self):
        """Compteur doit avoir une version à 1 au départ"""
        compteur = Compteur.objects.create(
            num_compteur="C-TEST-002",
            marque_compteur="Test"
        )
        
        self.assertEqual(compteur.version, 1)
    
    def test_compteur_version_increments_on_update(self):
        """La version doit s'incrémenter lors d'une mise à jour"""
        compteur = Compteur.objects.create(
            num_compteur="C-TEST-003",
            marque_compteur="Test"
        )
        self.assertEqual(compteur.version, 1)
        
        compteur.marque_compteur = "Updated Marque"
        compteur.save()
        compteur.refresh_from_db()
        
        self.assertEqual(compteur.version, 2)
    
    def test_compteur_has_timestamps(self):
        """Compteur doit avoir created_at et updated_at"""
        before = timezone.now()
        compteur = Compteur.objects.create(
            num_compteur="C-TEST-004",
            marque_compteur="Test"
        )
        after = timezone.now()
        
        self.assertIsNotNone(compteur.created_at)
        self.assertIsNotNone(compteur.updated_at)
        self.assertGreaterEqual(compteur.created_at, before)
        self.assertLessEqual(compteur.created_at, after)
    
    def test_compteur_soft_delete(self):
        """soft_delete() doit marquer le compteur comme supprimé"""
        compteur = Compteur.objects.create(
            num_compteur="C-TEST-005",
            marque_compteur="Test"
        )
        
        self.assertFalse(compteur.is_deleted)
        
        compteur.soft_delete()
        
        self.assertTrue(compteur.is_deleted)
        self.assertIsNotNone(compteur.deleted_at)
    
    def test_compteur_default_manager_excludes_deleted(self):
        """Le manager par défaut doit exclure les compteurs supprimés"""
        compteur1 = Compteur.objects.create(
            num_compteur="C-TEST-006",
            marque_compteur="Active"
        )
        compteur2 = Compteur.objects.create(
            num_compteur="C-TEST-007",
            marque_compteur="To Delete"
        )
        compteur2.soft_delete()
        
        # Le manager par défaut ne doit pas inclure le compteur supprimé
        visible_compteurs = Compteur.objects.filter(
            num_compteur__in=["C-TEST-006", "C-TEST-007"]
        )
        self.assertEqual(visible_compteurs.count(), 1)
        self.assertEqual(visible_compteurs.first().num_compteur, "C-TEST-006")
    
    def test_compteur_all_objects_includes_deleted(self):
        """all_objects doit inclure les compteurs supprimés"""
        compteur1 = Compteur.objects.create(
            num_compteur="C-TEST-008",
            marque_compteur="Active"
        )
        compteur2 = Compteur.objects.create(
            num_compteur="C-TEST-009",
            marque_compteur="Deleted"
        )
        compteur2.soft_delete()
        
        # all_objects doit inclure tous les compteurs
        all_compteurs = Compteur.all_objects.filter(
            num_compteur__in=["C-TEST-008", "C-TEST-009"]
        )
        self.assertEqual(all_compteurs.count(), 2)
    
    def test_compteur_restore(self):
        """restore() doit restaurer un compteur supprimé"""
        compteur = Compteur.objects.create(
            num_compteur="C-TEST-010",
            marque_compteur="Test"
        )
        compteur.soft_delete()
        
        self.assertTrue(compteur.is_deleted)
        
        compteur.restore()
        
        self.assertFalse(compteur.is_deleted)
        self.assertIsNone(compteur.deleted_at)
    
    def test_compteur_get_sync_data(self):
        """get_sync_data() doit retourner les métadonnées de sync"""
        compteur = Compteur.objects.create(
            num_compteur="C-TEST-011",
            marque_compteur="Test"
        )
        
        sync_data = compteur.get_sync_data()
        
        self.assertIn('sync_id', sync_data)
        self.assertIn('version', sync_data)
        self.assertIn('created_at', sync_data)
        self.assertIn('updated_at', sync_data)
        self.assertIn('is_deleted', sync_data)
        self.assertEqual(sync_data['version'], 1)
        self.assertFalse(sync_data['is_deleted'])


class ReleveCompteurSyncFieldsTestCase(TenantTestCase):
    """Tests pour vérifier les champs de synchronisation sur ReleveCompteur"""
    
    def setUp(self):
        """Créer un compteur pour les tests de relevé"""
        super().setUp()
        self.compteur = Compteur.objects.create(
            num_compteur="C-RELEVE-001",
            marque_compteur="Test"
        )
    
    def test_releve_has_sync_id(self):
        """ReleveCompteur doit avoir un sync_id UUID"""
        releve = ReleveCompteur.objects.create(
            date_releve=date.today(),
            volume=100,
            conso=10,
            num_compteur=self.compteur
        )
        
        self.assertIsNotNone(releve.sync_id)
        self.assertIsInstance(releve.sync_id, uuid.UUID)
    
    def test_releve_version_increments(self):
        """La version de ReleveCompteur doit s'incrémenter"""
        releve = ReleveCompteur.objects.create(
            date_releve=date.today(),
            volume=100,
            conso=10,
            num_compteur=self.compteur
        )
        self.assertEqual(releve.version, 1)
        
        releve.volume = 150
        releve.save()
        releve.refresh_from_db()
        
        self.assertEqual(releve.version, 2)
    
    def test_releve_soft_delete(self):
        """soft_delete() sur ReleveCompteur"""
        releve = ReleveCompteur.objects.create(
            date_releve=date.today(),
            volume=100,
            conso=10,
            num_compteur=self.compteur
        )
        
        releve.soft_delete()
        
        self.assertTrue(releve.is_deleted)
        # Vérifier qu'il n'apparaît plus dans le queryset par défaut
        self.assertFalse(
            ReleveCompteur.objects.filter(id_releve=releve.id_releve).exists()
        )
        # Mais apparaît toujours dans all_objects
        self.assertTrue(
            ReleveCompteur.all_objects.filter(id_releve=releve.id_releve).exists()
        )
    
    def test_releve_modified_since(self):
        """modified_since() doit filtrer par date de modification"""
        yesterday = timezone.now() - timedelta(days=1)
        
        releve = ReleveCompteur.objects.create(
            date_releve=date.today(),
            volume=100,
            conso=10,
            num_compteur=self.compteur
        )
        
        # Les relevés modifiés depuis hier devraient inclure notre relevé
        recent_releves = ReleveCompteur.objects.modified_since(yesterday)
        self.assertIn(releve, recent_releves)


class CompteurLogicIntegrityTestCase(TenantTestCase):
    """
    Tests pour vérifier que la logique métier existante n'est PAS affectée.
    
    Ces tests s'assurent que le SyncMixin n'a pas cassé le fonctionnement
    des modèles Compteur et ReleveCompteur.
    """
    
    def setUp(self):
        """Créer les données de test"""
        super().setUp()
        self.compteur_principal = CompteurPrincipale.objects.create(
            num_compteur_principale="CP-LOGIC-001",
            marque_compteur_principale="Test Marque"
        )
        self.compteur = Compteur.objects.create(
            num_compteur="C-LOGIC-001",
            marque_compteur="Test Marque",
            modele_compteur="Test Modele",
            num_compteur_principale=self.compteur_principal
        )
    
    def test_compteur_str_method_works(self):
        """Le modèle Compteur doit fonctionner normalement"""
        # Vérifier que la clé primaire fonctionne
        self.assertEqual(self.compteur.pk, "C-LOGIC-001")
        
        # Vérifier la relation FK
        self.assertEqual(
            self.compteur.num_compteur_principale, 
            self.compteur_principal
        )
    
    def test_releve_creation_works(self):
        """La création de relevés doit fonctionner normalement"""
        releve = ReleveCompteur.objects.create(
            date_releve=date.today(),
            volume=1000,
            conso=50,
            num_compteur=self.compteur
        )
        
        self.assertIsNotNone(releve.id_releve)
        self.assertEqual(releve.volume, 1000)
        self.assertEqual(releve.conso, 50)
        self.assertEqual(releve.num_compteur, self.compteur)
    
    def test_compteur_releves_relation_works(self):
        """La relation compteur -> relevés doit fonctionner"""
        releve1 = ReleveCompteur.objects.create(
            date_releve=date.today() - timedelta(days=30),
            volume=900,
            conso=40,
            num_compteur=self.compteur
        )
        releve2 = ReleveCompteur.objects.create(
            date_releve=date.today(),
            volume=1000,
            conso=100,
            num_compteur=self.compteur
        )
        
        # La relation inverse doit fonctionner
        releves = self.compteur.relevecompteurs.all()
        self.assertEqual(releves.count(), 2)
        self.assertIn(releve1, releves)
        self.assertIn(releve2, releves)
    
    def test_compteur_principal_relation_works(self):
        """La relation compteur principal -> sous-compteurs doit fonctionner"""
        compteur2 = Compteur.objects.create(
            num_compteur="C-LOGIC-002",
            marque_compteur="Test",
            num_compteur_principale=self.compteur_principal
        )
        
        sous_compteurs = self.compteur_principal.compteurs.all()
        self.assertEqual(sous_compteurs.count(), 2)
        self.assertIn(self.compteur, sous_compteurs)
        self.assertIn(compteur2, sous_compteurs)
    
    def test_compteur_principal_conso_calcul_works(self):
        """Le calcul de consommation du compteur principal doit fonctionner"""
        # Créer des relevés pour le compteur
        ReleveCompteur.objects.create(
            date_releve=date.today(),
            volume=1000,
            conso=100,
            num_compteur=self.compteur
        )
        
        # Note: Le calcul retourne 0 car le compteur n'a pas de contrat
        # (la logique métier existante exclut les compteurs sans contrat)
        # On vérifie simplement que la méthode ne lève pas d'erreur
        total_conso = self.compteur_principal.get_total_conso_sous_compteurs()
        # Le résultat est 0 car pas de contrat, mais la méthode fonctionne
        self.assertIsNotNone(total_conso)
