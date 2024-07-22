from django.urls import path

from Main_Courante.api_anomalie.views import DeclareMaincourate, suivie_mc

urlpatterns = [
    path('anomalie', DeclareMaincourate.as_view()),
    path('commentaire', suivie_mc)
]
