from functools import wraps
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse

from django.contrib import messages
from django.contrib.auth import logout, login
from django.contrib.auth.hashers import check_password
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.views import View

from Rel_Compteur.api_utils import ApiResponse
from Tenants.models import Utilisateur, Initial
from Login.models import MobileVersion, DownloadToken


# Fonction decorateur pour verifie si un utilisateur et connecté ou pas avant d'acceder a un url
def authentification_requis(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Veuillez vous connecter !")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return ApiResponse.error(message="Authentification requise", details={"redirect": "/login"}, http_status=403)
            return redirect('authentification')
        return view_func(request, *args, **kwargs)
    return wrapper


# Fonction decorateur pour donné l'accès à un utilisateur
def role_requis(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request_or_self, *args, **kwargs):
            # Si c'est une méthode de classe, request est le deuxième argument
            request = request_or_self.request if hasattr(request_or_self, 'request') else request_or_self

            if not request.user.is_authenticated:
                return redirect('authentification')

            # Utilisation du rôle stocké en session (pour compatibilité) ou via request.user
            user_role = request.session.get('role_utilisateur') or (request.user.role.role if hasattr(request.user, 'role') else None)
            
            if user_role in roles:
                return view_func(request_or_self, *args, **kwargs)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return ApiResponse.error(message="Permission refusée", http_status=403)
            return HttpResponseForbidden("Vous n'avez pas la permission nécessaire pour effectuer cette tâche !")

        return _wrapped_view
    return decorator


class Authentification(View):
    template_name = 'login/login_page.html'

    def get(self, request):
        if request.user.is_authenticated:
            if request.session.get('role_utilisateur') == 'Releveur':
                return redirect('compteur_list')
            return redirect('tableau_bord')
        return render(request, self.template_name)

    def post(self, request):
        num_utilisateur = request.POST.get('num_utilisateur')
        motpasse_utilisateur = request.POST.get('motpasse_utilisateur')
        sauvegarder = request.POST.get('sauvegarder')

        # 1. Vérifier si l'utilisateur existe
        try:
            utilisateur = Utilisateur.objects.get(num_utilisateur=num_utilisateur)
        except Utilisateur.DoesNotExist:
            messages.warning(request, "Votre Compte n'existe pas !")
            return redirect('authentification')

        # 2. Bloquer l'accès aux SuperAdmin / Staff sur cette interface (Redirection admin)
        if utilisateur.is_superuser or utilisateur.is_staff:
            messages.warning(request, "Les administrateurs doivent utiliser l'interface d'administration.")
            return redirect('authentification')

        # 3. Vérifier le mot de passe via Django Check
        if not check_password(motpasse_utilisateur, utilisateur.password):
            messages.error(request, 'Mot de passe incorrect !')
            return redirect('authentification')

        # 4. Vérifier le statut du compte
        if not utilisateur.statut:
            messages.warning(request, "Votre compte a été désactivé, Veuillez contacter l'Administrateur !")
            return redirect('authentification')

        # 5. Authentification officielle Django
        login(request, utilisateur)

        # 6. Configuration de la session (Maintien de la compatibilité avec l'existant)
        try:
            initial = Initial.objects.get(utilisateur_cree=utilisateur.pk)
            creator_name = f"{initial.utilisateur_createur.nom_utilisateur} {initial.utilisateur_createur.prenom_utilisateur}"
        except Initial.DoesNotExist:
            creator_name = "Système / Admin"

        request.session['id_utilisateur'] = utilisateur.id_utilisateur
        request.session['nom_utilisateur'] = utilisateur.nom_utilisateur
        request.session['prenom_utilisateur'] = utilisateur.prenom_utilisateur
        request.session['num_utilisateur'] = utilisateur.num_utilisateur
        request.session['role_utilisateur'] = utilisateur.role.role if utilisateur.role else None
        request.session['photo_utilisateur'] = utilisateur.photo_utilisateur.url if utilisateur.photo_utilisateur else None
        request.session['initial_utilisateur'] = creator_name
        request.session['entreprise'] = utilisateur.entreprise_id
        
        if utilisateur.role and utilisateur.role.role in ['Releveur', 'Gestionnaire']:
            request.session['cp_commune'] = utilisateur.cp_commune_id

        # Gestion de la durée de session
        request.session.set_expiry(None if sauvegarder else 0)

        # 7. Redirection intelligente
        destination = 'compteur_list' if utilisateur.role and utilisateur.role.role == 'Releveur' else 'tableau_bord'
        return redirect(destination)


def deconnexion(request):
    logout(request)
    return redirect('authentification')


@authentification_requis
def mobile_app_page(request):
    # Version actuelle depuis la base de données
    version_actuelle = MobileVersion.obtenir_version_actuelle()
    versions_precedentes = MobileVersion.obtenir_historique()

    temp_download_url = None
    if version_actuelle:
        ip_address = request.META.get('REMOTE_ADDR')
        token_obj = DownloadToken.create_token(
            mobile_version=version_actuelle,
            duration_hours=24,
            max_downloads=5,
            ip_address=ip_address,
        )
        download_path = reverse('download_direct', kwargs={'token_string': token_obj.token})
        temp_download_url = request.build_absolute_uri(download_path)

    context = {
        'current_version': {
            'version': version_actuelle.version if version_actuelle else None,
            'date': version_actuelle.telecharge_le if version_actuelle else None,
            'size': version_actuelle.taille if version_actuelle else None,
            'changelog': version_actuelle.changelog.split('\n') if version_actuelle and version_actuelle.changelog else [],
        },
        'previous_versions': [
            {
                'version': v.version,
                'date': v.telecharge_le,
                'size': v.taille,
                'download_url': v.url_telechargement,
            } for v in versions_precedentes
        ],
        'apk_download_url': temp_download_url if temp_download_url else (version_actuelle.url_telechargement if version_actuelle else ''),
        'has_versions': version_actuelle is not None,
        'download_token': temp_download_url,
        'token_expires_at': timezone.now() + timedelta(hours=24),
    }

    return render(request, 'login/mobile_app.html', context)
