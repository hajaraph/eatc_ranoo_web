from django.contrib import admin
from django.urls import path

from Login.views import Authentification, deconnexion

urlpatterns = [
    path('', Authentification.as_view(), name='authentification'),
    path('deconnexion', deconnexion, name='deconnexion'),
    path('admin', admin.site.urls),
]
