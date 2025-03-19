from django.urls import path

from Acommune.views import region, CommuneNew, supp_commune
from Ranoo_Config.views import TarifMod

urlpatterns = [
    path('region', region, name='region'),
    path('region/nouveau/commune', CommuneNew.as_view(), name='commune_new'),
    path('region/supprimer/commune?=?<str:pk>', supp_commune, name='supp_commune'),
]