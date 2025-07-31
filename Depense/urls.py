from django.urls import path

from Depense.views import depense

urlpatterns = [
    path('list', depense, name='depense'),
]