from django.urls import path

from Main_Courante.api_anomalie.views import DeclareMaincourate

urlpatterns = [
    path('anomalie', DeclareMaincourate.as_view())
]
