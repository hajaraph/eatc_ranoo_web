"""
Mixins pour la synchronisation des modèles Django.

Ce module fournit des classes de base pour ajouter des fonctionnalités
de synchronisation aux modèles Django, incluant:
- Traçabilité (created_at, updated_at)
- Versioning pour la détection de conflits
- Soft delete pour la synchronisation des suppressions
- UUID unique pour l'identification cross-platform
"""
import uuid
from django.db import models
from django.utils import timezone


class SyncMixin(models.Model):
    """
    Mixin abstrait pour ajouter les champs de synchronisation à tous les modèles.
    
    Attributs:
        sync_id: UUID unique pour identifier l'entité dans la synchronisation
        created_at: Date/heure de création
        updated_at: Date/heure de dernière modification
        version: Numéro de version pour la détection de conflits
        is_deleted: Marqueur de suppression logique (soft delete)
        deleted_at: Date/heure de suppression
    
    Usage:
        class MonModele(SyncMixin, models.Model):
            nom = models.CharField(max_length=100)
            # ...
    """
    sync_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        verbose_name="ID de synchronisation",
        help_text="Identifiant unique pour la synchronisation"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Date de création"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        verbose_name="Date de modification"
    )
    version = models.PositiveIntegerField(
        default=1,
        verbose_name="Version",
        help_text="Numéro de version pour la détection de conflits"
    )
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Supprimé",
        help_text="Marqueur de suppression logique (soft delete)"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de suppression"
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Surcharge de save() pour incrémenter automatiquement la version
        lors des mises à jour.
        """
        # Si force_insert est True, c'est une création
        is_insert = kwargs.get('force_insert', False)
        
        # Ne pas incrémenter la version lors de la création
        if not is_insert and self.pk is not None:
            # Utiliser le manager de base pour éviter le filtrage de SyncManager
            base_manager = models.Manager()
            base_manager.model = self.__class__
            
            try:
                # Vérifier si l'objet existe déjà en base
                # On utilise une requête directe pour éviter les problèmes de manager
                from django.db import connection
                with connection.cursor() as cursor:
                    table_name = self._meta.db_table
                    pk_column = self._meta.pk.column
                    pk_value = self.pk
                    
                    # Échapper correctement selon le type de pk
                    if isinstance(pk_value, str):
                        cursor.execute(
                            f'SELECT version FROM "{table_name}" WHERE "{pk_column}" = %s',
                            [pk_value]
                        )
                    else:
                        cursor.execute(
                            f'SELECT version FROM "{table_name}" WHERE "{pk_column}" = %s',
                            [pk_value]
                        )
                    
                    row = cursor.fetchone()
                    if row is not None:
                        old_version = row[0]
                        # Incrémenter seulement si ce n'est pas déjà incrémenté manuellement
                        if self.version == old_version:
                            self.version += 1
            except Exception:
                # Si la table n'existe pas encore ou autre erreur, on ignore
                pass
        
        super().save(*args, **kwargs)

    def soft_delete(self):
        """
        Effectue une suppression logique (soft delete).
        L'enregistrement reste en base mais est marqué comme supprimé.
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        """
        Restaure un enregistrement supprimé logiquement.
        """
        self.is_deleted = False
        self.deleted_at = None
        self.save()

    def delete(self, using=None, keep_parents=False):
        """
        Surcharge de la méthode delete standard pour effectuer un soft delete par défaut.
        Cela garantit que les suppressions sont synchronisées vers les clients mobiles.
        """
        self.soft_delete()

    def hard_delete(self, using=None, keep_parents=False):
        """
        Effectue une suppression physique (définitive) de l'enregistrement.
        Attention: Cette opération est irréversible!
        """
        super().delete(using=using, keep_parents=keep_parents)

    def get_sync_data(self):
        """
        Retourne les métadonnées de synchronisation de l'objet.
        Utile pour les réponses API.
        """
        return {
            'sync_id': str(self.sync_id),
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
        }


class SyncManager(models.Manager):
    """
    Manager personnalisé qui exclut automatiquement les éléments supprimés.
    
    Usage:
        class MonModele(SyncMixin, models.Model):
            objects = SyncManager()
            all_objects = models.Manager()  # Pour accéder aux supprimés
    """
    
    def get_queryset(self):
        """Retourne uniquement les éléments non supprimés"""
        return super().get_queryset().filter(is_deleted=False)
    
    def with_deleted(self):
        """Retourne tous les éléments, y compris les supprimés"""
        return super().get_queryset()
    
    def deleted_only(self):
        """Retourne uniquement les éléments supprimés"""
        return super().get_queryset().filter(is_deleted=True)
    
    def modified_since(self, timestamp):
        """
        Retourne les éléments modifiés depuis une date donnée.
        
        Args:
            timestamp: datetime - Date/heure de référence
            
        Returns:
            QuerySet des éléments modifiés après la date donnée
        """
        return self.get_queryset().filter(updated_at__gte=timestamp)
    
    def modified_since_with_deleted(self, timestamp):
        """
        Retourne tous les éléments modifiés depuis une date, y compris les supprimés.
        Utile pour la synchronisation incrémentielle.
        
        Args:
            timestamp: datetime - Date/heure de référence
            
        Returns:
            QuerySet de tous les éléments modifiés (actifs et supprimés)
        """
        return super().get_queryset().filter(updated_at__gte=timestamp)
