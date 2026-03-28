"""
URLs pour les APIs REST du Tableau de Bord.

Ces endpoints sont accessibles via /api/dashboard/ et sont réservés aux
Administrateurs et Gestionnaires (online-only).

Endpoints:
    GET /api/dashboard/kpi/ - KPI globaux
    GET /api/dashboard/evo-conso/ - Évolution consommation (6 mois)
    GET /api/dashboard/factures-statut/ - Statut factures (payées/impayées)
    GET /api/dashboard/anomalies-statut/ - Statut anomalies (non_traite/en_cours/realise)
"""

from django.urls import path

from .views import (
    dashboard_kpi,
    dashboard_evo_conso,
    dashboard_factures_statut,
    dashboard_anomalies_statut,
)

urlpatterns = [
    path('kpi', dashboard_kpi, name='api-admin-dashboard-kpi'),
    path('evo-conso', dashboard_evo_conso, name='api-admin-dashboard-evo-conso'),
    path('factures-statut', dashboard_factures_statut, name='api-admin-dashboard-factures-statut'),
    path('anomalies-statut', dashboard_anomalies_statut, name='api-admin-dashboard-anomalies-statut'),
]
