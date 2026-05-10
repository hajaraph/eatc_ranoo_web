from rest_framework import serializers
from Facturation.models import Facture, Paiement, Tarif, Taxe
from Clients.models import Contrat, Client
from Compteurs.models import ReleveCompteur, Compteur


class PaiementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paiement
        fields = ['id_paiement', 'montant_payer', 'date_paiement', 'facture']
        read_only_fields = ['id_paiement']


class FactureListSerializer(serializers.ModelSerializer):
    """Serializer allege pour la liste des factures."""
    client_nom = serializers.SerializerMethodField()
    client_num = serializers.SerializerMethodField()
    commune_nom = serializers.SerializerMethodField()
    compteur_num = serializers.SerializerMethodField()
    montant_paye = serializers.SerializerMethodField()
    restant_du = serializers.SerializerMethodField()

    class Meta:
        model = Facture
        fields = [
            'id_facture', 'num_facture', 'date_facture', 'date_echeance',
            'montant_total_ttc', 'statut', 'num_contrat',
            'client_nom', 'client_num', 'commune_nom', 'compteur_num',
            'montant_paye', 'restant_du'
        ]
        read_only_fields = ['id_facture']

    def get_client_nom(self, obj):
        contrat = obj.num_contrat
        if contrat and contrat.client:
            client = contrat.client
            return f"{client.nom_client} {client.prenom_client}"
        return None

    def get_client_num(self, obj):
        contrat = obj.num_contrat
        if contrat and contrat.client:
            return contrat.client.num_client
        return None

    def get_commune_nom(self, obj):
        contrat = obj.num_contrat
        if contrat and contrat.cp_commune:
            return contrat.cp_commune.nom_commune
        return None

    def get_compteur_num(self, obj):
        contrat = obj.num_contrat
        if contrat and contrat.num_compteur:
            return contrat.num_compteur.numero_compteur
        return None

    def get_montant_paye(self, obj):
        total = obj.paiements.aggregate(total=models.Sum('montant_payer'))['total']
        return total or 0

    def get_restant_du(self, obj):
        total_paye = self.get_montant_paye(obj)
        return (obj.montant_total_ttc or 0) - total_paye


class FactureDetailSerializer(serializers.ModelSerializer):
    """Serializer complet pour le detail d'une facture."""
    client_nom = serializers.SerializerMethodField()
    client_num = serializers.SerializerMethodField()
    client_adresse = serializers.SerializerMethodField()
    commune_nom = serializers.SerializerMethodField()
    compteur_num = serializers.SerializerMethodField()
    contrat_info = serializers.SerializerMethodField()
    paiements = PaiementSerializer(many=True, read_only=True)
    montant_paye = serializers.SerializerMethodField()
    restant_du = serializers.SerializerMethodField()

    class Meta:
        model = Facture
        fields = [
            'id_facture', 'num_facture', 'date_facture_precedant',
            'date_facture', 'montant_total_ttc', 'avoir_avant',
            'avoir_utilise', 'avoir_nouveau', 'restant_precedant',
            'restant_nouvel', 'statut', 'taxes_appliquees',
            'date_echeance', 'tva_appliquer', 'num_contrat',
            'relevecompteur', 'client_nom', 'client_num',
            'client_adresse', 'commune_nom', 'compteur_num',
            'contrat_info', 'paiements', 'montant_paye', 'restant_du'
        ]
        read_only_fields = ['id_facture']

    def get_client_nom(self, obj):
        contrat = obj.num_contrat
        if contrat and contrat.client:
            client = contrat.client
            return f"{client.nom_client} {client.prenom_client}"
        return None

    def get_client_num(self, obj):
        contrat = obj.num_contrat
        if contrat and contrat.client:
            return contrat.client.num_client
        return None

    def get_client_adresse(self, obj):
        contrat = obj.num_contrat
        if contrat and contrat.client:
            return contrat.client.adresse_client
        return None

    def get_commune_nom(self, obj):
        contrat = obj.num_contrat
        if contrat and contrat.cp_commune:
            return contrat.cp_commune.nom_commune
        return None

    def get_compteur_num(self, obj):
        contrat = obj.num_contrat
        if contrat and contrat.num_compteur:
            return contrat.num_compteur.numero_compteur
        return None

    def get_contrat_info(self, obj):
        contrat = obj.num_contrat
        if contrat:
            return {
                'num_contrat': contrat.num_contrat,
                'date_debut': contrat.date_debut,
                'date_fin': contrat.date_fin,
                'adresse_contrat': contrat.adresse_contrat,
            }
        return None

    def get_montant_paye(self, obj):
        total = obj.paiements.aggregate(total=models.Sum('montant_payer'))['total']
        return total or 0

    def get_restant_du(self, obj):
        total_paye = self.get_montant_paye(obj)
        return (obj.montant_total_ttc or 0) - total_paye


class PaiementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paiement
        fields = ['montant_payer', 'date_paiement', 'facture']
