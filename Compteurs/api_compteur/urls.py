from django.urls import path

from Login.api_auth.views import donne_tout
from . import views, cache_views
from .views import Missions, accueil, FactureDetail, relever_client

urlpatterns = [
    path('donnee', donne_tout),
    path('accueil', accueil),
    path('missions', Missions.as_view()),
    path('releverClient', relever_client),
    path('facture', FactureDetail.as_view()),
]
