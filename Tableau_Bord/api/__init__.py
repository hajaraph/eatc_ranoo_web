"""
APIs REST pour le Tableau de Bord.

Ce package contient les vues API pour le dashboard Admin/Gestionnaire.
"""

from .views import (
    dashboard_kpi,
    dashboard_evo_conso,
    dashboard_factures_statut,
    dashboard_anomalies_statut,
)

__all__ = [
    'dashboard_kpi',
    'dashboard_evo_conso',
    'dashboard_factures_statut',
    'dashboard_anomalies_statut',
]
