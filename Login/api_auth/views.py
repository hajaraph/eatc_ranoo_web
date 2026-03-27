import os
import logging
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken

from Tenants.models import Utilisateur
from Rel_Compteur.api_utils import ApiResponse
from Login.models import DownloadToken, MobileVersion
from django.urls import reverse
from django.http import FileResponse

logger = logging.getLogger(__name__)

# Constantes de validation
ALLOWED_ROLES = ['Releveur']
MAX_PASSWORD_LENGTH = 128


def _validate_auth_request(data):
    """Valide les paramètres requis pour l'authentification."""
    num_utilisateur = data.get('num_utilisateur')
    motpasse_utilisateur = data.get('password')

    if not num_utilisateur or not motpasse_utilisateur:
        return None, None, "Les champs 'num_utilisateur' et 'password' sont requis."

    if len(motpasse_utilisateur) > MAX_PASSWORD_LENGTH:
        return None, None, "Mot de passe trop long."

    return num_utilisateur, motpasse_utilisateur, None


def _check_user_credentials(utilisateur, motpasse_utilisateur):
    """Vérifie les identifiants utilisateur et retourne les tokens si valides."""
    if not utilisateur.statut:
        logger.warning(f"Tentative connexion compte désactivé: {utilisateur.num_utilisateur}")
        return None, "Compte désactivé."

    if not utilisateur.role or utilisateur.role.role not in ALLOWED_ROLES:
        logger.warning(f"Tentative connexion rôle non autorisé: {utilisateur.num_utilisateur}")
        return None, "Accès réservé aux Releveurs."

    if not check_password(motpasse_utilisateur, utilisateur.password):
        logger.warning(f"Échec authentification: {utilisateur.num_utilisateur}")
        return None, "Identifiants incorrects."

    return _generate_tokens(utilisateur), None


def _generate_tokens(utilisateur):
    """Génère et retourne les tokens JWT pour un utilisateur."""
    refresh_token = RefreshToken.for_user(utilisateur)
    access_token = refresh_token.access_token

    with transaction.atomic():
        Utilisateur.objects.filter(
            pk=utilisateur.pk
        ).update(
            last_token=str(access_token)
        )

    return {
        'access_token': str(access_token),
        'refresh_token': str(refresh_token),
        'info_utilisateur': {
            'id_utilisateur': utilisateur.id_utilisateur,
            'nom_utilisateur': utilisateur.nom_utilisateur,
            'prenom_utilisateur': utilisateur.prenom_utilisateur,
            'num_utilisateur': utilisateur.num_utilisateur,
            'role': utilisateur.role.role,
            'region': utilisateur.cp_commune.region.region if utilisateur.cp_commune and utilisateur.cp_commune.region else None,
            'commune': utilisateur.cp_commune.commune if utilisateur.cp_commune else None,
            'cp_commune': utilisateur.cp_commune_id,
        }
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def authentification(request):
    """
    Authentifie un utilisateur et retourne un token JWT.
    Réservé aux Releveurs avec compte actif.
    """
    num_utilisateur, motpasse_utilisateur, validation_error = _validate_auth_request(request.data)

    if validation_error:
        return ApiResponse.error(
            validation_error,
            code="MISSING_PARAM",
            http_status=status.HTTP_400_BAD_REQUEST
        )

    try:
        utilisateur = Utilisateur.objects.select_related(
            'role', 'cp_commune', 'cp_commune__region'
        ).get(num_utilisateur=num_utilisateur)
    except Utilisateur.DoesNotExist:
        logger.info(f"Tentative connexion utilisateur inexistant: {num_utilisateur}")
        return ApiResponse.error(
            "Identifiants incorrects.",
            code="AUTH_FAILED",
            http_status=status.HTTP_401_UNAUTHORIZED
        )

    token_data, auth_error = _check_user_credentials(utilisateur, motpasse_utilisateur)

    if auth_error:
        return ApiResponse.error(
            auth_error,
            code="AUTH_FAILED",
            http_status=status.HTTP_401_UNAUTHORIZED
        )

    logger.info(f"Connexion réussie: {num_utilisateur}")
    return ApiResponse.success(data=token_data)


# Constantes pour l'upload APK
APK_MAX_SIZE_MB = 200
APK_ALLOWED_EXTENSIONS = ['.apk']
VERSION_PATTERN_MAX_LENGTH = 20


def _validate_apk_upload(request):
    """Valide les données d'upload APK. Retourne (données_validées, erreur)."""
    user = request.user

    if not (user.num_utilisateur.startswith('svc_') or 
            user.num_utilisateur.startswith('service_')) and not user.is_superuser:
        return None, "Accès réservé aux services."

    apk_file = request.FILES.get('apk_file')
    version = request.data.get('version')

    if not apk_file:
        return None, "Le fichier APK est requis."

    if not version or len(version) > VERSION_PATTERN_MAX_LENGTH:
        return None, "Version requise (max 20 caractères)."

    if not any(apk_file.name.lower().endswith(ext) for ext in APK_ALLOWED_EXTENSIONS):
        return None, "Fichier APK invalide."

    if apk_file.size > APK_MAX_SIZE_MB * 1024 * 1024:
        return None, f"Fichier trop volumineux (max {APK_MAX_SIZE_MB}MB)."

    changelog = request.data.get('changelog', '')
    size = request.data.get('size', '')

    return {
        'apk_file': apk_file,
        'version': version,
        'changelog': changelog,
        'size': size,
        'user': user,
    }, None


def _save_apk_file(apk_file, version):
    """Sauvegarde le fichier APK et retourne le chemin. Gère le nettoyage en cas d'erreur."""
    filename = f"Ranoo_v{version}.apk"
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'login', 'apk')
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)

    try:
        with open(file_path, 'wb+') as destination:
            for chunk in apk_file.chunks():
                destination.write(chunk)

        file_size = os.path.getsize(file_path)
        size_mb = f"{file_size / (1024 * 1024):.2f} MB"

        return file_path, filename, size_mb, None
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Erreur sauvegarde APK: {str(e)}")
        return None, None, None, f"Erreur sauvegarde: {str(e)}"


@api_view(['GET'])
@permission_classes([AllowAny])
def check_server(request):
    """
    Vérifie la disponibilité du serveur.
    """
    return ApiResponse.success(data={'status': 'Server is available'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@parser_classes([MultiPartParser, FormParser])
def upload_apk(request):
    """
    API d'upload d'APK pour GitHub Actions.
    Sécurisée par TokenAuthentication.

    Champs attendus :
    - apk_file: Le fichier APK (max 100MB)
    - version: La version (ex: 1.0.0, max 20 caractères)
    - changelog: Changelog (optionnel)
    - size: Taille du fichier (optionnel)
    """
    validated_data, error = _validate_apk_upload(request)

    if error:
        return ApiResponse.error(
            error,
            code="ACCESS_DENIED" if "Accès" in error else "VALIDATION_ERROR",
            http_status=status.HTTP_403_FORBIDDEN if "Accès" in error else status.HTTP_400_BAD_REQUEST
        )

    file_path, filename, size_mb, save_error = _save_apk_file(
        validated_data['apk_file'],
        validated_data['version']
    )

    if save_error:
        return ApiResponse.error(
            save_error,
            code="UPLOAD_ERROR",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    try:
        mobile_version = MobileVersion.objects.create(
            version=validated_data['version'],
            filename=filename,
            file=file_path,
            taille=validated_data['size'] or size_mb,
            changelog=validated_data['changelog'],
            est_actuelle=True,
            telecharge_par=validated_data['user'] if hasattr(validated_data['user'], 'id_utilisateur') else None,
        )

        existing_current = MobileVersion.objects.filter(est_actuelle=True).exclude(
            id_version=mobile_version.id_version
        )
        if existing_current.exists():
            mobile_version.est_actuelle = False
            mobile_version.save(update_fields=['est_actuelle'])

        logger.info(f"APK uploadé: {filename} par {validated_data['user'].num_utilisateur}")

        return ApiResponse.success(
            data={
                'id_version': mobile_version.id_version,
                'filename': filename,
                'version': validated_data['version'],
                'size': validated_data['size'] or size_mb,
                'upload_path': file_path,
                'download_url': mobile_version.url_telechargement,
            },
            message=f"APK v{validated_data['version']} uploadé avec succès"
        )

    except Exception as e:
        logger.error(f"Erreur création MobileVersion: {str(e)}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return ApiResponse.error(
            f"Erreur base de données: {str(e)}",
            code="DB_ERROR",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Constantes pour les tokens de téléchargement
TOKEN_MAX_DURATION_HOURS = 168  # 7 jours
TOKEN_DEFAULT_DURATION_HOURS = 24
TOKEN_DEFAULT_MAX_DOWNLOADS = 5


def _get_mobile_version_for_download(version_id=None):
    """Récupère la version mobile demandée ou la version actuelle. Retourne (version, erreur)."""
    if not version_id:
        version = MobileVersion.obtenir_version_actuelle()
        if not version:
            return None, "Aucune version disponible."
        return version, None

    try:
        return MobileVersion.objects.get(id_version=version_id), None
    except MobileVersion.DoesNotExist:
        return None, "Version non trouvée."


def _validate_token_params(duration_hours, max_downloads):
    """Valide les paramètres du token. Retourne (duration_valide, max_downloads_valide, erreur)."""
    try:
        duration_hours = int(duration_hours)
        max_downloads = int(max_downloads)
    except (ValueError, TypeError):
        return None, None, "Paramètres invalides."

    duration_hours = min(max(1, duration_hours), TOKEN_MAX_DURATION_HOURS)
    max_downloads = max(1, max_downloads)

    return duration_hours, max_downloads, None


@api_view(['GET'])
@permission_classes([AllowAny])
def get_mobile_version(request):
    """
    Récupère la version actuelle de l'application mobile.
    Utilisé par l'app pour vérifier les mises à jour.
    """
    version_actuelle = MobileVersion.obtenir_version_actuelle()

    if not version_actuelle:
        return ApiResponse.error(
            "Aucune version disponible.",
            code="NO_VERSION",
            http_status=status.HTTP_404_NOT_FOUND
        )

    if request.GET.get('track_download', 'false').lower() == 'true':
        version_actuelle.incrementer_telechargements()

    return ApiResponse.success(
        data={
            'version': version_actuelle.version,
            'date': version_actuelle.telecharge_le.strftime('%Y-%m-%d'),
            'size': version_actuelle.taille,
            'changelog': version_actuelle.changelog.split('\n') if version_actuelle.changelog else [],
            'download_url': version_actuelle.url_telechargement,
            'force_update': version_actuelle.maj_forcee,
        }
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def generate_download_token(request):
    """
    Génère un token de téléchargement temporaire (valable 24h max 7 jours).
    Peut être utilisé pour sécuriser l'accès aux APK.

    Params optionnels:
    - duration: Durée en heures (défaut: 24, max: 168)
    - max_downloads: Nombre max de téléchargements (défaut: 5)
    - version_id: ID de la version (défaut: version actuelle)
    """
    version_id = request.data.get('version_id')

    version, error = _get_mobile_version_for_download(version_id)
    if error:
        return ApiResponse.error(
            error,
            code="NO_VERSION" if not version_id else "VERSION_NOT_FOUND",
            http_status=status.HTTP_404_NOT_FOUND
        )

    duration_hours, max_downloads, error = _validate_token_params(
        request.data.get('duration', TOKEN_DEFAULT_DURATION_HOURS),
        request.data.get('max_downloads', TOKEN_DEFAULT_MAX_DOWNLOADS)
    )

    if error:
        return ApiResponse.error(
            error,
            code="INVALID_PARAMS",
            http_status=status.HTTP_400_BAD_REQUEST
        )

    ip_address = request.META.get('REMOTE_ADDR')

    token = DownloadToken.create_token(
        mobile_version=version,
        duration_hours=duration_hours,
        max_downloads=max_downloads,
        ip_address=ip_address,
    )

    download_path = reverse('download_direct', kwargs={'token_string': token.token})
    download_url = request.build_absolute_uri(download_path)

    logger.info(f"Token téléchargement généré: {version.filename} pour {ip_address}")

    return ApiResponse.success(
        data={
            'token': token.token,
            'download_url': download_url,
            'expires_at': token.expires_at.isoformat(),
            'expires_in_hours': duration_hours,
            'max_downloads': max_downloads,
            'version': version.version,
            'filename': version.filename,
        },
        message=f"Token généré - Valable {duration_hours}h"
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def download_with_token(request, token_string):
    """
    Télécharge le fichier APK avec un token valide.
    Valide le token et incrémente le compteur.
    """
    token = DownloadToken.get_valid_token(token_string)

    if not token:
        logger.warning(f"Tentative téléchargement avec token invalide: {token_string}")
        return ApiResponse.error(
            "Token invalide ou expiré.",
            code="INVALID_TOKEN",
            http_status=status.HTTP_403_FORBIDDEN
        )

    file_path = token.mobile_version.file.path

    if not os.path.exists(file_path):
        logger.error(f"Fichier APK introuvable: {file_path}")
        return ApiResponse.error(
            "Fichier non trouvé.",
            code="FILE_NOT_FOUND",
            http_status=status.HTTP_404_NOT_FOUND
        )

    token.increment_download()

    logger.info(f"Téléchargement APK: {token.mobile_version.filename} via token {token_string[:8]}...")

    response = FileResponse(
        open(file_path, 'rb'),
        content_type='application/vnd.android.package-archive'
    )
    response['Content-Length'] = os.path.getsize(file_path)
    response['Content-Disposition'] = f'attachment; filename="{token.mobile_version.filename}"'

    return response
