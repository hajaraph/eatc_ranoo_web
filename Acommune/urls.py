from django.urls import path

from Acommune.views import (
    commune_list,
    province_list_api,
    regions_by_province_api,
    communes_by_region_api,
    communes_by_province_api,
    commune_detail_api
)

urlpatterns = [
    # URL existante pour compatibilité
    path('nouveau/province/<str:province>', commune_list, name='commune_list'),
    
    # ===== API REST pour la cascade Province → Région → Commune =====
    
    # Lister toutes les provinces
    path('api/communes/provinces/', province_list_api, name='province_list_api'),
    
    # Lister les régions d'une province
    path('api/communes/provinces/<int:province_id>/regions/', regions_by_province_api, name='regions_by_province_api'),
    
    # Lister les communes d'une région
    path('api/communes/regions/<int:region_id>/communes/', communes_by_region_api, name='communes_by_region_api'),
    
    # Lister toutes les communes d'une province (cascade complète)
    path('api/communes/provinces/<int:province_id>/communes/', communes_by_province_api, name='communes_by_province_api'),
    
    # Détails d'une commune spécifique
    path('api/communes/<str:cp_commune>/', commune_detail_api, name='commune_detail_api'),
]