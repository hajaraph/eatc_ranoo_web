from rest_framework import serializers
from Clients.models import Client, TypeClient, PieceClient, Contrat
from Acommune.models import Commune
from Compteurs.models import Compteur
from Tenants.models import Utilisateur


class TypeClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeClient
        fields = ['id_type_client', 'designation_client']
        read_only_fields = ['id_type_client']


class ClientSerializer(serializers.ModelSerializer):
    type_client_designation = serializers.CharField(source='type_client.designation_client', read_only=True)
    commune_nom = serializers.CharField(source='cp_commune.nom_commune', read_only=True)
    contrats = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            'id_client', 'num_client', 'nom_client', 'prenom_client',
            'tel1_client', 'tel2_client', 'email_client', 'adresse_client',
            'pays_client', 'profession_client', 'nb_personne_menage',
            'compte_actif', 'cp_commune', 'type_client',
            'type_client_designation', 'commune_nom', 'contrats'
        ]
        read_only_fields = ['id_client']

    def get_contrats(self, obj):
        contrats = obj.contrats.all()
        result = [
            {
                'num_contrat': c.num_contrat,
                'num_compteur': c.num_compteur.num_compteur if c.num_compteur else None,
            }
            for c in contrats
        ]
        print(f'[ClientSerializer] Contrats for {obj.nom_client}: {result}')
        return result


class ClientCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            'num_client', 'nom_client', 'prenom_client',
            'tel1_client', 'tel2_client', 'email_client', 'adresse_client',
            'pays_client', 'profession_client', 'nb_personne_menage',
            'compte_actif', 'cp_commune', 'type_client'
        ]


class PieceClientSerializer(serializers.ModelSerializer):
    client_nom = serializers.CharField(source='client.nom_client', read_only=True)
    
    class Meta:
        model = PieceClient
        fields = ['id_piece', 'pieces_client', 'designation', 'client', 'client_nom']
        read_only_fields = ['id_piece']


class ContratSerializer(serializers.ModelSerializer):
    client_nom = serializers.CharField(source='client.nom_client', read_only=True)
    compteur_marque = serializers.CharField(source='num_compteur.marque', read_only=True)
    commune_nom = serializers.CharField(source='cp_commune.nom_commune', read_only=True)
    
    class Meta:
        model = Contrat
        fields = [
            'num_contrat', 'date_debut', 'date_fin', 'adresse_contrat',
            'pays_contrat', 'cp_commune', 'client', 'num_compteur',
            'utilisateur', 'client_nom', 'compteur_marque', 'commune_nom'
        ]
        read_only_fields = ['num_contrat']


class ContratCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contrat
        fields = [
            'date_debut', 'date_fin', 'adresse_contrat',
            'pays_contrat', 'cp_commune', 'client', 'num_compteur', 'utilisateur'
        ]
