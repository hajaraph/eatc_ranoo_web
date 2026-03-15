from django.urls import path

from Compteurs.views import (
    compteur_liste, CompteurNew, CompteurDetail, compteur_releve, ReleveNew,
    ReleveMod, del_releve, compteur_supp, export_relever, export_recouvrement, export_fiche_releve,
    # Compteur Principal
    compteur_principale_liste, CompteurPrincipaleNew, CompteurPrincipaleDetail,
    compteur_principale_supp, ReleveCompteurPrincipaleNew, releve_cp_supp, comparaison_consommation,
    # Alertes
    alerte_marquer_lu, alerte_marquer_toutes_lues, alerte_traiter, alertes_liste, alerte_supprimer,
    # Missions en attente de validation
    missions_en_attente, confirmer_mission, rejeter_mission, compter_missions_en_attente
)

urlpatterns = [
    # Compteurs
    path('liste', compteur_liste, name='compteur_list'),
    path('nouveau', CompteurNew.as_view(), name='compteur_new'),
    path('detail=<str:pk>', CompteurDetail.as_view(), name='compteur_detail'),
    path('supprimer/num_compteur=<str:pk>', compteur_supp, name='compteur_supp'),
    path('releve', compteur_releve, name='compteur_releve'),
    path('nouveau/num_compteur=<str:num_compteur>', ReleveNew.as_view(), name='releve_new'),
    path('detail/id_releve=<int:pk>', ReleveMod.as_view(), name='releve_mod'),
    path('supprimer/id_releve=<int:pk>', del_releve, name='del_releve'),
    path('exporte/compteur', export_fiche_releve, name='export_fiche_releve'),
    path('exporte/recouvrement', export_recouvrement, name='export_recouvrement'),
    path('exporte/relever/num_compteur=<str:num_compteur>', export_relever, name='export_relever'),

    # Compteurs Principaux
    path('principal/liste', compteur_principale_liste, name='compteur_principale_list'),
    path('principal/nouveau', CompteurPrincipaleNew.as_view(), name='compteur_principale_new'),
    path('principal/detail=<str:pk>', CompteurPrincipaleDetail.as_view(), name='compteur_principale_detail'),
    path('principal/supprimer/<str:pk>', compteur_principale_supp, name='compteur_principale_supp'),

    # Relevés Compteurs Principaux
    path('principal/releve/nouveau/<str:num_compteur>', ReleveCompteurPrincipaleNew.as_view(), name='releve_cp_new'),
    path('principal/releve/supprimer/<int:pk>', releve_cp_supp, name='releve_cp_supp'),

    # Comparaison
    path('principal/comparaison/<str:pk>', comparaison_consommation, name='comparaison_consommation'),

    # Alertes de Consommation
    path('alertes/', alertes_liste, name='alertes_liste'),
    path('alertes/marquer-lu/<int:pk>', alerte_marquer_lu, name='alerte_marquer_lu'),
    path('alertes/marquer-toutes-lues', alerte_marquer_toutes_lues, name='alerte_marquer_toutes_lues'),
    path('alertes/traiter/<int:pk>', alerte_traiter, name='alerte_traiter'),
    path('alertes/supprimer/<int:pk>', alerte_supprimer, name='alerte_supprimer'),

    # Missions en attente de validation
    path('missions/', missions_en_attente, name='missions_en_attente'),
    path('missions/confirmer/<int:pk>', confirmer_mission, name='confirmer_mission'),
    path('missions/rejeter/<int:pk>', rejeter_mission, name='rejeter_mission'),
    path('missions/count', compter_missions_en_attente, name='compter_missions_en_attente'),
]

