import os
import uuid
from datetime import datetime
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken

from Tenants.models import Utilisateur
from Login.models import MobileVersion
from Rel_Compteur.api_utils import ApiResponse


@api_view(['POST'])
@permission_classes([AllowAny])
def authentification(request):
    num_utilisateur = request.data.get('num_utilisateur')
    motpasse_utilisateur = request.data.get('password')

    if not num_utilisateur or not motpasse_utilisateur:
        return ApiResponse.error(
            "Les champs 'num_utilisateur' et 'password' sont requis.",
            code="MISSING_PARAM",
            http_status=status.HTTP_400_BAD_REQUEST
        )

    try:
        utilisateur = Utilisateur.objects.get(num_utilisateur=num_utilisateur)
        if check_password(motpasse_utilisateur, utilisateur.password):
            # 1. Vérifier si le compte est actif
            if not utilisateur.statut:
                return ApiResponse.error(
                    "Votre compte est désactivé !",
                    code="ACCOUNT_DISABLED",
                    http_status=status.HTTP_401_UNAUTHORIZED
                )

            # 2. Vérifier si c'est un Releveur (avec sécurité si role est None)
            if utilisateur.role and utilisateur.role.role == "Releveur":
                refresh_token = RefreshToken.for_user(utilisateur)
                access_token = refresh_token.access_token

                utilisateur.last_token = str(access_token)
                utilisateur.save()

                return ApiResponse.success(
                    data={
                        'access_token': str(access_token),
                        'info_utilisateur': {
                            'id_utilisateur': utilisateur.id_utilisateur,
                            'nom_utilisateur': utilisateur.nom_utilisateur,
                            'prenom_utilisateur': utilisateur.prenom_utilisateur,
                            'num_utilisateur': utilisateur.num_utilisateur,
                            'role': utilisateur.role.role,
                            'region': utilisateur.cp_commune.region.region,
                            'commune': utilisateur.cp_commune.commune,
                            'cp_commune': utilisateur.cp_commune_id,
                            'last_token': utilisateur.last_token
                        }
                    }
                )
            else:
                return ApiResponse.error(
                    "Accès réservé aux Releveurs. Veuillez utiliser l'application web.",
                    code="ACCESS_DENIED",
                    http_status=status.HTTP_403_FORBIDDEN
                )
        else:
            return ApiResponse.error(
                "Mot de passe incorrect !",
                code="INVALID_PASSWORD",
                http_status=status.HTTP_401_UNAUTHORIZED
            )
    except Utilisateur.DoesNotExist:
        return ApiResponse.error(
            "Votre compte n'existe pas !",
            code="USER_NOT_FOUND",
            http_status=status.HTTP_401_UNAUTHORIZED
        )


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
    user = request.user
    # Accepter les préfixes 'svc_' et 'service_' pour les utilisateurs de service
    if not (user.num_utilisateur.startswith('svc_') or user.num_utilisateur.startswith('service_')) and not user.is_superuser:
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
    filename = f"EATC_Releveurs_v{version}.apk"

    # Chemin de stockage
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'login', 'apk')
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, filename)

    try:
        # Sauvegarder le fichier
        with open(file_path, 'wb+') as destination:
            for chunk in apk_file.chunks():
                destination.write(chunk)

        # Calculer la taille réelle
        file_size = os.path.getsize(file_path)
        size_mb = f"{file_size / (1024 * 1024):.2f} MB"
        
        # Créer l'entrée en base de données
        mobile_version = MobileVersion.objects.create(
            version=version,
            filename=filename,
            file=file_path,
            taille=size or size_mb,
            changelog=changelog,
            est_actuelle=True,  # Première version ou version par défaut
            telecharge_par=user if hasattr(user, 'id_utilisateur') else None,
        )
        
        # Si c'est la première version, la définir comme actuelle
        if MobileVersion.objects.filter(est_actuelle=True).exclude(id_version=mobile_version.id_version).exists():
            # S'il y a déjà une version actuelle, on ne définit pas celle-ci comme actuelle automatiquement
            mobile_version.est_actuelle = False
            mobile_version.save(update_fields=['est_actuelle'])

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
