from django.urls import path

from Facturation.views import facture, facture_restant, facture_retard, facture_avoir, facture_etat_detail,\
    facture_genere_pdf, facture_paiement, facture_impaye, facture_paye

urlpatterns = [
    path('list', facture, name='facture'),
    path('detail/num_facture=<str:num_facture>', facture_etat_detail, name='facture_etat_detail'),
    path('paye', facture_paye, name='facture_paye'),
    path('impaye', facture_impaye, name='facture_impaye'),
    path('restant', facture_restant, name='facture_restant'),
    path('retard', facture_retard, name='facture_retard'),
    path('avoir', facture_avoir, name='facture_avoir'),
    path('paiement', facture_paiement, name='facture_paiement'),
    path('pdf/num_facture=<str:pk>', facture_genere_pdf, name='facture_genere_pdf')
]
