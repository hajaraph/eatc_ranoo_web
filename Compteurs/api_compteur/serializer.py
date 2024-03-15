from rest_framework import serializers

from Compteurs.models import ReleveCompteur
from Facturation.models import Facture, Paiement


class ReleveCompteurSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReleveCompteur
        fields = ['id_releve', 'date_releve', 'volume', 'conso', 'image_compteur', 'utilisateur', 'num_compteur']


class MissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReleveCompteur
        fields = ['date_releve', 'volume', 'num_compteur', 'utilisateur']


class MissionReceivePost (serializers.Serializer):
    class Meta:
        model = ReleveCompteur
        fields =  [ 
                'num_compteur',
                'volume_dernier_releve',
                'date_releve',
                'utilisateur'
            ]


class FactureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facture
        fields = '__all__'


class PaiementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paiement
        fields = '__all__'
