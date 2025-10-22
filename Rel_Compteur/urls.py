from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('', include('Login.urls')),
    path('admin', admin.site.urls),
    path('tableau_bord/', include('Tableau_Bord.urls')),
    path('clients/', include('Clients.urls')),
    path('compteurs/', include('Compteurs.urls')),
    path('facture/', include('Facturation.urls')),
    path('main_courante/', include('Main_Courante.urls')),
    path('parametre/', include('Parametre.urls')),
    path('ranoo_config/', include([
        path('', include('Ranoo_Config.urls')),
        path('', include('Acommune.urls')),
    ])),
    path('recette/', include('Recette.urls')),
    path('depense/', include('Depense.urls')),
    # path('rubrique/', include('Rubrique.urls')),
    path('api/', include([
        path('', include('Login.api_auth.urls')),
        path('', include('Compteurs.api_compteur.urls')),
        path('', include('Main_Courante.api_anomalie.urls')),
    ])),
    path('__reload__', include('django_browser_reload.urls'))
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
