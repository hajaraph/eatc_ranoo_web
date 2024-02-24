from rest_framework import serializers

from Compteurs.models import ReleveCompteur, Compteur


class CompteurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Compteur
        fields = ['num_compteur']


class MissionSerializer(serializers.ModelSerializer):
    num_compteur = CompteurSerializer(read_only=True)

    class Meta:
        model = ReleveCompteur
        fields = ['date_releve', 'volume', 'num_compteur', 'utilisateur']
