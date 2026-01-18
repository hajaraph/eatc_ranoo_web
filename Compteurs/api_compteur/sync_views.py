"""
Vues API pour la synchronisation incrémentielle.

Ces endpoints permettent au mobile de:
- Récupérer uniquement les modifications depuis la dernière sync (delta sync)
- Envoyer des opérations par lot (batch)
- Vérifier le statut de synchronisation
"""
import logging
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db import transaction, models
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from Tenants.middleware import schema_use_api
from Compteurs.models import Compteur, ReleveCompteur
from Compteurs.api_compteur.sync_serializers import (
    CompteurSyncSerializer,
    ReleveCompteurSyncSerializer,
    ReleveCompteurCreateSerializer,
    BatchRequestSerializer,
)
from Rel_Compteur.api_utils import ApiResponse, ensure_idempotent

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@schema_use_api
def sync_status(request):
    """
    Endpoint pour vérifier le statut de synchronisation.
    
    Retourne les compteurs de modifications par entité depuis la dernière sync.
    
    Query params:
        - last_sync: ISO datetime - Date de la dernière synchronisation
    
    Response:
        {
            "success": true,
            "data": {
                "server_time": "2024-01-18T10:00:00Z",
                "changes": {
                    "compteurs": {"total": 100, "modified": 5, "deleted": 1},
                    "releves": {"total": 500, "modified": 20, "deleted": 0}
                }
            }
        }
    """
    try:
        cp_commune_id = request.user.cp_commune_id
        last_sync_str = request.GET.get('last_sync')
        last_sync = None
        
        if last_sync_str:
            last_sync = parse_datetime(last_sync_str)
            if not last_sync:
                return ApiResponse.error(
                    "Format de date invalide pour 'last_sync'. Utilisez ISO 8601.",
                    code="INVALID_DATE"
                )
        
        # Compteurs liés à la commune de l'utilisateur
        compteurs_base = Compteur.all_objects.filter(
            contrats__cp_commune_id=cp_commune_id
        ).distinct()
        
        releves_base = ReleveCompteur.all_objects.filter(
            num_compteur__contrats__cp_commune_id=cp_commune_id
        ).distinct()
        
        changes = {}
        
        if last_sync:
            # Mode incrémental: compter les modifications depuis last_sync
            compteurs_modified = compteurs_base.filter(
                updated_at__gte=last_sync, is_deleted=False
            )
            compteurs_deleted = compteurs_base.filter(
                updated_at__gte=last_sync, is_deleted=True
            )
            
            releves_modified = releves_base.filter(
                updated_at__gte=last_sync, is_deleted=False
            )
            releves_deleted = releves_base.filter(
                updated_at__gte=last_sync, is_deleted=True
            )
            
            changes = {
                'compteurs': {
                    'total': compteurs_base.filter(is_deleted=False).count(),
                    'modified': compteurs_modified.count(),
                    'deleted': compteurs_deleted.count(),
                    'needs_sync': compteurs_modified.exists() or compteurs_deleted.exists(),
                },
                'releves': {
                    'total': releves_base.filter(is_deleted=False).count(),
                    'modified': releves_modified.count(),
                    'deleted': releves_deleted.count(),
                    'needs_sync': releves_modified.exists() or releves_deleted.exists(),
                }
            }
        else:
            # Mode full sync: tout doit être synchronisé
            changes = {
                'compteurs': {
                    'total': compteurs_base.filter(is_deleted=False).count(),
                    'needs_full_sync': True,
                },
                'releves': {
                    'total': releves_base.filter(is_deleted=False).count(),
                    'needs_full_sync': True,
                }
            }
        
        return ApiResponse.success(data={
            'server_time': timezone.now().isoformat(),
            'changes': changes,
        })
        
    except Exception as e:
        logger.error(f"Erreur dans sync_status: {str(e)}", exc_info=True)
        return ApiResponse.server_error(str(e))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@schema_use_api
def sync_compteurs(request):
    """
    Endpoint de synchronisation incrémentielle des compteurs.
    
    Query params:
        - modified_since: ISO datetime - Retourne uniquement les modifications après cette date
        - include_deleted: bool - Inclure les éléments supprimés (défaut: true pour sync)
        - limit: int - Nombre max d'éléments (défaut: 100, max: 500)
        - cursor: str - Curseur pour la pagination
    
    Response:
        {
            "success": true,
            "data": [...],
            "sync": {
                "server_time": "2024-01-18T10:00:00Z",
                "has_more": false,
                "next_cursor": null
            }
        }
    """
    try:
        cp_commune_id = request.user.cp_commune_id
        
        # Paramètres de requête
        modified_since_str = request.GET.get('modified_since')
        include_deleted = request.GET.get('include_deleted', 'true').lower() == 'true'
        limit = min(int(request.GET.get('limit', 100)), 500)
        cursor = request.GET.get('cursor')
        
        # Construire le queryset de base
        if include_deleted:
            queryset = Compteur.all_objects.filter(
                contrats__cp_commune_id=cp_commune_id
            ).distinct()
        else:
            queryset = Compteur.objects.filter(
                contrats__cp_commune_id=cp_commune_id
            ).distinct()
        
        # Filtrer par date de modification (delta sync)
        if modified_since_str:
            modified_since = parse_datetime(modified_since_str)
            if modified_since:
                queryset = queryset.filter(updated_at__gte=modified_since)
            else:
                return ApiResponse.error(
                    "Format de date invalide pour 'modified_since'",
                    code="INVALID_DATE"
                )
        
        # Pagination par curseur
        if cursor:
            try:
                cursor_time, cursor_id = cursor.split('|')
                cursor_dt = parse_datetime(cursor_time)
                if cursor_dt:
                    queryset = queryset.filter(
                        models.Q(updated_at__gt=cursor_dt) |
                        models.Q(updated_at=cursor_dt, sync_id__gt=cursor_id)
                    )
            except ValueError:
                pass
        
        # Ordonner et limiter
        queryset = queryset.order_by('updated_at', 'sync_id')[:limit + 1]
        results = list(queryset)
        
        # Vérifier s'il y a plus de résultats
        has_more = len(results) > limit
        if has_more:
            results = results[:limit]
        
        # Préparer le curseur suivant
        next_cursor = None
        if has_more and results:
            last_item = results[-1]
            next_cursor = f"{last_item.updated_at.isoformat()}|{last_item.sync_id}"
        
        # Sérialiser
        serializer = CompteurSyncSerializer(results, many=True)
        
        return ApiResponse.sync_response(
            data=serializer.data,
            server_time=timezone.now().isoformat(),
            has_more=has_more,
            next_cursor=next_cursor
        )
        
    except Exception as e:
        logger.error(f"Erreur dans sync_compteurs: {str(e)}", exc_info=True)
        return ApiResponse.server_error(str(e))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@schema_use_api
def sync_releves(request):
    """
    Endpoint de synchronisation incrémentielle des relevés de compteurs.
    
    Query params:
        - modified_since: ISO datetime
        - include_deleted: bool
        - limit: int
        - cursor: str
    """
    try:
        cp_commune_id = request.user.cp_commune_id
        
        # Paramètres
        modified_since_str = request.GET.get('modified_since')
        include_deleted = request.GET.get('include_deleted', 'true').lower() == 'true'
        limit = min(int(request.GET.get('limit', 100)), 500)
        cursor = request.GET.get('cursor')
        
        # Queryset de base
        if include_deleted:
            queryset = ReleveCompteur.all_objects.filter(
                num_compteur__contrats__cp_commune_id=cp_commune_id
            ).distinct()
        else:
            queryset = ReleveCompteur.objects.filter(
                num_compteur__contrats__cp_commune_id=cp_commune_id
            ).distinct()
        
        # Filtrer par date
        if modified_since_str:
            modified_since = parse_datetime(modified_since_str)
            if modified_since:
                queryset = queryset.filter(updated_at__gte=modified_since)
        
        # Pagination par curseur
        if cursor:
            try:
                cursor_time, cursor_id = cursor.split('|')
                cursor_dt = parse_datetime(cursor_time)
                if cursor_dt:
                    queryset = queryset.filter(
                        models.Q(updated_at__gt=cursor_dt) |
                        models.Q(updated_at=cursor_dt, sync_id__gt=cursor_id)
                    )
            except ValueError:
                pass
        
        # Ordonner et limiter
        queryset = queryset.order_by('updated_at', 'sync_id')[:limit + 1]
        results = list(queryset)
        
        has_more = len(results) > limit
        if has_more:
            results = results[:limit]
        
        next_cursor = None
        if has_more and results:
            last_item = results[-1]
            next_cursor = f"{last_item.updated_at.isoformat()}|{last_item.sync_id}"
        
        serializer = ReleveCompteurSyncSerializer(results, many=True)
        
        return ApiResponse.sync_response(
            data=serializer.data,
            server_time=timezone.now().isoformat(),
            has_more=has_more,
            next_cursor=next_cursor
        )
        
    except Exception as e:
        logger.error(f"Erreur dans sync_releves: {str(e)}", exc_info=True)
        return ApiResponse.server_error(str(e))


class BatchSyncView(APIView):
    """
    Endpoint pour envoyer plusieurs opérations en une seule requête.
    
    Permet de:
    - Créer plusieurs relevés
    - Mettre à jour plusieurs éléments
    - Réduire le nombre de requêtes réseau
    """
    permission_classes = [IsAuthenticated]
    
    @schema_use_api
    def post(self, request):
        """
        Traite un lot d'opérations de synchronisation.
        
        Body:
        {
            "operations": [
                {
                    "type": "releve",
                    "action": "create",
                    "client_id": "uuid-local",
                    "data": { ... }
                }
            ]
        }
        """
        serializer = BatchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return ApiResponse.error(
                "Données invalides",
                code="VALIDATION_ERROR",
                details=serializer.errors
            )
        
        operations = serializer.validated_data['operations']
        
        if len(operations) > 100:
            return ApiResponse.error(
                "Maximum 100 opérations par requête",
                code="TOO_MANY_OPERATIONS"
            )
        
        results = []
        utilisateur = request.user
        
        for op in operations:
            client_id = op.get('client_id')
            op_type = op.get('type')
            action = op.get('action')
            data = op.get('data', {})
            
            try:
                result = self._process_operation(op_type, action, data, utilisateur)
                results.append({
                    'client_id': client_id,
                    'success': True,
                    **result
                })
            except Exception as e:
                logger.error(f"Erreur batch operation {client_id}: {str(e)}")
                results.append({
                    'client_id': client_id,
                    'success': False,
                    'error': str(e),
                    'error_code': getattr(e, 'code', 'UNKNOWN'),
                })
        
        return ApiResponse.batch_response(results)
    
    def _process_operation(self, op_type, action, data, utilisateur):
        """Traite une opération individuelle"""
        if op_type == 'releve' and action == 'create':
            return self._create_releve(data, utilisateur)
        elif op_type == 'releve' and action == 'update':
            return self._update_releve(data)
        else:
            raise ValueError(f"Opération non supportée: {op_type}/{action}")
    
    def _create_releve(self, data, utilisateur):
        """Crée un nouveau relevé"""
        with transaction.atomic():
            serializer = ReleveCompteurCreateSerializer(data=data)
            if not serializer.is_valid():
                raise ValueError(str(serializer.errors))
            
            releve = serializer.save(utilisateur=utilisateur)
            
            return {
                'server_id': releve.id_releve,
                'sync_id': str(releve.sync_id),
                'version': releve.version,
            }
    
    def _update_releve(self, data):
        """Met à jour un relevé existant"""
        sync_id = data.get('sync_id')
        expected_version = data.get('expected_version')
        
        if not sync_id:
            raise ValueError("sync_id requis pour la mise à jour")
        
        with transaction.atomic():
            try:
                releve = ReleveCompteur.all_objects.get(sync_id=sync_id)
            except ReleveCompteur.DoesNotExist:
                raise ValueError(f"Relevé non trouvé: {sync_id}")
            
            # Vérifier la version pour détecter les conflits
            if expected_version and releve.version != expected_version:
                raise ValueError(
                    f"Conflit de version: attendu {expected_version}, actuel {releve.version}"
                )
            
            # Mettre à jour les champs
            for field in ['volume', 'conso', 'date_releve']:
                if field in data:
                    setattr(releve, field, data[field])
            
            releve.save()
            
            return {
                'sync_id': str(releve.sync_id),
                'version': releve.version,
            }


# Alias pour compatibilité avec ensure_idempotent
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ensure_idempotent(ttl=3600)
@schema_use_api
def create_releve_idempotent(request):
    """
    Endpoint idempotent pour créer un relevé.
    
    Utilise le header X-Idempotency-Key ou le champ idempotency_key dans le body
    pour garantir qu'une requête répétée ne crée pas de doublons.
    """
    try:
        utilisateur = request.user
        serializer = ReleveCompteurCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ApiResponse.error(
                "Données invalides",
                code="VALIDATION_ERROR",
                details=serializer.errors
            )
        
        with transaction.atomic():
            releve = serializer.save(utilisateur=utilisateur)
        
        return ApiResponse.created(data={
            'id_releve': releve.id_releve,
            'sync_id': str(releve.sync_id),
            'version': releve.version,
        })
        
    except Exception as e:
        logger.error(f"Erreur create_releve_idempotent: {str(e)}", exc_info=True)
        return ApiResponse.server_error(str(e))
