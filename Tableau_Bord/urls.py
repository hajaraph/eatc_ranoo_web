from django.urls import path

from Tableau_Bord.views import tableau_bord, importe
from Tableau_Bord.views import (
    api_kpi_globaux,
    api_evo_conso_commune,
    api_statut_factures,
    api_statut_main_courante,
    api_factures_par_type_client,
    api_conso_par_type_client,
    api_debit_par_commune,
    api_marnage_par_commune
)

urlpatterns = [
    path('', tableau_bord, name='tableau_bord'),
    path('import', importe, name='import'),
    
    # Anciennes APIs (JsonResponse simples - pour le web)
    path('kpi-globaux/', api_kpi_globaux, name='api_kpi_globaux'),
    path('evo-conso-commune/', api_evo_conso_commune, name='api_evo_conso_commune'),
    path('statut-factures/', api_statut_factures, name='api_statut_factures'),
    path('statut-main-courante/', api_statut_main_courante, name='api_statut_main_courante'),
    path('factures-par-type-client/', api_factures_par_type_client, name='api_factures_par_type_client'),
    path('conso-par-type-client/', api_conso_par_type_client, name='api_conso_par_type_client'),
    path('debit-par-commune/', api_debit_par_commune, name='api_debit_par_commune'),
    path('marnage-par-commune/', api_marnage_par_commune, name='api_marnage_par_commune'),
]
