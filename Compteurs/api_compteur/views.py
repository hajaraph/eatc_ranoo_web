from django.db.models import Count
from django.db.models import Q
import re

from django.http import JsonResponse 
from rest_framework.response import Response
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from Clients.models import Contrat
from Login.models import Utilisateur
from Clients.communes import Commune

from .serializer import MissionSerializer

from Login.api_auth.serializer import UtilisateurSerializerWithLastToken,UstilisateursSynchrone
from Compteurs.models import Compteur, ReleveCompteur
from Compteurs.views import relever
from Facturation.models import Facture, MontantHT
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
            'id': int(compteur.num_compteur),
            'marque': compteur.marque_compteur,
            'modele': compteur.modele_compteur,
            # Ajouter d'autres informations sur le compteur au besoin
        }

        # Récupérer le contrat associé au compteur
        contrat = get_object_or_404(Contrat, num_compteur=compteur)

        # Extraire le numéro du contrat
        contrat_nums = contrat.num_contrat
        num_contrat = re.search(r'\d+', contrat_nums).group()

        # Récupérer les informations sur le contrat
        contrat_info = {
            'id': int(num_contrat),  # Utiliser l'ID en tant qu'entier
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
                'id_releve': releve.pk,
                'compteur_id': int(compteur.num_compteur),
                'contrat_id': int(num_contrat),
                'client_id': int(client.id_client),
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
            compteur_id = serializer.validated_data.get('num_compteur')
            date_releve = serializer.validated_data.get('date_releve')
            volume = serializer.validated_data.get('volume')
            image_compteur = request.FILES.get('image_compteur')

            dernier_volume = ReleveCompteur.objects.filter(num_compteur=compteur_id).latest('date_releve')

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

            historique = f"Relever et Facture d'un compteur {compteur_id}"
            enregistre_historique(request, historique, utilisateur)

            return JsonResponse({'enregistre': True}, status=status.HTTP_201_CREATED)

        else:
            return JsonResponse({'erreur': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class FactureDetail(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        id_releve = request.GET.get('id_releve')

        releve = get_object_or_404(Facture, relevecompteur_id=id_releve)
        montant_ht = get_object_or_404(MontantHT, facture_id=releve.id_facture)

        facture = {
            'relevecompteur_id': releve.relevecompteur_id,
            'num_facture': releve.num_facture,
            'num_compteur': releve.num_contrat.num_compteur_id,
            'date_facture': releve.date_facture,
            'total_conso_ht': montant_ht.total_conso_ht,
            'total_taxe_co_ht': montant_ht.total_taxe_co_ht,
            'total_redevance_bs_ht': montant_ht.total_redevance_bs_ht,
            'total_redevance_fr_ht': montant_ht.total_redevance_fr_ht,
            'tarif_m3': montant_ht.tarif.prix_m3,
            'avoir_avant': releve.avoir_avant,
            'avoir_utilise': releve.avoir_utilise,
            'restant_precedant': releve.restant_precedant,
            'montant_total_ttc': releve.montant_total_ttc,
            'statut': 'Payé' if releve.statut else 'Impayé',
        }
        return JsonResponse(
            {
                'facture': facture
            }
        )

    @staticmethod
    @parser_classes((MultiPartParser, FormParser))
    def post(request):
        serializer = PaiementSerializer(data=request.data)

        if serializer.is_valid():
            id_releve = serializer.validated_data.get('relevecompteur_id')
            montant_payer = float(serializer.validated_data.get('paiement'))
            paiement(request, id_releve, montant_payer)
            return JsonResponse({'message': 'Paiement effectué avec succès'})
        else:
            return JsonResponse({'message': serializer.errors})
            
class SynchronisationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        # Récupérer les données JSON envoyées dans la requête
        data = request.data
        communeUsrs = request.user.cp_commune_id
        
        utilisateurs_data = data.get('utilisateurs', [])
        missions_data = data.get('missions', [])  

        utilisateurs_synchronises = []
        missions_synchronisees = []

        utilisateurs_sync = self.sync_utilisateur()
        utilisateurs_synchronises.extend(utilisateurs_sync)

        # Synchronisation des missions
        for mission_data in missions_data:
            mission_sync = self.sync_mission(mission_data, communeUsrs)
            missions_synchronisees.append(mission_sync)

        # Récupérer toutes les missions dans la base de données associées à l'utilisateur actuel
        toutes_missions = ReleveCompteur.objects.filter(utilisateur=request.user).values(
            'date_releve', 'volume', 'conso', 'num_compteur__num_compteur', 'utilisateur_id'
        )

        # Récupérer les détails des missions
        missions_details = self.get_missions_details(toutes_missions)

        # Récupérer les données d'accueil
        accueil_data = self.get_accueil_data(request)

        # Retourner les utilisateurs, les missions synchronisées, les détails des missions et les données d'accueil
        return JsonResponse({
            'utilisateurs': utilisateurs_synchronises,
            'missions': missions_synchronisees,
            'missions_details': missions_details,
            'acceuil': accueil_data,
        })

    def sync_utilisateur(self):
            users = Utilisateur.objects.filter(role_id=3)
            serializer = UtilisateurSerializerWithLastToken(users, many=True)
            return serializer.data
    
    
    
    
    def sync_mission(self, mission_data, communeUsrs):
        
        date_releve = mission_data.get('date_releve')
        volume = mission_data.get('volume')
        num_compteur = mission_data.get('num_compteur')
        utilisateur_id = mission_data.get('utilisateur_id')

        end_of_month = pd.to_datetime('now').to_period('M').to_timestamp() + MonthEnd(0)

        try:
            utilisateur = Utilisateur.objects.get(id_utilisateur=utilisateur_id)
        except Utilisateur.DoesNotExist:
            utilisateur = None

        if utilisateur:
            compteur, created = Compteur.objects.get_or_create(num_compteur=num_compteur)

            dernier_releve = ReleveCompteur.objects.filter(num_compteur=compteur).latest('date_releve')
            dernier_volume = dernier_releve.volume if dernier_releve else 0
            conso = volume - dernier_volume if dernier_volume else volume

            mission, created = ReleveCompteur.objects.update_or_create(
                date_releve=date_releve,
                num_compteur=compteur,
                defaults={
                    'volume': volume,
                    'conso': conso,
                    'utilisateur': utilisateur
                }
            )
            contrats_commune =  (Contrat.objects
                        .filter(cp_commune_id=communeUsrs)
                        .select_related('client', 'num_compteur')
                        .annotate(
                            conso_dernier_releve=Sum('num_compteur__relevecompteurs__conso'),
                            volume_dernier_releve=Sum('num_compteur__relevecompteurs__volume')
                        ))
            
            for contrat in contrats_commune:
                dernier_releve = ReleveCompteur.objects.filter(num_compteur=contrat.num_compteur).aggregate(
                    max_date=Max('date_releve'))
                contrat.date_releve = dernier_releve['max_date'] if dernier_releve['max_date'] else None

                # Comparaison des mois pour définir le statut
                if contrat.date_releve != None:
                    contrat.statut = 1
                else:
                    contrat.statut = 0
            print(contrat)
            mission_dict = {
                'utilisateur_id': utilisateur_id,
                'nom_client': contrat.client.nom_client,
                'prenom_client': contrat.client.prenom_client,
                'adresse_client': contrat.client.adresse_client,
                'num_compteur': contrat.num_compteur_id,
                'conso_dernier_releve': contrat.conso_dernier_releve,
                'volume_dernier_releve': contrat.volume_dernier_releve,
                'date_releve': contrat.date_releve,
                'statut': contrat.statut
            }
            return mission_dict


    def get_missions_details(self, toutes_missions):
        missions_details = []
        for mission in toutes_missions:
            compteur_id = mission['num_compteur__num_compteur']
            compteur = get_object_or_404(Compteur, num_compteur=compteur_id)
            contrat = get_object_or_404(Contrat, num_compteur=compteur)
            client = contrat.client
            releves_data = ReleveCompteur.objects.filter(num_compteur=compteur).order_by('-date_releve')
            releves_list = []
            for releve in releves_data:
                releves_list.append({
                    'id_relelve': releve.pk,
                    'date_releve': releve.date_releve,
                    'volume': releve.volume,
                    'conso': releve.conso,
                })
            missions_details.append({
                'compteur': {
                    'id': compteur.num_compteur,
                    'marque': compteur.marque_compteur,
                    'modele': compteur.modele_compteur,
                },
                'contrat': {
                    'id': contrat.num_contrat,
                    'numero_contrat': contrat.num_contrat,
                    'date_debut': contrat.date_debut,
                    'date_fin': contrat.date_fin,
                    'adresse_contrat': contrat.adresse_contrat,
                    'pays_contrat': contrat.pays_contrat,
                },
                'client': {
                    'id': client.id_client,
                    'nom': client.nom_client,
                    'prenom': client.prenom_client,
                    'adresse': client.adresse_client,
                    'commune': client.cp_commune.commune,
                    'region': client.cp_commune.region.region,
                    'tephone1': client.tel1_client,
                    'tephone2': client.tel2_client,
                    'actif': client.compte_actif
                },
                'releves': releves_list
            })
        return missions_details

    def get_accueil_data(self, request):
        cp_commune_id = request.user.cp_commune_id
        non_traite = MainCourante.objects.filter(statuts__non_traite=True).count()
        realise = MainCourante.objects.filter(statuts__realise=True).count()
        total_anomalie = non_traite + realise
        nombre_total_compteur = Compteur.objects.filter(contrats__cp_commune_id=cp_commune_id).count()

        end_of_month = (
                pd.to_datetime('now')
                .to_period('M')
                .to_timestamp()
                + MonthEnd(0)
        )

        contrat_data = (
            Contrat.objects
            .filter(cp_commune_id=cp_commune_id)
            .annotate(releve_count=Count('num_compteur__relevecompteurs',
                                        filter=Q(num_compteur__relevecompteurs__date_releve__month=end_of_month.month)))
            .distinct()
        )

        contrat_list = list(contrat_data)
        nombre_relever_effectuer = sum(1 for contrat in contrat_list if contrat.releve_count > 0)
        
        accueil = {
                'totale_anomalie': total_anomalie,
                'realise': realise,
                'nombre_total_compteur': nombre_total_compteur,
                'nombre_relever_effectuer': nombre_relever_effectuer,
            }
        return accueil
