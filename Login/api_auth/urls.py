from django.urls import path

from Login.api_auth.views import (
    authentification,
    check_server,
    upload_apk,
    get_mobile_version,
    generate_download_token,
    download_with_token,
    refresh_token,
)

urlpatterns = [
    path('authentification', authentification),
    path('refresh/', refresh_token, name='refresh_token'),
    path('serveurTest/', check_server, name='check_server_availability'),
    path('upload-apk/', upload_apk, name='upload_apk'),
    path('version/', get_mobile_version, name='get_mobile_version'),
    path('generate-token/', generate_download_token, name='generate_download_token'),
    path('download/<str:token_string>/', download_with_token, name='download_with_token'),
]
