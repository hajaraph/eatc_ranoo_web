from django.urls import path
from Compteurs.api_compteur.views import accueil, Missions, relever_client, FactureDetail, SynchronisationView
from Login.api_auth.views import donne_tout

urlpatterns = [
    path('donnee', donne_tout),
    path('accueil', accueil),
    path('missions', Missions.as_view()),
    path('releverClient', relever_client),
    path('facture', FactureDetail.as_view()),
    path('synchronisation', SynchronisationView.as_view()),  # Ajout de la vue pour la synchronisation
]
