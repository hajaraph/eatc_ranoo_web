from rest_framework import serializers

from Compteurs.models import ReleveCompteur
from Facturation.models import Facture, Paiement


class ReleveCompteurSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReleveCompteur
        fields = ['id_releve', 'date_releve', 'volume', 'conso', 'image_compteur', 'utilisateur', 'num_compteur']


class MissionSerializer(serializers.ModelSerializer):
    image_compteur = serializers.ImageField(required=False)  # Champ pour le fichier image_compteur

    class Meta:
        model = ReleveCompteur
        fields = ['date_releve', 'volume', 'num_compteur', 'utilisateur', 'image_compteur']


class MissionReceivePost(serializers.Serializer):
    class Meta:
        model = ReleveCompteur
        fields = [
            'num_compteur',
            'volume_dernier_releve',
            'date_releve',
            'utilisateur'
        ]


class FactureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facture
        fields = ['relevecompteur_id']


class PaiementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paiement
        fields = ['montant_payer']
