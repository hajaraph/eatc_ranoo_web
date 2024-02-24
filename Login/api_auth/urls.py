from django.urls import path

from Login.api_auth.views import authentification,get_users ,donne_tout,check_server

urlpatterns = [
    path('authentification', authentification),
    path('getUsers/', get_users),
    path('serveurTest/', check_server, name='check_server_availability'),
    path('donnee', donne_tout) 
]
