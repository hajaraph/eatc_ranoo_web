from django.urls import path

from Clients.views import client_liste, client_contrat, ClientNew, ContratNew, ClientContrat, \
    ClientDetail, supp_file_client, export_clients, delete_client, genere_pdf_contrat, supp_contrat, export_clients_pdf, \
    liste_num_client_lte, get_clients_by_commune

urlpatterns = [
    path('liste', client_liste, name='client_liste'),
    path('nouveau', ClientNew.as_view(), name='client_new'),
    path('contrat', client_contrat, name='client_contrat'),
    path('contrat/nouveau', ContratNew.as_view(), name='client_new_contrat'),
    path('detail/contact=<str:pk>', ClientDetail.as_view(), name='client_detail'),
    path('detail/contrat=<str:pk>', ClientContrat.as_view(), name='client_li_contrat'),
    path('supprimer/file/id_client=<int:pk>', supp_file_client, name='supp_file_client'),
    path('excel', export_clients, name='export_clients'),
    path('supprimer/id_client=<int:pk>', delete_client, name='client_delete'),
    path('suppression/num_contrat=<str:pk>', supp_contrat, name='supp_contrat'),
    path('pdf/num_contrat=<str:pk>', genere_pdf_contrat, name='genere_pdf_contrat'),
    path('pdf/client', export_clients_pdf, name='export_clients_pdf'),
    path('liste/num_client_deb=<str:num_client_deb>', liste_num_client_lte, name='liste_num_client_lte'),
    path('liste/num_client_by_commune/', get_clients_by_commune, name='get_clients_by_commune')
]
