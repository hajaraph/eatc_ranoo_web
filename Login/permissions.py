"""
Permissions personnalisées pour les API REST.

Ce module définit des classes de permissions basées sur les rôles utilisateurs
pour sécuriser les endpoints de l'API mobile Ranoo.

Usage:
    from Login.permissions import IsReleveur, IsAdministrateur, IsAdminOuGestionnaire
    
    @api_view(['GET'])
    @permission_classes([IsReleveur])
    def ma_vue_releveur(request):
        ...
"""

from rest_framework import permissions


class IsReleveur(permissions.BasePermission):
    """
    Permission réservée aux utilisateurs avec rôle 'Releveur'.
    
    Utilisé pour les endpoints spécifiques aux releveurs :
    - Missions de relevé
    - Déclaration d'anomalies
    - Sync offline-first
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role') or not request.user.role:
            return False
        
        return request.user.role.role == 'Releveur'
    
    def has_object_permission(self, request, view, obj):
        # Les releveurs ne peuvent accéder qu'à leurs propres données
        if hasattr(obj, 'utilisateur') and obj.utilisateur:
            return obj.utilisateur == request.user
        
        # Pour les objets liés à une commune, vérifier la correspondance
        if hasattr(obj, 'cp_commune_id') and request.user.cp_commune_id:
            return obj.cp_commune_id == request.user.cp_commune_id
        
        return True


class IsGestionnaire(permissions.BasePermission):
    """
    Permission réservée aux utilisateurs avec rôle 'Gestionnaire'.
    
    Utilisé pour les endpoints de gestion limités à une commune :
    - Validation des relevés
    - Gestion clients (limité à sa commune)
    - Dashboard commune
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role') or not request.user.role:
            return False
        
        return request.user.role.role == 'Gestionnaire'
    
    def has_object_permission(self, request, view, obj):
        # Les gestionnaires sont limités à leur commune
        if hasattr(obj, 'cp_commune_id') and request.user.cp_commune_id:
            return obj.cp_commune_id == request.user.cp_commune_id
        
        return True


class IsAdministrateur(permissions.BasePermission):
    """
    Permission réservée aux utilisateurs avec rôle 'Administrateur'.
    
    Utilisé pour les endpoints d'administration globale :
    - CRUD utilisateurs
    - Configuration tarifs
    - Dashboard global
    - Suppressions critiques
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role') or not request.user.role:
            return False
        
        return request.user.role.role == 'Administrateur'


class IsAdminOuGestionnaire(permissions.BasePermission):
    """
    Permission combinée pour Administrateur ET Gestionnaire.
    
    Utilisé pour les endpoints accessibles aux deux rôles :
    - Dashboard (global pour Admin, limité pour Gest)
    - Gestion clients/compteurs
    - Validation relevés
    - Consultation factures
    
    Note: La logique de filtrage par commune doit être appliquée dans la vue
    pour les Gestionnaires.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role') or not request.user.role:
            return False
        
        return request.user.role.role in ['Administrateur', 'Gestionnaire']
    
    def has_object_permission(self, request, view, obj):
        # Administrateur a accès à tout
        if request.user.role.role == 'Administrateur':
            return True
        
        # Gestionnaire limité à sa commune
        if hasattr(obj, 'cp_commune_id') and request.user.cp_commune_id:
            return obj.cp_commune_id == request.user.cp_commune_id
        
        return True


class IsAdminOuGestionnaireOuReleveur(permissions.BasePermission):
    """
    Permission pour tous les rôles de l'application mobile.
    
    Utilisé pour les endpoints communs :
    - Authentification
    - Profil utilisateur
    - Changement mot de passe
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role') or not request.user.role:
            return False
        
        return request.user.role.role in ['Administrateur', 'Gestionnaire', 'Releveur']


class IsServiceUser(permissions.BasePermission):
    """
    Permission pour les utilisateurs de service (upload APK, maintenance).
    
    Les utilisateurs de service ont un numéro commençant par 'svc_' ou 'service_'.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superuser a toujours accès
        if request.user.is_superuser:
            return True
        
        # Vérifier le préfixe du numéro
        return (
            request.user.num_utilisateur.startswith('svc_') or
            request.user.num_utilisateur.startswith('service_')
        )


class RoleBasedPermission(permissions.BasePermission):
    """
    Permission dynamique basée sur une liste de rôles autorisés.
    
    Usage:
        @permission_classes([
            RoleBasedPermission(['Administrateur', 'Gestionnaire'])
        ])
        def ma_vue(request):
            ...
    """
    
    def __init__(self, allowed_roles=None):
        """
        Args:
            allowed_roles: Liste des rôles autorisés (ex: ['Administrateur', 'Gestionnaire'])
        """
        self.allowed_roles = allowed_roles or []
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(request.user, 'role') or not request.user.role:
            return False
        
        return request.user.role.role in self.allowed_roles


# Classes prêtes à l'emploi pour les combinaisons courantes
IsReleveurOuGestionnaire = RoleBasedPermission(['Releveur', 'Gestionnaire'])
IsReleveurOuAdministrateur = RoleBasedPermission(['Releveur', 'Administrateur'])
IsGestionnaireOuAdministrateur = IsAdminOuGestionnaire  # Alias
