from django.urls import path

from Login.views import Authentification, deconnexion, mobile_app_page, download_apk

urlpatterns = [
    path('', Authentification.as_view(), name='authentification'),
    path('deconnexion', deconnexion, name='deconnexion'),
    path('mobile-app/', mobile_app_page, name='mobile_app'),
    path('download-apk/', download_apk, name='download_apk'),
]
