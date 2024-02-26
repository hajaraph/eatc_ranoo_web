from rest_framework import serializers

from Compteurs.models import ReleveCompteur
from Facturation.models import Facture


class MissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReleveCompteur
        fields = ['date_releve', 'volume', 'num_compteur', 'utilisateur']


class FactureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facture
        fields = '__all__'
