import re
import pandas as pd
from django.db import transaction
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
from Login.models import Utilisateur

from .serializer import MissionSerializer, PaiementSerializer, FactureSerializer

from Login.api_auth.serializer import UtilisateurSerializerWithLastToken
from Compteurs.models import Compteur, ReleveCompteur
from Compteurs.views import relever, ReleveMod
from Facturation.models import Facture, MontantHT, Tarif
from Facturation.views import facture_creation, paiement
from Main_Courante.models import MainCourante
from django.db.models import Sum, Max
from pandas.tseries.offsets import MonthEnd
from Parametre.views import enregistre_historique


def calculer_nombre_relever_effectuer(cp_commune_id):
    # Calcul du nombre total de compteurs
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

    return nombre_total_compteur, nombre_relever_effectuer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def accueil(request):
    cp_commune_id = request.user.cp_commune_id
    non_traite = MainCourante.objects.filter(statuts__non_traite=True).count()
    realise = MainCourante.objects.filter(statuts__realise=True).count()
    en_cours = MainCourante.objects.filter(statuts__en_cours=True).count()
    total_anomalie = non_traite + en_cours

    nombre_total_facture_impayer = Facture.objects.filter(
        relevecompteur__num_compteur__contrats__cp_commune_id=cp_commune_id,
        statut=False
    ).count()

    nombre_total_facture_payer = Facture.objects.filter(
        relevecompteur__num_compteur__contrats__cp_commune_id=cp_commune_id,
        statut=True
    ).count()
    nombre_total_facture_impayer -= nombre_total_facture_payer
    nombre_total_facture_payer -= nombre_total_facture_payer
    
    nombre_total_compteur, nombre_relever_effectuer = calculer_nombre_relever_effectuer(cp_commune_id)

    # Soustraire le nombre de relevés effectués du nombre total de compteurs
    nombre_total_compteur -= nombre_relever_effectuer
    nombre_relever_effectuer -= nombre_relever_effectuer 

    return JsonResponse(
        {
            'non_traite': non_traite,
            'realise': realise,
            'en_cours': en_cours,
            'totale_anomalie': total_anomalie,
            'nombre_total_compteur': nombre_total_compteur,
            'nombre_relever_effectuer': nombre_relever_effectuer,
            'nombre_total_facture_impayer': nombre_total_facture_impayer,
            'nombre_total_facture_payer': nombre_total_facture_payer
        }
    )


def relever_client(request):
    compteur_id = request.GET.get('num_compteur')

    try:
        with transaction.atomic():
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
                'prenom': client.prenom_client if client.prenom_client else '',
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
                releve_dict = {
                    'id': int(releve.id_releve),
                    'id_releve': int(releve.id_releve),
                    'compteur_id': int(compteur.num_compteur),
                    'contrat_id': int(num_contrat),
                    'client_id': int(client.id_client),
                    'date_releve': releve.date_releve,
                    'volume': releve.volume,
                    'conso': releve.conso,
                    'image_compteur': releve.image_compteur.url if releve.image_compteur else 'null',
                    # Ajouter d'autres informations sur le relevé au besoin
                }

                # Récupérer la facture associée au relevé
                facture = Facture.objects.filter(relevecompteur=releve).first()
                if facture:
                    # Si une facture est associée, enregistrer le statut de la facture dans le dictionnaire
                    releve_dict['etatFacture'] = 'Payé' if facture.statut else 'Impayé'
                else:
                    # Si aucune facture n'est associée, enregistrer "Pas de facture"
                    releve_dict['etatFacture'] = 'Pas de facture'

                releves_list.append(releve_dict)

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
    except ValueError as e:
        return JsonResponse({'erreur': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return JsonResponse({'erreur': f"Erreur du serveur: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class Missions(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod 
    def get_liste_mission(request):
        cp_commune = request.user.cp_commune_id
        end_of_month = pd.to_datetime('now').to_period('M').to_timestamp() + MonthEnd(0)

        contrats_commune = (
            Contrat.objects
            .filter(cp_commune_id=cp_commune)
            .select_related('client', 'num_compteur')
            .annotate(
                conso_dernier_releve=Sum('num_compteur__relevecompteurs__conso'),
            )
        )

        for contrat in contrats_commune: 
            dernier_releve = ReleveCompteur.objects.filter(num_compteur=contrat.num_compteur).order_by('date_releve').last()
            if dernier_releve:
                contrat.date_releve = dernier_releve.date_releve
                if dernier_releve.date_releve.month == datetime.now().month and dernier_releve.date_releve.year == datetime.now().year:
                    contrat.statut = 2
                else:
                    contrat.statut = 0
            elif contrat.date_releve and contrat.date_releve.month != end_of_month.month:
                contrat.statut = 0
            else: 
                contrat.statut = 0

        liste_contrats_info = []

        for contrat in contrats_commune:
            dernier_releve = contrat.num_compteur.relevecompteurs.order_by('date_releve').last()
            contrat_info = {
                'id': dernier_releve.pk if dernier_releve else None,
                'nom_client': contrat.client.nom_client,
                'prenom_client': contrat.client.prenom_client,
                'adresse_client': contrat.client.adresse_client,
                'num_compteur': contrat.num_compteur_id,
                'conso_dernier_releve': contrat.conso_dernier_releve,
                'volume_dernier_releve': dernier_releve.volume if dernier_releve else None,
                'date_releve': dernier_releve.date_releve if dernier_releve else None,
                'statut': contrat.statut
            }
            liste_contrats_info.append(contrat_info)

        return liste_contrats_info

    def get(self, request):
        liste_contrats_info = self.get_liste_mission(request)
        return JsonResponse({'compteurs_liste': liste_contrats_info})



    @staticmethod
    @parser_classes((MultiPartParser, FormParser))
    def post(request):
        # Imprimer les données reçues dans la requête
        serializerpaiement = PaiementSerializer(data=request.data)
        serializerrelever = FactureSerializer(data=request.data)

        try:
            with transaction.atomic():
                if serializerpaiement.is_valid() and serializerrelever.is_valid():
                    id_releve = request.data.get('relevecompteur_id')
                    montant_payer = float(request.data.get('paiement'))
                    utilisateur_id = request.user.id_utilisateur

                    # Vérifier si le paiement est supérieur ou égal à 0.1
                    if montant_payer >= 0.1:
                        # Imprimer les données extraites et validées
                        print("ID Relevé :", id_releve)
                        print("Montant à payer :", montant_payer)
                        print("ID Utilisateur :", utilisateur_id)

                        # Appeler la fonction paiement et imprimer le résultat
                        resultat_paiement = paiement(request, id_releve, montant_payer, utilisateur_id)
                        print("Résultat du paiement :", resultat_paiement)

                        return JsonResponse({'message': 'Paiement effectué avec succès !'})
                    else:
                        return JsonResponse({'message': 'Le montant du paiement doit être supérieur ou égal à 0.1.'},
                                            status=400)
                else:
                    return JsonResponse({
                        'message_paiement': serializerpaiement.errors,
                        'message_releve': serializerrelever.errors
                    })
        except ValueError as e:
            return JsonResponse({'erreur': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'erreur': f"Erreur du serveur: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_missions_details(toutes_missions):
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


class SynchronisationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        # Récupérer les données JSON envoyées dans la requête
        data = request.data
        commune_users = request.user.cp_commune_id

        utilisateurs_data = data.get('utilisateurs', [])
        missions_data = data.get('missions', [])

        utilisateurs_synchronises = []
        missions_synchronisees = []

        utilisateurs_sync = self.sync_utilisateur()
        utilisateurs_synchronises.extend(utilisateurs_sync)

        # Synchronisation des missions
        for mission_data in missions_data:
            mission_sync = self.sync_mission(mission_data, commune_users)
            missions_synchronisees.append(mission_sync)

        # Récupérer toutes les missions dans la base de données associées à l'utilisateur actuel
        toutes_missions = ReleveCompteur.objects.filter(utilisateur=request.user).values(
            'date_releve', 'volume', 'conso', 'num_compteur__num_compteur', 'utilisateur_id'
        )

        # Récupérer les détails des missions
        missions_details = get_missions_details(toutes_missions)

        # Récupérer les données d'accueil
        accueil_data = self.get_accueil_data(request)

        # Retourner les utilisateurs, les missions synchronisées, les détails des missions et les données d'accueil
        return JsonResponse({
            'utilisateurs': utilisateurs_synchronises,
            'missions': missions_synchronisees,
            'missions_details': missions_details,
            'acceuil': accueil_data,
        })

    @staticmethod
    def sync_utilisateur():
        users = Utilisateur.objects.filter(role_id=3)
        serializer = UtilisateurSerializerWithLastToken(users, many=True)
        return serializer.data

    @staticmethod
    def sync_mission(mission_data, commune_usrs):

        # date_releve = mission_data.get('date_releve')
        volume = mission_data.get('volume')
        num_compteur = mission_data.get('num_compteur')
        utilisateur_id = mission_data.get('utilisateur_id')

        # end_of_month = pd.to_datetime('now').to_period('M').to_timestamp() + MonthEnd(0)

        try:
            utilisateur = Utilisateur.objects.get(id_utilisateur=utilisateur_id)
        except Utilisateur.DoesNotExist:
            utilisateur = None

        if utilisateur:
            compteur, created = Compteur.objects.get_or_create(num_compteur=num_compteur)

            dernier_releve = ReleveCompteur.objects.filter(num_compteur=compteur).latest('date_releve')
            dernier_volume = dernier_releve.volume if dernier_releve else 0
            conso = volume - dernier_volume if dernier_volume else volume

            contrats_commune = Contrat.objects.filter(cp_commune_id=commune_usrs).select_related(
                'client', 'num_compteur'
            ).annotate(
                conso_dernier_releve=Sum('num_compteur__relevecompteurs__conso'),
                volume_dernier_releve=Sum('num_compteur__relevecompteurs__volume')
            )
            mission_dicts = []
            for contrat in contrats_commune:
                dernier_releve = ReleveCompteur.objects.filter(num_compteur=contrat.num_compteur).aggregate(
                    max_date=Max('date_releve'))
                contrat.date_releve = dernier_releve['max_date'] if dernier_releve['max_date'] else None
                # Comparaison des mois pour définir le statut
                if contrat.date_releve is not None:
                    contrat.statut = 1
                else:
                    contrat.statut = 0
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
                mission_dicts.append(mission_dict)

            return mission_dicts

    @staticmethod
    def get_accueil_data(request):
        cp_commune_id = request.user.cp_commune_id
        non_traite = MainCourante.objects.filter(statuts__non_traite=True).count()
        realise = MainCourante.objects.filter(statuts__realise=True).count()
        total_anomalie = non_traite + realise

        nombre_total_compteur, nombre_relever_effectuer = calculer_nombre_relever_effectuer(cp_commune_id)

        accueils = {
            'totale_anomalie': total_anomalie,
            'realise': realise,
            'nombre_total_compteur': nombre_total_compteur,
            'nombre_relever_effectuer': nombre_relever_effectuer,
        }
        return accueils
