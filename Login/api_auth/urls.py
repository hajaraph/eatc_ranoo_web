from django.urls import path

from Login.api_auth.views import authentification, donne_tout

urlpatterns = [
    path('authentification', authentification),
    path('donnee', donne_tout)
]
