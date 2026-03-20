from django.contrib.auth.hashers import check_password
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from Tenants.models import Utilisateur
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
