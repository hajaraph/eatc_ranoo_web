from django.urls import path
from .views import (
    TypeClientListView, TypeClientDetailView,
    ClientListView, ClientDetailView,
    PieceClientListView, PieceClientDetailView,
    ContratListView, ContratDetailView
)

urlpatterns = [
    # TypeClient endpoints
    path('type-clients/', TypeClientListView.as_view(), name='type-client-list'),
    path('type-clients/<int:pk>/', TypeClientDetailView.as_view(), name='type-client-detail'),
    
    # Client endpoints
    path('clients/', ClientListView.as_view(), name='client-list'),
    path('clients/<int:pk>/', ClientDetailView.as_view(), name='client-detail'),
    
    # PieceClient endpoints
    path('pieces/', PieceClientListView.as_view(), name='piece-client-list'),
    path('pieces/<int:pk>/', PieceClientDetailView.as_view(), name='piece-client-detail'),
    
    # Contrat endpoints
    path('contrats/', ContratListView.as_view(), name='contrat-list'),
    path('contrats/<str:num_contrat>/', ContratDetailView.as_view(), name='contrat-detail'),
]
