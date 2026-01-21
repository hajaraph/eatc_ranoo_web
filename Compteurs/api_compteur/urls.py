from django.urls import path

from .views import Missions, accueil, FactureDetail, relever_client
from .sync_views import (
    sync_status,
    sync_compteurs,
    sync_releves,
    BatchSyncView,
    create_releve_idempotent,
)

urlpatterns = [
    path('accueil', accueil),
    path('missions', Missions.as_view()),
    path('releverClient', relever_client),
    path('facture', FactureDetail.as_view()),
    
    # Nouveaux endpoints de synchronisation
    path('sync/status', sync_status, name='sync-status'),
    path('sync/compteurs', sync_compteurs, name='sync-compteurs'),
    path('sync/releves', sync_releves, name='sync-releves'),
    path('sync/batch', BatchSyncView.as_view(), name='sync-batch'),
    path('sync/releve/create', create_releve_idempotent, name='sync-releve-create'),
]

