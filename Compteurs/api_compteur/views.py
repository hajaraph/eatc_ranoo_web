from datetime import timedelta

from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from Clients.models import Contrat
from Compteurs.api_compteur.serializer import MissionSerializer
from Compteurs.models import Compteur
from Facturation.models import Tarif
from Main_Courante.models import MainCourante


# def custom_auth_required(view_func):
#     @wraps(view_func)
#     def _wrapped_view(request, *args, **kwargs):
#         token = request.headers.get('Authorization').split(' ')[1]
#         print(token)
#         try:
#             token = request.headers.get('Authorization').split(' ')[1]
#             access_token = AccessToken(token)
#             user = Utilisateur.objects.get(pk=access_token['id_utilisateur'])
#             request.user = user
#         except Exception as e:
#             return JsonResponse({'error': 'Invalid or expired token'}, status=status.HTTP_401_UNAUTHORIZED)
#
#         return view_func(request, *args, **kwargs)
#
#     return _wrapped_view


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def accueil(request):
    cp_commune_id = request.user.cp_commune_id
    jour_proch_relever = Tarif.objects.get(cp_commune_id=cp_commune_id).jour_proch_relever
    non_traite = MainCourante.objects.filter(statuts__non_traite=True).count()
    realise = MainCourante.objects.filter(statuts__realise=True).count()
    total_anomalie = non_traite + realise

    date_limite = timezone.now() - timedelta(days=jour_proch_relever)
    nombre_total_comtpeur = Compteur.objects.filter(contrats__cp_commune_id=cp_commune_id).count()

    nombre_total_compteur_sans_releve = (
        Contrat.objects
        .filter(cp_commune_id=cp_commune_id, num_compteur__relevecompteurs__date_releve__lt=date_limite)
        .distinct()
        .count()
    )

    return JsonResponse(
        {
            'totale_anomalie': total_anomalie,
            'realise': realise,
            'nombre_total_comtpeur': nombre_total_comtpeur,
            'nombre_relever_effectuer': nombre_total_compteur_sans_releve
        }
    )


class Missions(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get_liste_mission(request):
        cp_commune = request.user.cp_commune_id
        jour_proch_relever = Tarif.objects.get(cp_commune_id=cp_commune).jour_proch_relever
        date_limite = timezone.now() - timedelta(days=jour_proch_relever)

        contrats_commune = (
            Contrat.objects
            .filter(cp_commune_id=cp_commune, num_compteur__relevecompteurs__date_releve__lt=date_limite)
            .select_related('client', 'num_compteur')  # Permet de récupérer les informations du client et compteur
            # en une seule requête
            .annotate(
                conso_dernier_releve=F('num_compteur__relevecompteurs__conso')
            )
            # Permet de récupérer les informations du compteur en une seule requête
        )

        liste_contrats_info = [
            {
                'nom_client': contrat.client.nom_client,
                'prenom_client': contrat.client.prenom_client,
                'adresse_client': contrat.client.adresse_client,
                'num_compteur': contrat.num_compteur_id,
                'conso_dernier_releve': contrat.conso_dernier_releve,
            }
            for contrat in contrats_commune
        ]

        return liste_contrats_info

    def get(self, request):
        liste_contrats_info = self.get_liste_mission(request)
        return JsonResponse(
            {
                'compteurs_liste': liste_contrats_info,
            }
        )

    @staticmethod
    @parser_classes((MultiPartParser, FormParser))
    def post(request):
        serializer = MissionSerializer(data=request.data)
        utilisateur = request.user.id_utilisateur

        if serializer.is_valid():
            serializer.save(utilisateur_id=utilisateur)

            return JsonResponse(
                {
                    'enregistre': True,
                },
                status=status.HTTP_201_CREATED
            )
        else:
            return JsonResponse(
                {
                    'erreur': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
