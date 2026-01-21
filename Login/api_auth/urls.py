from django.urls import path

from Login.api_auth.views import authentification, check_server

urlpatterns = [
    path('authentification', authentification),
    path('serveurTest/', check_server, name='check_server_availability'),
]
