from rest_framework import serializers

from Compteurs.models import ReleveCompteur
from Facturation.models import Facture, Paiement


class MissionSerializer(serializers.ModelSerializer):
    image_compteur = serializers.ImageField(required=False)
    releve_id = serializers.IntegerField(required=False)

    class Meta:
        model = ReleveCompteur
        fields = ['releve_id', 'date_releve', 'volume', 'num_compteur', 'image_compteur']


class FactureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facture
        fields = ['relevecompteur_id']


class PaiementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paiement
        fields = ['montant_payer']
