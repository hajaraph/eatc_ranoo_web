from django.urls import path

from Depense.views import depense, DepenseNew, depense_suppression

urlpatterns = [
    path('list', depense, name='depense'),
    path('nouveau', DepenseNew.as_view(), name='depense_new'),
    path('suppression/<int:pk>', depense_suppression, name='depense_suppression'),
]