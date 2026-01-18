"""
Serializers pour la synchronisation des modèles Compteurs.

Ces serializers incluent les champs de synchronisation (sync_id, version, etc.)
et sont utilisés par les endpoints de sync incrémentielle.
"""
from rest_framework import serializers
from Compteurs.models import Compteur, ReleveCompteur, CompteurPrincipale


class SyncMetaMixin(serializers.Serializer):
    """
    Mixin pour ajouter les champs de synchronisation aux serializers.
    """
    sync_id = serializers.UUIDField(read_only=True)
    version = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_deleted = serializers.BooleanField(read_only=True)
    deleted_at = serializers.DateTimeField(read_only=True, allow_null=True)


class CompteurSyncSerializer(serializers.ModelSerializer):
    """
    Serializer pour la synchronisation des Compteurs.
    Inclut toutes les informations nécessaires pour la sync mobile.
    """
    sync_id = serializers.UUIDField(read_only=True)
    version = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_deleted = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Compteur
        fields = [
            # Identifiants
            'num_compteur',
            'sync_id',
            
            # Données métier
            'marque_compteur',
            'modele_compteur',
            'DN_compteur',
            'origin_compteur',
            'num_compteur_principale',
            
            # Métadonnées de sync
            'version',
            'created_at',
            'updated_at',
            'is_deleted',
        ]


class ReleveCompteurSyncSerializer(serializers.ModelSerializer):
    """
    Serializer pour la synchronisation des Relevés de Compteurs.
    Inclut toutes les informations nécessaires pour la sync mobile.
    """
    sync_id = serializers.UUIDField(read_only=True)
    version = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_deleted = serializers.BooleanField(read_only=True)
    
    # Champs relationnels
    num_compteur_id = serializers.CharField(source='num_compteur.num_compteur', read_only=True)
    utilisateur_id = serializers.IntegerField(source='utilisateur.id_utilisateur', read_only=True, allow_null=True)
    
    class Meta:
        model = ReleveCompteur
        fields = [
            # Identifiants
            'id_releve',
            'sync_id',
            
            # Données métier
            'date_releve',
            'volume',
            'conso',
            'image_compteur',
            'num_compteur_id',
            'utilisateur_id',
            
            # Métadonnées de sync
            'version',
            'created_at',
            'updated_at',
            'is_deleted',
        ]


class ReleveCompteurCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création de Relevés depuis le mobile.
    Accepte un client_sync_id pour le mapping local.
    """
    client_sync_id = serializers.UUIDField(write_only=True, required=False, 
                                            help_text="UUID local du mobile pour le mapping")
    
    class Meta:
        model = ReleveCompteur
        fields = [
            'client_sync_id',
            'date_releve',
            'volume',
            'conso',
            'image_compteur',
            'num_compteur',
        ]
    
    def create(self, validated_data):
        # Retirer le client_sync_id qui n'est pas un champ du modèle
        validated_data.pop('client_sync_id', None)
        return super().create(validated_data)


class SyncStatusSerializer(serializers.Serializer):
    """
    Serializer pour le statut de synchronisation.
    Retourne les compteurs de modifications par entité.
    """
    server_time = serializers.DateTimeField()
    changes = serializers.DictField()


class BatchOperationSerializer(serializers.Serializer):
    """
    Serializer pour une opération de batch.
    """
    type = serializers.ChoiceField(choices=['releve', 'anomalie', 'facture_payment'])
    action = serializers.ChoiceField(choices=['create', 'update', 'delete'])
    client_id = serializers.CharField(help_text="ID local du mobile pour le mapping")
    data = serializers.DictField(required=False)
    idempotency_key = serializers.CharField(required=False)


class BatchRequestSerializer(serializers.Serializer):
    """
    Serializer pour une requête de batch.
    """
    operations = BatchOperationSerializer(many=True)
