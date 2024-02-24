from django.urls import path

from Ranoo_Config.views import config_utilisateur, NouvelUtilisateur, sup_utilisateur, UtilisateurMod, config_facture, \
    config_tarif, region, CommuneNew, supp_commune, TarifMod, TarifNew

urlpatterns = [
    path('utilisateur', config_utilisateur, name='config_utilisateur'),
    path('nouvelle/utilisateur', NouvelUtilisateur.as_view(), name='nouvel_utilisateur'),
    path('modifier/utilisateur=?<int:pk>', UtilisateurMod.as_view(), name='utilisateur_modifier'),
    path('supprimer/utilisateur=?<int:pk>', sup_utilisateur, name='sup_utilisateur'),
    path('configuration/facture', config_facture, name='config_facture'),
    path('tarif', config_tarif, name='config_tarif'),
    path('tarif/nouveau', TarifNew.as_view(), name='tarif_nouveau'),
    path('region', region, name='region'),
    path('region/nouveau/commune', CommuneNew.as_view(), name='commune_new'),
    path('region/supprimer/commune?=?<str:pk>', supp_commune, name='supp_commune'),
    path('tarif/modifier?=?<int:pk>', TarifMod.as_view(), name='tarif_mod')
]
