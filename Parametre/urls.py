from django.urls import path

from Parametre.views import para_utilisateur, historique, ProfileModifier, ChangerMotdePasse

urlpatterns = [
    path('utilisateur', para_utilisateur, name='para_utilisateur'),
    path('historique', historique, name='historique'),
    path('modifier/profile', ProfileModifier.as_view(), name='profile_modifier'),
    path('changer', ChangerMotdePasse.as_view(), name='changer_motde_passe')
]
