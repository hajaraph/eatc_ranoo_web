from django.contrib.auth.hashers import check_password
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response

from Tenants.models import Utilisateur


@api_view(['POST'])
def authentification(request):
    num_utilisateur = request.data.get('num_utilisateur')
    motpasse_utilisateur = request.data.get('password')

    if not num_utilisateur or not motpasse_utilisateur:
        return Response(
            {"detail": "Les champs 'num_utilisateur' et 'password' sont requis."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        utilisateur = Utilisateur.objects.get(num_utilisateur=num_utilisateur)
        if check_password(motpasse_utilisateur, utilisateur.password):
            # 1. Vérifier si le compte est actif
            if not utilisateur.statut:
                raise AuthenticationFailed("Votre compte est désactivé !")

            # 2. Vérifier si c'est un Releveur (avec sécurité si role est None)
            if utilisateur.role and utilisateur.role.role == "Releveur":
                refresh_token = RefreshToken.for_user(utilisateur)
                access_token = refresh_token.access_token

                utilisateur.last_token = str(access_token)
                utilisateur.save()

                return Response({
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
                }, status=status.HTTP_200_OK)
            else:
                # Message générique ou spécifique selon besoin. Ici on dit juste que c'est pour l'app web.
                raise AuthenticationFailed("Accès réservé aux Releveurs. Veuillez utiliser l'application web.")
        else:
            raise AuthenticationFailed('Mot de passe incorrect !')
    except Utilisateur.DoesNotExist:
        raise AuthenticationFailed("Votre compte n'existe pas !")


@api_view(['GET'])
def check_server(request):
    """
    Vue pour vérifier la disponibilité du serveur.
    """
    return Response({'status': 'Server is available'}, status=status.HTTP_200_OK)
