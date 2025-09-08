from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.views import View
from django_tenants.utils import schema_exists, schema_context
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from Tenants.models import Entreprise


def get_entreprise_and_schema(request, is_api=False):
    """Récupère l'entreprise et le schéma en fonction de la requête (API ou Web)"""
    # Authentification
    if is_api:
        if not (hasattr(request, 'user') and request.user.is_authenticated):
            return None, None, Response(
                {"detail": "Authentification requise."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        entreprise_id = request.user.entreprise_id
    else:
        if not request.session.get('num_utilisateur'):
            messages.error(request, f"Veuillez vous connecté !")
            return None, None, redirect('authentification')
        entreprise_id = request.session.get('entreprise')

    # Vérification de l'entreprise
    if not entreprise_id:
        if is_api:
            return None, None, Response(
                {"detail": "Aucune entreprise n'est associée à votre compte."},
                status=status.HTTP_403_FORBIDDEN
            )
        messages.error(request, "Aucune entreprise n'est associée à votre compte.")
        return None, None, redirect('authentification')

    try:
        entreprise = Entreprise.objects.get(pk=entreprise_id)
        schema_name = entreprise.schema_name
    except (Entreprise.DoesNotExist, AttributeError):
        if is_api:
            return None, None, Response(
                {"detail": "Impossible de déterminer le schéma de l'entreprise."},
                status=status.HTTP_404_NOT_FOUND
            )
        messages.error(request, "Impossible de déterminer le schéma de l'entreprise.")
        return None, None, redirect('authentification')

    # Vérification du schéma
    if not schema_exists(schema_name):
        if is_api:
            return None, None, Response(
                {"detail": "Le schéma associé à cette entreprise est inexistant."},
                status=status.HTTP_404_NOT_FOUND
            )
        messages.error(request, "Le schéma associé à cette entreprise est inexistant.")
        return None, None, redirect('authentification')

    return entreprise, schema_name, None


def schema_use(view_func):
    """Décorateur pour les vues Web"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        entreprise, schema_name, error_response = get_entreprise_and_schema(request)
        if error_response:
            return error_response

        with schema_context(schema_name):
            return view_func(request, *args, **kwargs)
    return _wrapped_view


def schema_use_api(view_func):
    """Décorateur pour les vues API"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        entreprise, schema_name, error_response = get_entreprise_and_schema(request, is_api=True)
        if error_response:
            return error_response

        with schema_context(schema_name):
            return view_func(request, *args, **kwargs)
    return _wrapped_view


class SchemaAwareView(View):
    """Classe de base pour les vues basées sur les classes"""
    def dispatch(self, request, *args, **kwargs):
        entreprise, schema_name, error_response = get_entreprise_and_schema(request)
        if error_response:
            return error_response

        with schema_context(schema_name):
            return super().dispatch(request, *args, **kwargs)


class SchemaAwareAPIView(APIView):
    """Classe de base pour les APIView basées sur les schémas"""
    def dispatch(self, request, *args, **kwargs):
        entreprise, schema_name, error_response = get_entreprise_and_schema(request)
        if error_response:
            return error_response

        with schema_context(schema_name):
            return super().dispatch(request, *args, **kwargs)