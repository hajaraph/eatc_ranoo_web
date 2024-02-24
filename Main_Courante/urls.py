from django.urls import path

from Main_Courante.views import main_liste_mc, detail_mc, MainCouranteNew, lance_mc, supprimer_mc, valide_mc, suivie, \
    supp_suivie

urlpatterns = [
    path('liste/mc', main_liste_mc, name='main_liste_mc'),
    path('detail/mc?=?<int:pk>', detail_mc, name='detail_mc'),
    path('nouvelle/mc', MainCouranteNew.as_view(), name='main_courante_new'),
    path('lance?=?<int:pk>', lance_mc, name='lance_mc'),
    path('supprimer/mc?=?<int:pk>', supprimer_mc, name='supprimer_mc'),
    path('valide/mc?=?<int:pk>', valide_mc, name='valide_mc'),
    path('nouvelle/mc', MainCouranteNew.as_view(), name='main_courante_new'),
    path('suivie/mc?<int:pk>?', suivie, name='suivie'),
    path('suivie/supprimer?<int:pk>?', supp_suivie, name='supp_suivie')
]
