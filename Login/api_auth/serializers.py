from rest_framework import serializers

from Tenants.models import Utilisateur


class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ['num_utilisateur', 'password']


class UtilisateurSerializerWithLastToken(serializers.ModelSerializer):
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
        ]
