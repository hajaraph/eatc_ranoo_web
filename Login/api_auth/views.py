from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response

from Compteurs.api_compteur.views import Missions
from Login.api_auth.serializer import UtilisateurSerializer, UtilisateurSerializerWithLastToken
from Tenants.middleware import schema_use_api
from Tenants.models import Utilisateur
from Main_Courante.models import StatutMC


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
            if utilisateur.role.role == "Releveur":
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
                raise AuthenticationFailed("Veuillez vous connecter dans l'application web !")
        else:
            raise AuthenticationFailed('Mot de passe incorrect !')
    except Utilisateur.DoesNotExist:
        raise AuthenticationFailed("Votre compte n'existe pas !")


@api_view(['GET'])
def get_users(request):
    users = Utilisateur.objects.filter(role_id=3)
    serializer = UtilisateurSerializerWithLastToken(users, many=True)
    
    return JsonResponse(serializer.data, safe=False)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@schema_use_api
def donne_tout(request):
    utilisateurs = Utilisateur.objects.filter(role_id=3)
    utilisateur_liste = [
        {
            'id_utilisateur': utilisateur.id_utilisateur,
            'nom_utilisateur': utilisateur.nom_utilisateur,
            'prenom_utilisateur': utilisateur.prenom_utilisateur,
            'num_utilisateurs': utilisateur.num_utilisateur,
            'cp_commune': utilisateur.cp_commune_id
        }
        for utilisateur in utilisateurs
    ]

    main_courantes = StatutMC.objects.all()
    main_courante_liste = [
        {
            'id_main_courante': main_courante.main_courante.id_mc,
            'date_declaration': main_courante.main_courante.date_mc,
            'type_anomalie': main_courante.main_courante.type_anomalie
        }
        for main_courante in main_courantes
    ]

    mission = Missions.get_liste_mission(request)

    return JsonResponse(
        {
            'utilisateur_liste': utilisateur_liste,
            'main_courante_liste': main_courante_liste,
            'mission': mission
        }
    )


@api_view(['GET'])
def check_server(request):
    """
    Vue pour vérifier la disponibilité du serveur.
    """
    return Response({'status': 'Server is available'}, status=status.HTTP_200_OK)
