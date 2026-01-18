"""
Utilitaires pour les réponses API standardisées.

Ce module fournit des classes et fonctions pour créer des réponses API
cohérentes et standardisées à travers toute l'application.
"""
from functools import wraps
from django.utils import timezone
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework import status


class ApiResponse:
    """
    Classe utilitaire pour générer des réponses API standardisées.
    
    Toutes les réponses suivent le format:
    {
        "success": bool,
        "timestamp": "ISO datetime",
        "data": {...} ou null,
        "message": "string" ou null,
        "error": {...} ou null,
        "meta": {...} ou null
    }
    """
    
    @staticmethod
    def success(data=None, message=None, meta=None, http_status=status.HTTP_200_OK):
        """
        Génère une réponse de succès standardisée.
        
        Args:
            data: Données à retourner (dict, list, ou autre)
            message: Message optionnel pour l'utilisateur
            meta: Métadonnées optionnelles (pagination, etc.)
            http_status: Code HTTP (défaut: 200)
            
        Returns:
            Response: Réponse DRF standardisée
        """
        response = {
            'success': True,
            'timestamp': timezone.now().isoformat(),
        }
        if data is not None:
            response['data'] = data
        if message:
            response['message'] = message
        if meta:
            response['meta'] = meta
        return Response(response, status=http_status)
    
    @staticmethod
    def created(data=None, message="Créé avec succès"):
        """
        Génère une réponse pour une création réussie (HTTP 201).
        
        Args:
            data: Données de l'objet créé
            message: Message de confirmation
            
        Returns:
            Response: Réponse DRF avec status 201
        """
        response = {
            'success': True,
            'message': message,
            'timestamp': timezone.now().isoformat(),
        }
        if data is not None:
            response['data'] = data
        return Response(response, status=status.HTTP_201_CREATED)
    
    @staticmethod
    def error(message, code=None, details=None, http_status=status.HTTP_400_BAD_REQUEST):
        """
        Génère une réponse d'erreur standardisée.
        
        Args:
            message: Message d'erreur principal
            code: Code d'erreur technique (ex: 'VALIDATION_ERROR')
            details: Détails supplémentaires (ex: erreurs de validation)
            http_status: Code HTTP (défaut: 400)
            
        Returns:
            Response: Réponse DRF d'erreur standardisée
        """
        response = {
            'success': False,
            'timestamp': timezone.now().isoformat(),
            'error': {
                'message': message,
            }
        }
        if code:
            response['error']['code'] = code
        if details:
            response['error']['details'] = details
        return Response(response, status=http_status)
    
    @staticmethod
    def not_found(message="Ressource non trouvée", code="NOT_FOUND"):
        """
        Génère une réponse 404 standardisée.
        
        Args:
            message: Message d'erreur
            code: Code d'erreur technique
            
        Returns:
            Response: Réponse DRF 404
        """
        return ApiResponse.error(
            message=message,
            code=code,
            http_status=status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def conflict(message="Conflit détecté", code="CONFLICT", details=None):
        """
        Génère une réponse 409 (conflit) standardisée.
        Utilisée pour les conflits de version lors de la synchronisation.
        
        Args:
            message: Message d'erreur
            code: Code d'erreur technique
            details: Détails du conflit (versions, données)
            
        Returns:
            Response: Réponse DRF 409
        """
        return ApiResponse.error(
            message=message,
            code=code,
            details=details,
            http_status=status.HTTP_409_CONFLICT
        )
    
    @staticmethod
    def server_error(message="Erreur interne du serveur", code="INTERNAL_ERROR"):
        """
        Génère une réponse 500 standardisée.
        
        Args:
            message: Message d'erreur
            code: Code d'erreur technique
            
        Returns:
            Response: Réponse DRF 500
        """
        return ApiResponse.error(
            message=message,
            code=code,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    @staticmethod
    def sync_response(data, server_time=None, has_more=False, next_cursor=None):
        """
        Génère une réponse spécialisée pour les opérations de synchronisation.
        
        Args:
            data: Données synchronisées
            server_time: Heure du serveur (pour la prochaine sync incrémentielle)
            has_more: Indique s'il y a plus de données à récupérer
            next_cursor: Curseur pour la pagination
            
        Returns:
            Response: Réponse DRF avec métadonnées de sync
        """
        response = {
            'success': True,
            'data': data,
            'sync': {
                'server_time': server_time or timezone.now().isoformat(),
                'has_more': has_more,
            }
        }
        if next_cursor:
            response['sync']['next_cursor'] = next_cursor
        return Response(response, status=status.HTTP_200_OK)
    
    @staticmethod
    def batch_response(results, success_count=None, failure_count=None):
        """
        Génère une réponse pour les opérations par lot (batch).
        
        Args:
            results: Liste des résultats individuels
            success_count: Nombre de succès (calculé si non fourni)
            failure_count: Nombre d'échecs (calculé si non fourni)
            
        Returns:
            Response: Réponse DRF avec statistiques de batch
        """
        if success_count is None:
            success_count = sum(1 for r in results if r.get('success', False))
        if failure_count is None:
            failure_count = len(results) - success_count
        
        return ApiResponse.success(
            data={'results': results},
            meta={
                'total': len(results),
                'success_count': success_count,
                'failure_count': failure_count,
            }
        )


def ensure_idempotent(ttl=3600, key_param='idempotency_key'):
    """
    Décorateur pour garantir l'idempotence des requêtes POST/PUT/DELETE.
    
    Utilise un cache pour stocker les réponses précédentes et retourner
    la même réponse si la même requête est répétée.
    
    Args:
        ttl: Durée de vie du cache en secondes (défaut: 1 heure)
        key_param: Nom du paramètre contenant la clé d'idempotence
        
    Usage:
        @api_view(['POST'])
        @ensure_idempotent(ttl=3600)
        def create_releve(request):
            # Le header X-Idempotency-Key ou le body param 'idempotency_key'
            # sera utilisé pour garantir l'idempotence
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Récupérer la clé d'idempotence depuis le header ou le body
            idempotency_key = (
                request.headers.get('X-Idempotency-Key') or
                request.data.get(key_param)
            )
            
            # Si pas de clé, exécuter normalement
            if not idempotency_key:
                return func(request, *args, **kwargs)
            
            cache_key = f"idempotent:{idempotency_key}"
            cached_response = cache.get(cache_key)
            
            # Si réponse en cache, la retourner
            if cached_response is not None:
                return Response(
                    cached_response['data'],
                    status=cached_response['status']
                )
            
            # Exécuter la fonction
            response = func(request, *args, **kwargs)
            
            # Mettre en cache si ce n'est pas une erreur serveur
            if response.status_code < 500:
                cache.set(cache_key, {
                    'data': response.data,
                    'status': response.status_code
                }, ttl)
            
            return response
        return wrapper
    return decorator
