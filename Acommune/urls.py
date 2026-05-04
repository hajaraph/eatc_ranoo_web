from django.urls import path

from Acommune.views import (
    commune_list
)

urlpatterns = [
    # URL existante pour compatibilité
    path('nouveau/province/<str:province>', commune_list, name='commune_list'),
]