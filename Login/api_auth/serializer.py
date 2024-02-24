from rest_framework import serializers

from Compteurs.models import Compteur
from Login.models import Utilisateur


class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ['num_utilisateur', 'password']
