from rest_framework import serializers

from Tenants.models import Utilisateur


class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ['num_utilisateur', 'password']


class UtilisateurSerializerWithLastToken(serializers.ModelSerializer):
    last_token = serializers.SerializerMethodField()

    @staticmethod
    def get_last_token(utilisateur):
        return utilisateur.last_token if utilisateur.last_token else "Pas de token"

    class Meta:
        model = Utilisateur
        fields = [
            'id_utilisateur',
            'nom_utilisateur',
            'prenom_utilisateur',
            'num_utilisateur',
            'password',
            'cp_commune',
            'role_id',
            'last_token'
        ]

class UstilisateursSynchrone(serializers.ModelSerializer):

    class Meta:
        model = Utilisateur
        fields = [
            'nom_utilisateur',
            'prenom_utilisateur',
            'num_utilisateur',
            'password',
            'cp_commune',
            'role_id',
            'last_token'
        ]
