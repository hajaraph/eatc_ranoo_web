from django.db.models import Count
from django.db.models import Q

from django.http import JsonResponse
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from Clients.models import Contrat

from Compteurs.api_compteur.serializer import MissionSerializer
from Compteurs.models import Compteur, ReleveCompteur
from Compteurs.views import relever
from Facturation.views import facture_creation
from Main_Courante.models import MainCourante
from django.db.models import Sum, Max
from pandas.tseries.offsets import MonthEnd
import pandas as pd

from Parametre.views import enregistre_historique


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def accueil(request):
    cp_commune_id = request.user.cp_commune_id
    non_traite = MainCourante.objects.filter(statuts__non_traite=True).count()
    realise = MainCourante.objects.filter(statuts__realise=True).count()
    total_anomalie = non_traite + realise

    nombre_total_compteur = Compteur.objects.filter(contrats__cp_commune_id=cp_commune_id).count()

    # Calcul de la fin du mois actuel en utilisant pandas
    end_of_month = (
            pd.to_datetime('now')
            .to_period('M')
            .to_timestamp()
            + MonthEnd(0)
    )

    # Filtrer les contrats avec des relevés dans le mois actuel
    contrat_data = (
        Contrat.objects
        .filter(cp_commune_id=cp_commune_id)
        .annotate(releve_count=Count('num_compteur__relevecompteurs',
                                     filter=Q(num_compteur__relevecompteurs__date_releve__month=end_of_month.month)))
        .distinct()
    )

    contrat_list = list(contrat_data)

    # Calculer le nombre_relever_effectuer
    nombre_relever_effectuer = sum(1 for contrat in contrat_list if contrat.releve_count > 0)

    return JsonResponse(
        {
            'totale_anomalie': total_anomalie,
            'realise': realise,
            'nombre_total_compteur': nombre_total_compteur,
            'nombre_relever_effectuer': nombre_relever_effectuer,
        }
    )


def relever_client(request):
    compteur_id = request.GET.get('num_compteur')

    try:
        # Récupérer le compteur correspondant à l'ID fourni
        compteur = get_object_or_404(Compteur, num_compteur=compteur_id)

        # Récupérer les informations sur le compteur
        compteur_info = {
            'id': compteur.num_compteur,
            'marque': compteur.marque_compteur,
            'modele': compteur.modele_compteur,
            # Ajouter d'autres informations sur le compteur au besoin
        }

        # Récupérer le contrat associé au compteur
        contrat = get_object_or_404(Contrat, num_compteur=compteur)

        # Récupérer les informations sur le contrat
        contrat_info = {
            'id': contrat.num_contrat,  # Utiliser num_contrat au lieu de id_contrat
            'numero_contrat': contrat.num_contrat,
            'date_debut': contrat.date_debut,
            'date_fin': contrat.date_fin,
            'adresse_contrat': contrat.adresse_contrat,
            'pays_contrat': contrat.pays_contrat,
            # Ajouter d'autres informations sur le contrat au besoin
        }

        # Récupérer les informations sur le client associé au contrat
        client = contrat.client
        client_info = {
            'id': client.id_client,
            'nom': client.nom_client,
            'prenom': client.prenom_client,
            'adresse': client.adresse_client,
            'commune': client.cp_commune.commune,
            'region': client.cp_commune.region.region,
            'tephone1': client.tel1_client,
            'tephone2': client.tel2_client,
            'actif': client.compte_actif
            # Ajouter d'autres informations sur le client au besoin
        }

        # Récupérer les relevés de compteurs associés au compteur, triés par date décroissante
        releves_data = ReleveCompteur.objects.filter(num_compteur=compteur).order_by('-date_releve')

        releves_list = []
        for releve in releves_data:
            releves_list.append({
                'date_releve': releve.date_releve,
                'volume': releve.volume,
                'conso': releve.conso,
                # Ajouter d'autres informations sur le relevé au besoin
            })

        return JsonResponse({
            'compteur': compteur_info,
            'contrat': contrat_info,
            'client': client_info,
            'releves': releves_list
        })
    except Compteur.DoesNotExist:
        return JsonResponse({'error': 'Compteur non trouvé'}, status=404)
    except Contrat.DoesNotExist:
        return JsonResponse({'error': 'Contrat non trouvé'}, status=404)


class Missions(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get_liste_mission(request):
        cp_commune = request.user.cp_commune_id
        # Calcul de la fin du mois actuel en utilisant pandas
        end_of_month = pd.to_datetime('now').to_period('M').to_timestamp() + MonthEnd(0)

        contrats_commune = (
            Contrat.objects
            .filter(cp_commune_id=cp_commune)
            .select_related('client', 'num_compteur')
            .annotate(
                conso_dernier_releve=Sum('num_compteur__relevecompteurs__conso'),
                volume_dernier_releve=Sum('num_compteur__relevecompteurs__volume')
            )
        )

        for contrat in contrats_commune:
            dernier_releve = ReleveCompteur.objects.filter(num_compteur=contrat.num_compteur).aggregate(
                max_date=Max('date_releve'))
            contrat.date_releve = dernier_releve['max_date'] if dernier_releve['max_date'] else None

            # Comparaison des mois pour définir le statut
            if contrat.date_releve and contrat.date_releve.month != end_of_month.month:
                contrat.statut = 0
            else:
                contrat.statut = 1

        liste_contrats_info = [
            {
                'nom_client': contrat.client.nom_client,
                'prenom_client': contrat.client.prenom_client,
                'adresse_client': contrat.client.adresse_client,
                'num_compteur': contrat.num_compteur_id,
                'conso_dernier_releve': contrat.conso_dernier_releve,
                'volume_dernier_releve': contrat.volume_dernier_releve,
                'date_releve': contrat.date_releve,
                'statut': contrat.statut
            }
            for contrat in contrats_commune
        ]

        return liste_contrats_info

    def get(self, request):
        liste_contrats_info = self.get_liste_mission(request)
        return JsonResponse({'compteurs_liste': liste_contrats_info})

    @staticmethod
    @parser_classes((MultiPartParser, FormParser))
    def post(request):
        serializer = MissionSerializer(data=request.data)
        utilisateur = request.user.id_utilisateur

        if serializer.is_valid():
            num_compteur = serializer.validated_data.get('num_compteur')
            date_releve = serializer.validated_data.get('date_releve')
            volume = serializer.validated_data.get('volume')
            image_compteur = request.FILES.get('image_compteur')

            dernier_volume = ReleveCompteur.objects.filter(num_compteur=num_compteur).latest('date_releve')

            if dernier_volume:
                if date_releve <= dernier_volume.date_releve:
                    return JsonResponse({'erreur': "Veuillez fournir une date valide"},
                                        status=status.HTTP_400_BAD_REQUEST)
                if dernier_volume.volume > volume:
                    return JsonResponse({'erreur': "Assurez-vous de saisir les chiffres correctement et réessayez !"},
                                        status=status.HTTP_400_BAD_REQUEST)
                else:
                    conso = volume - dernier_volume.volume
            else:
                conso = volume

            releve = relever(request, dernier_volume.num_compteur_id, date_releve,
                             volume, conso, image_compteur, utilisateur)

            facture_creation(date_releve, dernier_volume.num_compteur_id, releve)

            historique = f"Relever et Facture d'un compteur {num_compteur}"
            enregistre_historique(request, historique, utilisateur)

            return JsonResponse({'enregistre': True}, status=status.HTTP_201_CREATED)

        else:
            return JsonResponse({'erreur': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


# class Facture(APIView):
#     permission_classes = [permissions.IsAuthenticated]
#
#     @staticmethod
#     def get(request):

