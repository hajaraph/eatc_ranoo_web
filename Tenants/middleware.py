from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import resolve
from django_tenants.utils import schema_exists, schema_context
from rest_framework import status
from rest_framework.response import Response

from Tenants.models import Entreprise


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        current_url = resolve(request.path_info).url_name

        # URLs exclues du middleware
        excluded_urls = ['admin:index', 'admin:login', 'authentification']

        # Si l'URL est dans les URLs exclues ou commence par /admin/
        if current_url in excluded_urls or request.path.startswith('/admin/'):
            return self.get_response(request)

        # Vérification de l'utilisateur
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('/admin/')
        else:
            messages.error(request, "Veuillez vous authentifier.")
            return redirect('authentification')

        return self.get_response(request)


def schema_use(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez être connecté pour accéder à cette page.")
            return redirect('authentification')

        entreprise_id = request.session.get('entreprise')
        if not entreprise_id:
            messages.error(request, "Aucune entreprise n'est associée à votre compte.")
            return redirect('authentification')

        try:
            entreprise = Entreprise.objects.get(pk=entreprise_id)
        except Entreprise.DoesNotExist:
            messages.error(request, "Entreprise introuvable.")
            return redirect('authentification')

        schema_name = entreprise.schema_name
        if not schema_exists(schema_name):
            messages.error(request, "Le schéma associé à cette entreprise est inexistant.")
            return redirect('authentification')

        # Appliquer le contexte du schéma
        with schema_context(schema_name):
            return view_func(request, *args, **kwargs)

    return _wrapped_view


def schema_use_api(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Vous devez être connecté pour accéder à cette ressource."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        entreprise_id = getattr(request.user, 'entreprise_id', None)

        if not entreprise_id:
            return Response(
                {"detail": "Aucune entreprise n'est associée à votre compte."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            entreprise = Entreprise.objects.get(pk=entreprise_id)
        except Entreprise.DoesNotExist:
            return Response(
                {"detail": "Entreprise introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        schema_name = entreprise.schema_name
        if not schema_exists(schema_name):
            return Response(
                {"detail": "Le schéma associé à cette entreprise est inexistant."},
                status=status.HTTP_404_NOT_FOUND
            )

        with schema_context(schema_name):
            return view_func(request, *args, **kwargs)

    return _wrapped_view
