from django.urls import path

from Compteurs.api_compteur.views import accueil, Missions
from Login.api_auth.views import donne_tout

urlpatterns = [
    path('donnee', donne_tout),
    path('accueil', accueil),
    path('missions', Missions.as_view())
]
