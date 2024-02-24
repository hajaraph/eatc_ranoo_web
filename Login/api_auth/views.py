from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from Compteurs.api_compteur.views import Missions
from Login.api_auth.serializer import UtilisateurSerializer
from Login.models import Utilisateur
from Main_Courante.models import StatutMC


@api_view(['POST'])
def authentification(request):
    serializer = UtilisateurSerializer(data=request.data)
    if serializer.is_valid():
        num_utilisateur = serializer.validated_data['num_utilisateur']
        motpasse_utilisateur = serializer.validated_data['password']

        try:
            utilisateur = Utilisateur.objects.get(num_utilisateur=num_utilisateur)

            if check_password(motpasse_utilisateur, utilisateur.password):

                if utilisateur.role.role == "Releveur":
                    refresh_token = RefreshToken.for_user(utilisateur)
                    access_token = refresh_token.access_token
                    # access_token = Token.objects.get_or_create(user=utilisateur)
                    return JsonResponse(
                        {
                            'access_token': str(access_token),
                            'info_utilisateur': {
                                'id_utilisateur': utilisateur.id_utilisateur,
                                'nom_utilisateur': utilisateur.nom_utilisateur,
                                'prenom_utilisateur': utilisateur.prenom_utilisateur,
                                'num_utilisateur': utilisateur.num_utilisateur,
                                'role': utilisateur.role.role,
                                'region': utilisateur.cp_commune.region.region,
                                'commune': utilisateur.cp_commune.commune,
                                'cp_commune': utilisateur.cp_commune_id
                            }
                        }
                    )

                else:
                    raise AuthenticationFailed("Veuillez vous connecté dans l'application web !")

            else:
                raise AuthenticationFailed('Mot de passe incorrect !')

        except Utilisateur.DoesNotExist:
            raise AuthenticationFailed("Votre Compte n'existe pas !")

    else:
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def donne_tout(request):
    utilisateurs = Utilisateur.objects.all()
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
