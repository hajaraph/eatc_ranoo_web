from django.urls import path

from Rubrique.views import DebitNew, DebitList, DebitMod, DebitDelete, MarnageList, MarnageNew, MarnageMod, MarnageDelete

urlpatterns = [
    path('debit', DebitList.as_view(), name='debit'),
    path('debit/nouveau', DebitNew.as_view(), name='debit_new'),
    path('debit/<int:pk>/modification', DebitMod.as_view(), name='debit_mod'),
    path('debit/<int:pk>/suppression', DebitDelete.as_view(), name='debit_delete'),
    
    # URLs pour le CRUD Marnage
    path('marnage', MarnageList.as_view(), name='marnage'),
    path('marnage/nouveau', MarnageNew.as_view(), name='marnage_new'),
    path('marnage/<int:pk>/modification', MarnageMod.as_view(), name='marnage_mod'),
    path('marnage/<int:pk>/suppression', MarnageDelete.as_view(), name='marnage_delete')
]