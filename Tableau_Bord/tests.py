import pytest
from django.test import TestCase
from django.utils import timezone


@pytest.mark.django_db
class TestTableauBordViews(TestCase):
    """Tests pour les vues du Tableau de Bord"""

    def test_api_kpi_view_exists(self):
        """Test que la vue API KPI existe"""
        from Tableau_Bord.views import api_kpi
        self.assertTrue(callable(api_kpi))

    def test_api_evo_conso_view_exists(self):
        """Test que la vue API Evolution Consommation existe"""
        from Tableau_Bord.views import api_evo_conso
        self.assertTrue(callable(api_evo_conso))
