from django.urls import path

from Login.api_auth.views import authentification, check_server, upload_apk, get_mobile_version

urlpatterns = [
    path('authentification', authentification),
    path('serveurTest/', check_server, name='check_server_availability'),
    path('upload-apk/', upload_apk, name='upload_apk'),
    path('version/', get_mobile_version, name='get_mobile_version'),
]
