from django.urls import path

from Depense.views import depense, DepenseNew, depense_suppression, export_depense, calculate_depense_total, \
    categorie_liste, CategorieNew, categorie_suppression

urlpatterns = [
    path('list', depense, name='depense'),
    path('nouveau', DepenseNew.as_view(), name='depense_new'),
    path('suppression/<int:pk>', depense_suppression, name='depense_suppression'),
    path('export/', export_depense, name='export_depense'),
    path('calculate_total/', calculate_depense_total, name='calculate_depense_total'),
    path('categorie/list', categorie_liste, name='categorie_liste'),
    path('categorie/nouveau', CategorieNew.as_view(), name='categorie_new'),
    path('categorie/suppression/<str:pk>', categorie_suppression, name='categorie_suppression'),
]