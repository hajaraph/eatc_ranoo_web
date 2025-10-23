from django.urls import path

from Rubrique.views import debit, DebitNew

urlpatterns = [
    path('debit', debit, name='debit'),
    path('debit/nouveau', DebitNew.as_view(), name='debit_new'),
]