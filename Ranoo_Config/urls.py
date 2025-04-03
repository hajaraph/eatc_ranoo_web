from django.urls import path

from Ranoo_Config.views import config_utilisateur, NouvelUtilisateur, sup_utilisateur, UtilisateurMod, \
    config_tarif, TarifMod, TarifNew, branchement, BranchementConfig, get_branchement_list, BranchementMod, \
    branchement_supp

urlpatterns = [
    path('utilisateur', config_utilisateur, name='config_utilisateur'),
    path('nouvelle/utilisateur', NouvelUtilisateur.as_view(), name='nouvel_utilisateur'),
    path('modifier/utilisateur=?<int:pk>', UtilisateurMod.as_view(), name='utilisateur_modifier'),
    path('supprimer/utilisateur=?<int:pk>', sup_utilisateur, name='sup_utilisateur'),
    path('tarif', config_tarif, name='config_tarif'),
    path('tarif/nouveau', TarifNew.as_view(), name='tarif_nouveau'),
    path('tarif/modifier?=?<int:pk>', TarifMod.as_view(), name='tarif_mod'),
    path('branchement', branchement, name='branchement'),
    path('branchement/nouveau', BranchementConfig.as_view(), name='branchement_nouveau'),
    path('branchement/modifier/<int:pk>', BranchementMod.as_view(), name='branchement_mod'),
    path('branchement/supprimer/<int:pk>', branchement_supp, name='branchement_supp'),
    path('branchement/liste', get_branchement_list)
]
