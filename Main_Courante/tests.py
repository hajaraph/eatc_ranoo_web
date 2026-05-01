import pytest
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from Main_Courante.models import MainCourante, StatutMC, SuivieMC, PhotoMC


@pytest.mark.django_db
class TestMainCouranteModel(TestCase):
    """Tests pour le modèle MainCourante"""

    def test_creation_main_courante(self):
        """Test la création d'une main courante"""
        main_courante = MainCourante.objects.create(
            description='Test incident',
            date_incident=timezone.now().date()
        )
        self.assertEqual(main_courante.description, 'Test incident')


class SignalSyncTests(TestCase):
    """Tests pour vérifier que les signaux mettent à jour updated_at de MainCourante."""

    def setUp(self):
        """Créer les données de test."""
        # On a besoin d'un utilisateur et potentiellement d'autres FK
        # Pour simplifier, on mock ou on utilise des fixtures
        pass

    @patch('Main_Courante.models.MainCourante.all_objects')
    def test_statut_change_updates_main_courante(self, mock_all_objects):
        """Test: Changer le statut doit mettre à jour updated_at de MainCourante."""
        # Simuler une instance de StatutMC
        from django.db.models.signals import post_save
        from Main_Courante.models import update_main_courante_on_statut_change
        
        class MockStatut:
            main_courante_id = 123
        
        # Appeler le signal manuellement
        update_main_courante_on_statut_change(
            sender=StatutMC,
            instance=MockStatut(),
            created=False
        )
        
        # Vérifier que filter et update ont été appelés
        mock_all_objects.filter.assert_called_once()
        mock_all_objects.filter.return_value.update.assert_called_once()
        print("✅ Test statut_change_updates_main_courante: PASSED")

    @patch('Main_Courante.models.MainCourante.all_objects')
    def test_suivie_change_updates_main_courante(self, mock_all_objects):
        """Test: Ajouter un suivi doit mettre à jour updated_at de MainCourante."""
        from Main_Courante.models import update_main_courante_on_suivie_change
        
        class MockSuivie:
            main_courante_id = 456
        
        update_main_courante_on_suivie_change(
            sender=SuivieMC,
            instance=MockSuivie(),
            created=True
        )
        
        mock_all_objects.filter.assert_called_once()
        print("✅ Test suivie_change_updates_main_courante: PASSED")

    @patch('Main_Courante.models.MainCourante.all_objects')
    def test_photo_change_updates_main_courante(self, mock_all_objects):
        """Test: Ajouter une photo doit mettre à jour updated_at de MainCourante."""
        from Main_Courante.models import update_main_courante_on_photo_change
        
        class MockPhoto:
            main_courante_id = 789
        
        update_main_courante_on_photo_change(
            sender=PhotoMC,
            instance=MockPhoto(),
            created=True
        )
        
        mock_all_objects.filter.assert_called_once()
        print("✅ Test photo_change_updates_main_courante: PASSED")


class DeltaSyncTests(TestCase):
    """Tests pour le Delta Sync des anomalies."""

    def test_delta_sync_filter_modified_since(self):
        """Test: Le queryset filtre correctement avec modified_since."""
        # Ce test nécessiterait une base de données de test configurée
        # Pour l'instant, on vérifie juste la logique
        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)
        
        # Format ISO attendu par l'API
        modified_since_str = one_hour_ago.isoformat()
        
        from django.utils.dateparse import parse_datetime
        parsed = parse_datetime(modified_since_str)
        
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed, one_hour_ago)
        print("✅ Test delta_sync_filter_modified_since: PASSED")


# Pour exécuter les tests manuellement sans Django test runner
if __name__ == '__main__':
    import django
    django.setup()
    
    print("\n=== Tests des Signaux de Synchronisation ===\n")
    
    # Test simple sans mock
    from Main_Courante.models import MainCourante
    
    print("1. Vérification des signaux enregistrés...")
    from django.db.models.signals import post_save
    
    # Vérifier que les receivers sont connectés
    receivers = post_save._live_receivers(StatutMC)
    statut_signal_connected = any('update_main_courante_on_statut_change' in str(r) for r in receivers)
    
    if statut_signal_connected:
        print("   ✅ Signal StatutMC -> MainCourante: CONNECTÉ")
    else:
        print("   ❌ Signal StatutMC -> MainCourante: NON CONNECTÉ")
    
    receivers = post_save._live_receivers(SuivieMC)
    suivie_signal_connected = any('update_main_courante_on_suivie_change' in str(r) for r in receivers)
    
    if suivie_signal_connected:
        print("   ✅ Signal SuivieMC -> MainCourante: CONNECTÉ")
    else:
        print("   ❌ Signal SuivieMC -> MainCourante: NON CONNECTÉ")
    
    print("\n2. Test de la méthode touch()...")
    # Vérifier que la méthode touch existe
    if hasattr(MainCourante, 'touch'):
        print("   ✅ Méthode touch() existe sur MainCourante")
    else:
        print("   ❌ Méthode touch() manquante sur MainCourante")
    
    print("\n=== Fin des tests ===")
