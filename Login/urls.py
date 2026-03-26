from django.urls import path

from Login.views import Authentification, deconnexion, mobile_app_page

urlpatterns = [
    path('', Authentification.as_view(), name='authentification'),
    path('deconnexion', deconnexion, name='deconnexion'),
    path('mobile-app/', mobile_app_page, name='mobile_app'),
]
