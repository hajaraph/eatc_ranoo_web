from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.core.cache import cache
from django_tenants.utils import schema_exists, schema_context
from rest_framework import status
from rest_framework.views import APIView
from django.views import View

from Rel_Compteur.api_utils import ApiResponse
from Tenants.models import Entreprise


def get_entreprise_and_schema(request, is_api=False):
    """
    Récupère l'entreprise et le schéma de manière optimisée via Cache/Session.
    """
    # 1. Vérification de l'authentification (basée sur request.user standardisé)
    if not request.user.is_authenticated:
        if is_api:
            return None, None, ApiResponse.error("Authentification requise.", http_status=status.HTTP_401_UNAUTHORIZED)
        
        messages.error(request, "Veuillez vous connecter !")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return None, None, ApiResponse.error("Authentification requise.", http_status=401)
        return None, None, redirect('authentification')

    entreprise_id = request.user.entreprise_id

    # 2. Vérification de l'existence d'une entreprise associée
    if not entreprise_id:
        msg = "Aucune entreprise n'est associée à votre compte."
        if is_api:
            return None, None, ApiResponse.error(msg, http_status=status.HTTP_403_FORBIDDEN)
        
        messages.error(request, msg)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
             return None, None, ApiResponse.error(msg, http_status=403)
        return None, None, redirect('authentification')

    # 3. Récupération du schéma (Optimisation CACHE REDIS)
    cache_key = f"tenant_schema_{entreprise_id}"
    schema_name = cache.get(cache_key)

    if not schema_name:
        try:
            entreprise = Entreprise.objects.get(pk=entreprise_id)
            schema_name = entreprise.schema_name
            # Mise en cache pour 24 heures (86400s)
            cache.set(cache_key, schema_name, 86400)
        except (Entreprise.DoesNotExist, AttributeError):
            msg = "Impossible de déterminer le schéma de l'entreprise."
            if is_api: return None, None, ApiResponse.error(msg, http_status=404)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return None, None, ApiResponse.error(msg, http_status=404)
            messages.error(request, msg)
            return None, None, redirect('authentification')

    # 4. Vérification finale de l'existence physique du schéma
    if not schema_exists(schema_name):
        msg = "Le schéma associé à cette entreprise est inexistant."
        if is_api: return None, None, ApiResponse.error(msg, http_status=404)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest': return None, None, ApiResponse.error(msg, http_status=404)
        messages.error(request, msg)
        return None, None, redirect('authentification')

    return None, schema_name, None


def schema_use(view_func):
    """Décorateur pour les vues Web"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        _, schema_name, error_response = get_entreprise_and_schema(request)
        if error_response:
            return error_response

        with schema_context(schema_name):
            return view_func(request, *args, **kwargs)
    return _wrapped_view


def schema_use_api(view_func):
    """Décorateur pour les vues API"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        _, schema_name, error_response = get_entreprise_and_schema(request, is_api=True)
        if error_response:
            return error_response

        with schema_context(schema_name):
            return view_func(request, *args, **kwargs)
    return _wrapped_view


class SchemaAwareView(View):
    """Classe de base pour les vues basées sur les classes"""
    def dispatch(self, request, *args, **kwargs):
        _, schema_name, error_response = get_entreprise_and_schema(request)
        if error_response:
            return error_response

        with schema_context(schema_name):
            return super().dispatch(request, *args, **kwargs)


class SchemaAwareAPIView(APIView):
    """Classe de base pour les APIView basées sur les schémas"""
    def dispatch(self, request, *args, **kwargs):
        _, schema_name, error_response = get_entreprise_and_schema(request, is_api=True)
        if error_response:
            return error_response

        with schema_context(schema_name):
            return super().dispatch(request, *args, **kwargs)
dispatch(request, *args, **kwargs)