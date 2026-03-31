import os
import logging
from django.conf import settings
from django.contrib.auth.hashers import check_password
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from Tenants.models import Utilisateur
from Rel_Compteur.api_utils import ApiResponse
from Login.models import DownloadToken, MobileVersion
from django.urls import reverse
from django.http import FileResponse, JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def authentification(request):
    """
    Authentification multi-rôles pour l'application mobile Ranoo.
    
    Rôles autorisés : Releveur, Gestionnaire, Administrateur
    
    Params:
        - num_utilisateur: Numéro de téléphone de l'utilisateur
        - password: Mot de passe
    
    Returns:
        - access_token: JWT token d'accès (valable 15 min)
        - refresh_token: JWT token de rafraîchissement (valable 30 jours)
        - info_utilisateur: Informations utilisateur et permissions
    """
    num_utilisateur = request.data.get('num_utilisateur')
    motpasse_utilisateur = request.data.get('password')

    if not num_utilisateur or not motpasse_utilisateur:
        return ApiResponse.error(
            "Les champs 'num_utilisateur' et 'password' sont requis.",
            code="MISSING_PARAM",
            http_status=status.HTTP_400_BAD_REQUEST
        )

    try:
        utilisateur = Utilisateur.objects.select_related(
            'role', 'cp_commune', 'cp_commune__region', 'entreprise'
        ).get(num_utilisateur=num_utilisateur)

        if check_password(motpasse_utilisateur, utilisateur.password):
            # 1. Vérifier si le compte est actif
            if not utilisateur.statut:
                logger.warning(f"Compte désactivé: {num_utilisateur}")
                return ApiResponse.error(
                    "Votre compte est désactivé !",
                    code="ACCOUNT_DISABLED",
                    http_status=status.HTTP_401_UNAUTHORIZED
                )

            # 2. Vérifier le rôle de l'utilisateur
            if not utilisateur.role:
                logger.warning(f"Aucun rôle défini: {num_utilisateur}")
                return ApiResponse.error(
                    "Aucun rôle n'est défini pour votre compte. Contactez l'administrateur.",
                    code="NO_ROLE",
                    http_status=status.HTTP_403_FORBIDDEN
                )
            
            role = utilisateur.role.role
            roles_autorises = ['Releveur', 'Gestionnaire', 'Administrateur']
            
            if role not in roles_autorises:
                logger.warning(f"Rôle non autorisé: {role} pour {num_utilisateur}")
                return ApiResponse.error(
                    f"Rôle '{role}' non autorisé sur l'application mobile.",
                    code="ACCESS_DENIED",
                    http_status=status.HTTP_403_FORBIDDEN
                )

            # 3. Déterminer le mode de données selon le rôle
            # Releveur = offline-first, Admin/Gest = online-only
            mode_donnees = 'offline-first' if role == 'Releveur' else 'online-only'

            # 4. Générer les tokens JWT
            refresh_tokens = RefreshToken.for_user(utilisateur)
            access_token = refresh_tokens.access_token

            # Ajouter des claims personnalisées au token
            access_token['role'] = role
            access_token['cp_commune_id'] = utilisateur.cp_commune_id
            access_token['entreprise_id'] = utilisateur.entreprise_id
            access_token['mode_donnees'] = mode_donnees

            logger.info(f"Connexion réussie: {num_utilisateur} (Rôle: {role})")

            # 5. Retourner les tokens avec informations complètes
            return ApiResponse.success(
                data={
                    'access_token': str(access_token),
                    'refresh_token': str(refresh_token),
                    'info_utilisateur': {
                        'id_utilisateur': utilisateur.id_utilisateur,
                        'nom_utilisateur': utilisateur.nom_utilisateur,
                        'prenom_utilisateur': utilisateur.prenom_utilisateur,
                        'num_utilisateur': utilisateur.num_utilisateur,
                        'role': role,
                        'region': utilisateur.cp_commune.region.region if utilisateur.cp_commune and utilisateur.cp_commune.region else None,
                        'commune': utilisateur.cp_commune.commune if utilisateur.cp_commune else None,
                        'cp_commune': utilisateur.cp_commune_id,
                        'entreprise_id': utilisateur.entreprise_id,
                        'mode_donnees': mode_donnees,
                        'permissions': _get_permissions_par_role(role),
                    }
                },
                message=f"Bienvenue {utilisateur.prenom_utilisateur} ({role})"
            )
        else:
            logger.warning(f"Mot de passe incorrect: {num_utilisateur}")
            return ApiResponse.error(
                "Mot de passe incorrect !",
                code="INVALID_PASSWORD",
                http_status=status.HTTP_401_UNAUTHORIZED
            )
    except Utilisateur.DoesNotExist:
        logger.info(f"Tentative compte inexistant: {num_utilisateur}")
        return ApiResponse.error(
            "Votre compte n'existe pas !",
            code="USER_NOT_FOUND",
            http_status=status.HTTP_401_UNAUTHORIZED
        )


def _get_permissions_par_role(role: str) -> dict:
    """
    Retourne les permissions pour chaque rôle.
    
    Args:
        role: Le rôle de l'utilisateur (Releveur, Gestionnaire, Administrateur)
    
    Returns:
        dict: Permissions avec accès aux modules
    """
    permissions_base = {
        'dashboard': False,
        'missions': False,
        'anomalies': False,
        'clients': False,
        'compteurs': False,
        'factures': False,
        'paiements': False,
        'validation_releves': False,
        'parametres': False,
        'utilisateurs': False,
        'depenses': False,
        'recettes': False,
    }
    
    if role == 'Releveur':
        permissions_base.update({
            'dashboard': True,  # Dashboard limité (stats personnelles)
            'missions': True,
            'anomalies': True,
            # Les Releveurs n'ont PAS accès aux factures/paiements
            # Ils se concentrent uniquement sur les relevés de compteurs
        })

    elif role == 'Gestionnaire':
        permissions_base.update({
            'dashboard': True,  # Dashboard complet (limité à sa commune)
            'clients': True,  # Consultation + modification (limité à sa commune)
            'compteurs': True,  # Consultation + validation
            'factures': True,  # Consultation + paiement
            'paiements': True,
            'validation_releves': True,
            'anomalies': True,  # Consultation
            'depenses': True,  # Limité à sa commune
        })
    
    elif role == 'Administrateur':
        permissions_base.update({
            'dashboard': True,  # Dashboard global
            'clients': True,  # CRUD complet
            'compteurs': True,  # CRUD complet
            'factures': True,  # CRUD complet + création
            'paiements': True,
            'validation_releves': True,
            'anomalies': True,  # Consultation + validation
            'parametres': True,  # Tarifs, configuration
            'utilisateurs': True,  # CRUD utilisateurs
            'depenses': True,  # Global
            'recettes': True,  # Global
        })
    
    return permissions_base


@api_view(['GET'])
@permission_classes([AllowAny])
def check_server(request):
    """
    Vue pour vérifier la disponibilité du serveur.
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
    - apk_file: Le fichier APK
    - version: La version (ex: 1.0.0)
    - changelog: Changelog (optionnel)
    - size: Taille du fichier (optionnel)
    """
    # Vérifier que l'utilisateur est un utilisateur de service
    utilisateur = request.user
    # Accepter les préfixes 'svc_' et 'service_' pour les utilisateurs de service
    if not (utilisateur.num_utilisateur.startswith('svc_') or utilisateur.num_utilisateur.startswith('service_')) and not utilisateur.is_superuser:
        return ApiResponse.error(
            "Accès réservé aux services.",
            code="ACCESS_DENIED",
            http_status=status.HTTP_403_FORBIDDEN
        )

    # Récupérer les données
    apk_file = request.FILES.get('apk_file')
    version = request.data.get('version')
    changelog = request.data.get('changelog', '')
    size = request.data.get('size', '')

    # Validation
    if not apk_file:
        return ApiResponse.error(
            "Le fichier APK est requis.",
            code="MISSING_FILE",
            http_status=status.HTTP_400_BAD_REQUEST
        )

    if not version:
        return ApiResponse.error(
            "La version est requise.",
            code="MISSING_VERSION",
            http_status=status.HTTP_400_BAD_REQUEST
        )
    
    # Vérifier l'extension
    if not apk_file.name.endswith('.apk'):
        return ApiResponse.error(
            "Le fichier doit être un APK.",
            code="INVALID_FILE_TYPE",
            http_status=status.HTTP_400_BAD_REQUEST
        )
    
    # Générer le nom de fichier
    filename = f"Ranoo_v{version}.apk"

    # Chemin de stockage
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'login', 'apk')
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, filename)

    # Vérifier si une version avec ce numéro existe déjà
    existing_version = MobileVersion.objects.filter(version=version).first()

    try:
        # Sauvegarder le fichier (écrase l'ancien si existe)
        with open(file_path, 'wb+') as destination:
            for chunk in apk_file.chunks():
                destination.write(chunk)

        # Calculer la taille réelle
        file_size = os.path.getsize(file_path)
        size_mb = f"{file_size / (1024 * 1024):.2f} MB"

        if existing_version:
            # Mettre à jour la version existante
            existing_version.filename = filename
            existing_version.file = file_path
            existing_version.taille = size or size_mb
            existing_version.changelog = changelog
            existing_version.est_actuelle = True
            existing_version.telecharge_par = utilisateur if hasattr(utilisateur, 'id_utilisateur') else None
            existing_version.save()

            mobile_version = existing_version
            logger.info(f"APK v{version} mis à jour (remplacement)")
        else:
            # Créer une nouvelle entrée
            mobile_version = MobileVersion.objects.create(
                version=version,
                filename=filename,
                file=file_path,
                taille=size or size_mb,
                changelog=changelog,
                est_actuelle=True,
                telecharge_par=utilisateur if hasattr(utilisateur, 'id_utilisateur') else None,
            )
            logger.info(f"APK v{version} créé (nouvelle version)")

        # Définir cette version comme actuelle et désactiver les autres
        MobileVersion.objects.exclude(id_version=mobile_version.id_version).update(
            est_actuelle=False
        )
        return ApiResponse.success(
            data={
                'id_version': mobile_version.id_version,
                'filename': filename,
                'version': version,
                'size': size or size_mb,
                'upload_path': file_path,
                'download_url': mobile_version.url_telechargement,
            },
            message=f"APK v{version} uploadé avec succès"
        )

    except Exception as e:
        # Nettoyer le fichier en cas d'erreur
        if os.path.exists(file_path):
            os.remove(file_path)
        return ApiResponse.error(
            f"Erreur lors de l'upload: {str(e)}",
            code="UPLOAD_ERROR",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_mobile_version(request):
    """
    API pour récupérer la version actuelle de l'application mobile.
    Utilisé par l'app pour vérifier les mises à jour.
    """
    version_actuelle = MobileVersion.obtenir_version_actuelle()
    
    if not version_actuelle:
        return ApiResponse.error(
            "Aucune version disponible.",
            code="NO_VERSION",
            http_status=status.HTTP_404_NOT_FOUND
        )
    
    # Incrémenter le compteur de téléchargements si demandé
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
    Génère un token de téléchargement temporaire (valable 24h).
    Peut être utilisé pour sécuriser l'accès aux APK.

    Params optionnels:
    - duration: Durée en heures (défaut: 24)
    - max_downloads: Nombre max de téléchargements (défaut: 5)
    """

    # Récupérer la version demandée
    version_id = request.data.get('version_id')

    if not version_id:
        # Utiliser la version actuelle par défaut
        version = MobileVersion.obtenir_version_actuelle()
        if not version:
            return ApiResponse.error(
                "Aucune version disponible.",
                code="NO_VERSION",
                http_status=status.HTTP_404_NOT_FOUND
            )
    else:
        try:
            version = MobileVersion.objects.get(id_version=version_id)
        except MobileVersion.DoesNotExist:
            return ApiResponse.error(
                "Version non trouvée.",
                code="VERSION_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND
            )

    # Paramètres optionnels
    duration_hours = int(request.data.get('duration', 24))
    max_downloads = int(request.data.get('max_downloads', 5))

    # Limiter la durée maximale à 7 jours (168h)
    duration_hours = min(duration_hours, 168)

    # Récupérer l'IP
    ip_address = request.META.get('REMOTE_ADDR')

    # Créer le token
    token = DownloadToken.create_token(
        mobile_version=version,
        duration_hours=duration_hours,
        max_downloads=max_downloads,
        ip_address=ip_address,
    )

    # Construire l'URL de téléchargement temporaire avec reverse()
    download_path = reverse('download_direct', kwargs={'token_string': token.token})
    download_url = request.build_absolute_uri(download_path)

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


@require_GET
def download_with_token(request, token_string):
    """
    Telecharge le fichier APK avec un token valide.
    Vue Django standard (pas DRF) pour eviter l'interference
    de la negociation de contenu avec le FileResponse binaire.
    """

    # Valider le token
    token = DownloadToken.get_valid_token(token_string)

    if not token:
        return ApiResponse.error(
            "Token invalide ou expiré.",
            code="INVALID_TOKEN",
            http_status=status.HTTP_403_FORBIDDEN
        )

    # Vérifier que le fichier existe
    file_path = token.mobile_version.file.path
    filename = token.mobile_version.filename

    if not os.path.exists(file_path):
        return ApiResponse.error(
            "Fichier non trouvé.",
            code="FILE_NOT_FOUND",
            http_status=status.HTTP_404_NOT_FOUND
        )

    # Incrementer le compteur AVANT le telechargement
    token.increment_download()

    # Envoyer le fichier en forcant le telechargement
    response = FileResponse(
        open(file_path, 'rb'),
        content_type='application/vnd.android.package-archive',
        as_attachment=True,
        filename=filename
    )

    # En-tetes explicites pour garantir le telechargement sur tous les navigateurs
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Content-Length'] = os.path.getsize(file_path)
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """
    Rafraîchit un access token expiré à l'aide d'un refresh token valide.
    
    Utilise quand l'access token expire (15 min) pour continuer sans reconnexion.
    Le refresh token est valable 30 jours et est automatiquement tourné.
    
    Corps de la requête attendu :
    {
        "refresh": "votre_refresh_token"
    }
    
    Retourne :
    {
        "access": "nouvel_access_token",
        "refresh": "nouveau_refresh_token"
    }
    """

    refresh_token_str = request.data.get('refresh')

    if not refresh_token_str:
        logger.warning("Tentative refresh sans token")
        return ApiResponse.error(
            "Le champ 'refresh' est requis.",
            code="MISSING_REFRESH_TOKEN",
            http_status=status.HTTP_400_BAD_REQUEST
        )

    try:
        refresh_token_obj = RefreshToken(refresh_token_str)
        access_token = refresh_token_obj.access_token

        logger.info(f"Refresh token réussi")
        
        return ApiResponse.success(
            data={
                'access_token': str(access_token),
                'refresh_token': str(refresh_token_obj),
                'token_type': 'Bearer',
                'expires_in': 900,
            },
            message="Token rafraîchi avec succès"
        )

    except TokenError as e:
        logger.warning(f"Refresh token invalide: {str(e)}")
        return ApiResponse.error(
            "Refresh token invalide ou expiré.",
            code="INVALID_REFRESH_TOKEN",
            http_status=status.HTTP_401_UNAUTHORIZED
        )
    except InvalidToken as e:
        logger.warning(f"Refresh token malformé: {str(e)}")
        return ApiResponse.error(
            "Refresh token malformé.",
            code="MALFORMED_TOKEN",
            http_status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Erreur refresh token: {str(e)}")
        return ApiResponse.error(
            f"Erreur serveur: {str(e)}",
            code="SERVER_ERROR",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
