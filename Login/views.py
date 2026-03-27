import logging
from functools import wraps
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.hashers import check_password
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View

from Tenants.models import Utilisateur, Initial
from Login.models import MobileVersion, DownloadToken

logger = logging.getLogger(__name__)

# Constantes de session
SESSION_KEY = 'num_utilisateur'
SESSION_ROLE_KEY = 'role_utilisateur'
SESSION_FIELDS = [
    'id_utilisateur',
    'nom_utilisateur',
    'prenom_utilisateur',
    'num_utilisateur',
    'role_utilisateur',
    'photo_utilisateur',
    'initial_utilisateur',
    'entreprise',
    'cp_commune',
]

# Constantes de redirection
REDIRECT_ROLES_RELEVEUR = ['Releveur', 'Gestionnaire']
RELEVEUR_REDIRECT = 'compteur_list'
DEFAULT_REDIRECT = 'tableau_bord'
ADMIN_REDIRECT = '/admin'

# Messages
MSG_AUTH_REQUIS = "Veuillez vous connecter !"
MSG_ADMIN_REDIRECT = "Les administrateurs doivent utiliser l'interface d'administration (/admin)."
MSG_COMPTE_INEXISTANT = "Votre compte n'existe pas !"
MSG_MDP_INCORRECT = "Mot de passe incorrect !"
MSG_COMPTE_DESACTIVE = "Votre compte a été désactivé. Veuillez contacter l'Administrateur !"
MSG_PERMISSION_REFUSEE = "Vous n'avez pas la permission nécessaire pour effectuer cette tâche !"


def authentification_requis(view_func):
    """
    Décorateur pour vérifier si un utilisateur est connecté.
    Redirige vers la page de login ou retourne 403 pour les requêtes AJAX.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get(SESSION_KEY):
            messages.error(request, MSG_AUTH_REQUIS)
            logger.warning(f"Tentative accès non authentifié: {request.path}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(
                    {"error": "Authentification requise", "redirect": "/login"},
                    status=403
                )
            return redirect('authentification')
        return view_func(request, *args, **kwargs)

    return wrapper


def role_requis(*roles):
    """
    Décorateur pour restreindre l'accès selon le rôle de l'utilisateur.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request_or_self, *args, **kwargs):
            request = _get_request_from_view(request_or_self)

            if not request or not hasattr(request, 'session'):
                logger.error("Session non disponible")
                return HttpResponseForbidden("Session non disponible")

            user_role = request.session.get(SESSION_ROLE_KEY)
            
            if user_role in roles:
                return view_func(request_or_self, *args, **kwargs)
            
            logger.warning(f"Tentative accès rôle non autorisé: {user_role} pour {request.path}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"error": "Permission refusée"}, status=403)
            
            messages.error(request, MSG_PERMISSION_REFUSEE)
            return HttpResponseForbidden(MSG_PERMISSION_REFUSEE)

        return _wrapped_view
    return decorator


def _get_request_from_view(request_or_self):
    """Extrait l'objet request d'une vue classe ou fonction."""
    if hasattr(request_or_self, 'request'):
        return request_or_self.request
    return request_or_self


def _is_ajax_request(request):
    """Vérifie si la requête est une requête AJAX."""
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _get_creator_name(utilisateur):
    """Récupère le nom du créateur du compte utilisateur."""
    try:
        initial = Initial.objects.get(utilisateur_cree=utilisateur.pk)
        return f"{initial.utilisateur_createur.nom_utilisateur} {initial.utilisateur_createur.prenom_utilisateur}"
    except Initial.DoesNotExist:
        return "Système / Admin"
    except Exception as e:
        logger.error(f"Erreur récupération créateur: {str(e)}")
        return "Système / Admin"


def _setup_session(request, utilisateur):
    """Configure la session avec les données de l'utilisateur."""
    session_data = {
        'id_utilisateur': utilisateur.id_utilisateur,
        'nom_utilisateur': utilisateur.nom_utilisateur,
        'prenom_utilisateur': utilisateur.prenom_utilisateur,
        'num_utilisateur': utilisateur.num_utilisateur,
        'role_utilisateur': utilisateur.role.role if utilisateur.role else None,
        'photo_utilisateur': utilisateur.photo_utilisateur.url if utilisateur.photo_utilisateur else None,
        'initial_utilisateur': _get_creator_name(utilisateur),
        'entreprise': utilisateur.entreprise_id,
    }

    for key, value in session_data.items():
        request.session[key] = value

    # Gestion de la durée de session (Se souvenir de moi)
    request.session.set_expiry(None)


def _get_redirect_destination(utilisateur):
    """Détermine la destination de redirection après connexion."""
    role = utilisateur.role.role if utilisateur.role else None

    if role in REDIRECT_ROLES_RELEVEUR:
        # Redirection spécifique pour Releveur
        if role == 'Releveur':
            return RELEVEUR_REDIRECT
        return DEFAULT_REDIRECT

    return DEFAULT_REDIRECT


class Authentification(View):
    """
    Vue de gestion de l'authentification.
    GET: Affiche le formulaire de connexion
    POST: Traite l'authentification
    """
    template_name = 'login/login_page.html'

    def get(self, request):
        """Affiche la page de login ou redirige si déjà connecté."""
        if request.session.get(SESSION_KEY):
            role = request.session.get(SESSION_ROLE_KEY)
            destination = RELEVEUR_REDIRECT if role == 'Releveur' else DEFAULT_REDIRECT
            return redirect(destination)
        
        return render(request, self.template_name)

    @staticmethod
    def post(request):
        """
        Traite l'authentification de l'utilisateur.
        """
        num_utilisateur = request.POST.get('num_utilisateur')
        motpasse_utilisateur = request.POST.get('motpasse_utilisateur')
        sauvegarder = request.POST.get('sauvegarder')

        # Validation des champs requis
        if not num_utilisateur or not motpasse_utilisateur:
            messages.error(request, "Numéro d'utilisateur et mot de passe requis.")
            logger.warning(f"Tentative connexion sans credentials: {request.META.get('REMOTE_ADDR')}")
            return redirect('authentification')

        # 1. Vérifier si l'utilisateur existe
        try:
            utilisateur = Utilisateur.objects.select_related('role').get(
                num_utilisateur=num_utilisateur
            )
        except Utilisateur.DoesNotExist:
            messages.warning(request, MSG_COMPTE_INEXISTANT)
            logger.info(f"Tentative connexion compte inexistant: {num_utilisateur}")
            return redirect('authentification')

        # 2. Bloquer l'accès aux SuperAdmin / Staff
        if utilisateur.is_superuser or utilisateur.is_staff:
            messages.warning(request, MSG_ADMIN_REDIRECT)
            logger.info(f"Tentative connexion admin sur interface standard: {num_utilisateur}")
            return redirect('authentification')

        # 3. Vérifier le mot de passe
        if not check_password(motpasse_utilisateur, utilisateur.password):
            messages.error(request, MSG_MDP_INCORRECT)
            logger.warning(f"Échec authentification: {num_utilisateur}")
            return redirect('authentification')

        # 4. Vérifier le statut du compte
        if not utilisateur.statut:
            messages.warning(request, MSG_COMPTE_DESACTIVE)
            logger.warning(f"Tentative connexion compte désactivé: {num_utilisateur}")
            return redirect('authentification')

        # 5. Configuration de la session
        _setup_session(request, utilisateur)

        # Gestion de la durée de session (Se souvenir de moi)
        if sauvegarder:
            request.session.set_expiry(None)
        else:
            request.session.set_expiry(0)

        # 6. Redirection selon le rôle
        destination = _get_redirect_destination(utilisateur)
        
        logger.info(f"Connexion réussie: {num_utilisateur} -> {destination}")
        return redirect(destination)


def deconnexion(request):
    """Déconnecte l'utilisateur et redirige vers la page de login."""
    user = request.session.get(SESSION_KEY)
    if user:
        logger.info(f"Déconnexion: {user}")
    logout(request)
    return redirect('authentification')


@authentification_requis
def mobile_app_page(request):
    """
    Page de téléchargement de l'application mobile pour les releveurs.
    Accessible uniquement aux utilisateurs connectés.
    """
    version_actuelle = MobileVersion.obtenir_version_actuelle()
    versions_precedentes = MobileVersion.obtenir_historique()

    context = {
        'current_version': None,
        'previous_versions': [],
        'apk_download_url': '',
        'has_versions': False,
        'download_token': None,
        'token_expires_at': None,
    }

    if version_actuelle:
        temp_download_url = _generate_temp_download_url(request, version_actuelle)
        
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
            'apk_download_url': temp_download_url or version_actuelle.url_telechargement,
            'has_versions': True,
            'download_token': temp_download_url,
            'token_expires_at': timezone.now() + timedelta(hours=24),
        }

    return render(request, 'login/mobile_app.html', context)


def _generate_temp_download_url(request, version_actuelle):
    """Génère une URL de téléchargement temporaire avec token."""
    try:
        ip_address = request.META.get('REMOTE_ADDR')
        token_obj = DownloadToken.create_token(
            mobile_version=version_actuelle,
            duration_hours=24,
            max_downloads=5,
            ip_address=ip_address,
        )
        download_path = reverse('download_direct', kwargs={'token_string': token_obj.token})
        url = request.build_absolute_uri(download_path)
        logger.info(f"Token téléchargement généré: {version_actuelle.filename}")
        return url
    except Exception as e:
        logger.error(f"Erreur génération token: {str(e)}")
        return None
