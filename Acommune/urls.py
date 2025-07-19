from django.urls import path

from Acommune.views import region, CommuneNew, supp_commune, commune_list, commune_list_by_region

urlpatterns = [
    path('region', region, name='region'),
    path('region/nouveau/commune', CommuneNew.as_view(), name='commune_new'),
    path('region/supprimer/commune?=?<str:pk>', supp_commune, name='supp_commune'),
    path('nouveau/province/<str:province>', commune_list, name='commune_list'),
    path('commune/region/<str:region_name>', commune_list_by_region, name='commune_list_by_region')
]