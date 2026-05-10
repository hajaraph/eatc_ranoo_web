from django.urls import path, include

from Facturation.views import facture, facture_restant, facture_retard, facture_avoir, facture_etat_detail, \
    facture_genere_pdf, facture_paiement, facture_impaye, facture_paye, generate_multiple_pages_pdf, \
    facture_export_excel, facture_supprimer, check_pdf_task_status, download_generated_pdf

urlpatterns = [
    path('api/', include('Facturation.api_facture.urls')),
    path('list', facture, name='facture'),
    path('detail/num_facture=<str:num_facture>', facture_etat_detail, name='facture_etat_detail'),
    path('paye', facture_paye, name='facture_paye'),
    path('impaye', facture_impaye, name='facture_impaye'),
    path('restant', facture_restant, name='facture_restant'),
    path('retard', facture_retard, name='facture_retard'),
    path('avoir', facture_avoir, name='facture_avoir'),
    path('paiement', facture_paiement, name='facture_paiement'),
    path('excel', facture_export_excel, name='facture_export_excel'),
    path('pdf/num_facture=<str:num_facture>', facture_genere_pdf, name='facture_genere_pdf'),
    path('supprimer/num_facture=<str:num_facture>', facture_supprimer, name='facture_supprimer'),
    path('pdf', generate_multiple_pages_pdf, name='generate_multiple_pages_pdf'),
    # Endpoints Celery pour la génération PDF asynchrone
    path('pdf/status/<str:task_id>/', check_pdf_task_status, name='check_pdf_task_status'),
    path('pdf/download/<str:filename>/', download_generated_pdf, name='download_generated_pdf'),
]
