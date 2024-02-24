from rest_framework import serializers

from Compteurs.models import ReleveCompteur


class MissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReleveCompteur
        fields = ['date_releve', 'volume', 'conso', 'num_compteur', 'utilisateur']
