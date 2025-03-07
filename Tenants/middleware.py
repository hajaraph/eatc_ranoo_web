from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django_tenants.utils import schema_exists, schema_context
from rest_framework import status
from rest_framework.response import Response

from Tenants.models import Entreprise


def schema_use(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):

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
