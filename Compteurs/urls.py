from django.urls import path

from Compteurs.views import compteur_liste, CompteurNew, CompteurDetail, compteur_releve, ReleveNew, \
    ReleveMod, del_releve, compteur_supp, export_compteur, export_relever

urlpatterns = [
    path('liste', compteur_liste, name='compteur_list'),
    path('nouveau/compteur', CompteurNew.as_view(), name='compteur_new'),
    path('compteur/detail=?<str:pk>', CompteurDetail.as_view(), name='compteur_detail'),
    path('supprimer/compteur=?<str:pk>', compteur_supp, name='compteur_supp'),
    path('releve', compteur_releve, name='compteur_releve'),
    path('nouveau/releve=?<str:num_compteur>', ReleveNew.as_view(), name='releve_new'),
    # path('client/absent=?<str:num_compteur>', client_absent, name='client_absent'),
    path('detail/releve=?<int:pk>', ReleveMod.as_view(), name='releve_mod'),
    path('supprimer/releve?=?<int:pk>', del_releve, name='del_releve'),
    path('exporte/compteur', export_compteur, name='export_compteur'),
    path('exporte/relever/num_compteur=<str:num_compteur>', export_relever, name='export_relever')
]
