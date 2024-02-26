from rest_framework import serializers

from Compteurs.models import ReleveCompteur, Compteur


class MissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReleveCompteur
        fields = ['date_releve', 'volume', 'num_compteur', 'utilisateur']


class FactureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReleveCompteur
        fields = '__all__'
