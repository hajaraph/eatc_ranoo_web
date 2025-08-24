from django.urls import path

from Recette.views import recette, RecetteCreateView, supprimer_recette

urlpatterns = [
    path('liste', recette, name='recette_list'),
    path('nouveau', RecetteCreateView.as_view(), name='recette_new'),
    path('suppression/<int:pk>', supprimer_recette, name='recette_suppression'),
]