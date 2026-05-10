from django.urls import path
from .views import (
    FactureListView,
    FactureDetailView,
    FacturePaiementView,
)

urlpatterns = [
    path('', FactureListView.as_view(), name='api-facture-list'),
    path('<int:pk>/', FactureDetailView.as_view(), name='api-facture-detail'),
    path('<int:pk>/paiement/', FacturePaiementView.as_view(), name='api-facture-paiement'),
]
