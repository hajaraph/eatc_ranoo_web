from functools import wraps
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.hashers import check_password
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect
from django.views import View


from Tenants.models import Utilisateur, Initial
from Login.models import MobileVersion


# Fonction decorateur pour verifie si un utilisateur et connecté ou pas avant d'acceder a un url
def authentification_requis(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('num_utilisateur'):
            messages.error(request, f"Veuillez vous connecté !")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"error": "Authentification requise", "redirect": "/login"}, status=403)
            return redirect('authentification')
        return view_func(request, *args, **kwargs)

    return wrapper


# Fonction decorateur pour donné l'accès à un utilisateur
def role_requis(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request_or_self, *args, **kwargs):
            # Si c'est une méthode de classe, request est le deuxième argument
            if hasattr(request_or_self, 'request'):
                request = request_or_self.request
            else:
                request = request_or_self

            if not hasattr(request, 'session'):
                return HttpResponseForbidden("Session non disponible")

            user_role = request.session.get('role_utilisateur')
            if user_role in roles:
                return view_func(request_or_self, *args, **kwargs)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({"error": "Permission refusée"}, status=403)
                return HttpResponseForbidden("Vous n'avez pas la permission nécessaire pour effectuer cette tâche !")

        return _wrapped_view

    return decorator


class Authentification(View):
    template_name = 'login/login_page.html'


    def get(self, request):
        if request.session.get('num_utilisateur'):
            if request.session.get('role_utilisateur') == 'Releveur':
                return redirect('compteur_list')
            else:
                return redirect('tableau_bord')
        else:
            return render(request, self.template_name)

    @staticmethod
    def post(request):
        num_utilisateur = request.POST.get('num_utilisateur')
        motpasse_utilisateur = request.POST.get('motpasse_utilisateur')
        sauvegarder = request.POST.get('sauvegarder')

        # 1. Vérifier si l'utilisateur existe
        try:
            utilisateur = Utilisateur.objects.get(num_utilisateur=num_utilisateur)
        except Utilisateur.DoesNotExist:
            messages.warning(request, "Votre Compte n'existe pas !")
            return redirect('authentification')

        # 2. Bloquer l'accès aux SuperAdmin / Staff sur cette interface
        if utilisateur.is_superuser or utilisateur.is_staff:
            messages.warning(request, "Les administrateurs doivent utiliser l'interface d'administration (/admin).")
            return redirect('authentification')

        # 3. Vérifier le mot de passe
        if not check_password(motpasse_utilisateur, utilisateur.password):
            messages.error(request, 'Mot de passe incorrect !')
            return redirect('authentification')

        # 4. Vérifier le statut du compte
        if not utilisateur.statut:
            messages.warning(request, "Votre compte a été désactivé, Veuillez contacter l'Administrateur !")
            return redirect('authentification')

        # 5. Utilisateur authentifié : Configuration de la session
        try:
            initial = Initial.objects.get(utilisateur_cree=utilisateur.pk)
            creator_name = f"{initial.utilisateur_createur.nom_utilisateur} {initial.utilisateur_createur.prenom_utilisateur}"
        except Initial.DoesNotExist:
            creator_name = "Système / Admin"

        request.session['id_utilisateur'] = utilisateur.id_utilisateur
        request.session['nom_utilisateur'] = utilisateur.nom_utilisateur
        request.session['prenom_utilisateur'] = utilisateur.prenom_utilisateur
        request.session['num_utilisateur'] = utilisateur.num_utilisateur
        request.session['role_utilisateur'] = utilisateur.role.role
        request.session['photo_utilisateur'] = utilisateur.photo_utilisateur.url if utilisateur.photo_utilisateur else None
        request.session['initial_utilisateur'] = creator_name
        request.session['entreprise'] = utilisateur.entreprise_id

        # Gestion de la durée de session (Se souvenir de moi)
        if sauvegarder:
            request.session.set_expiry(None)
        else:
            request.session.set_expiry(0)

        # 6. Redirection selon le rôle
        destination = 'tableau_bord'

        if utilisateur.role.role in ['Releveur', 'Gestionnaire']:
            request.session['cp_commune'] = utilisateur.cp_commune_id

        if utilisateur.role.role == 'Releveur':
            destination = 'compteur_list'

        return redirect(destination)


def deconnexion(request):
    logout(request)
    return redirect('authentification')


@authentification_requis
def mobile_app_page(request):
    """
    Page de téléchargement de l'application mobile pour les releveurs.
    Accessible uniquement aux utilisateurs connectés.
    """

    # Version actuelle depuis la base de données
    version_actuelle = MobileVersion.obtenir_version_actuelle()

    # Versions précédentes (historique)
    versions_precedentes = MobileVersion.obtenir_historique()

    # Préparer le contexte
    if version_actuelle:
        context = {
            'current_version': {
                'version': version_actuelle.version,
                'date': version_actuelle.telecharge_le,
                'size': version_actuelle.taille,
                'changelog': version_actuelle.changelog.split('\n') if version_actuelle.changelog else [],
            },
            'previous_versions': [
                {
                    'version': v.version,
                    'date': v.telecharge_le,
                    'size': v.taille,
                    'download_url': v.url_telechargement,
                }
                for v in versions_precedentes
            ],
            'apk_download_url': version_actuelle.url_telechargement if version_actuelle else '',
            'has_versions': version_actuelle is not None,
        }
    else:
        context = {
            'current_version': None,
            'previous_versions': [],
            'apk_download_url': '',
            'has_versions': False,
        }

    return render(request, 'login/mobile_app.html', context)
