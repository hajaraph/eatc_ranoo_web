from django.db.models import Count
from django.db.models import Q

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
                'id_relelve': releve.pk,
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
        num_facture = request.GET.get('num_facture')

class SynchronisationView(APIView):

    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, format=None):
        # Récupérer les données JSON envoyées dans la requête
        data = request.data
        utilisateurs_data = data.get('utilisateurs', [])
        missions_data = data.get('missions', [])  

        utilisateurs_synchronises = []
        missions_synchronisees = [] 

        # Synchronisation des utilisateurs
        for utilisateur_data in utilisateurs_data:
            # Logique de synchronisation pour chaque utilisateur
            utilisateur_id = utilisateur_data.get('id_utilisateurs')
            nom_utilisateur = utilisateur_data.get('nom_utilisateur')
            prenom_utilisateur = utilisateur_data.get('prenom_utilisateur')
            num_utilisateur = utilisateur_data.get('num_utilisateur')
            password = utilisateur_data.get('password')
            cp_commune = utilisateur_data.get('cp_commune')
            role_id = utilisateur_data.get('role_id')
            last_token = utilisateur_data.get('last_token')

            # Récupérer l'instance de la commune à partir du nom de la commune
            try:
                cp_commune_instance = Commune.objects.get(commune=cp_commune)
            except Commune.DoesNotExist:
                # Gérer le cas où la commune n'existe pas
                cp_commune_instance = None

            if cp_commune_instance:
                # Vérifier si l'utilisateur existe déjà dans la base de données
                try:
                    utilisateur = Utilisateur.objects.get(num_utilisateur=num_utilisateur)
                    # L'utilisateur existe déjà, mettre à jour ses données
                    utilisateur.nom_utilisateur = nom_utilisateur
                    utilisateur.prenom_utilisateur = prenom_utilisateur
                    utilisateur.password = password
                    utilisateur.cp_commune = cp_commune_instance
                    utilisateur.role_id = role_id
                    utilisateur.last_token = last_token
                    utilisateur.save()
                except Utilisateur.DoesNotExist:
                    # L'utilisateur n'existe pas, créer un nouvel utilisateur
                    utilisateur = Utilisateur(
                        id_utilisateurs=utilisateur_id,
                        nom_utilisateur=nom_utilisateur,
                        prenom_utilisateur=prenom_utilisateur,
                        num_utilisateur=num_utilisateur,
                        password=password,
                        cp_commune=cp_commune_instance,
                        role_id=role_id,
                        last_token=last_token
                    )
                    utilisateur.save()
                
                # Ajouter l'utilisateur synchronisé à la liste des utilisateurs synchronisés
                utilisateur_dict = {
                    'id_utilisateurs': utilisateur_id,
                    'nom_utilisateur': nom_utilisateur,
                    'prenom_utilisateur': prenom_utilisateur,
                    'num_utilisateur': num_utilisateur,
                    'cp_commune': cp_commune,
                    'role_id': role_id,
                    'last_token': last_token
                }
                utilisateurs_synchronises.append(utilisateur_dict)

        # Synchronisation des missions
        for mission_data in missions_data:
            # Logique de synchronisation pour chaque mission
            date_releve = mission_data.get('date_releve')
            volume = mission_data.get('volume')
            num_compteur = mission_data.get('num_compteur')
            utilisateur_id = mission_data.get('utilisateur_id')

            # Récupérer l'utilisateur associé à la mission
            try:
                utilisateur = Utilisateur.objects.get(id_utilisateur=utilisateur_id)
            except Utilisateur.DoesNotExist:
                utilisateur = None

            if utilisateur:
                # Vérifier si la mission existe déjà dans la base de données
                mission_exists = ReleveCompteur.objects.filter(date_releve=date_releve, num_compteur=num_compteur).exists()
                
                # Récupérer ou créer le compteur
                try:
                    compteur = Compteur.objects.get(num_compteur=num_compteur)
                except Compteur.DoesNotExist:
                    compteur = Compteur.objects.create(num_compteur=num_compteur)

                # Calculer la consommation
                dernier_volume = ReleveCompteur.objects.filter(num_compteur=compteur).latest('date_releve').volume if ReleveCompteur.objects.filter(num_compteur=compteur).exists() else 0
                conso = volume - dernier_volume if dernier_volume else volume

                if not mission_exists:
                    # Créer une nouvelle mission
                    mission = ReleveCompteur(
                        date_releve=date_releve,
                        volume=volume,
                        conso=conso,
                        num_compteur=compteur,
                        utilisateur=utilisateur
                    )
                    mission.save()

                    # Ajouter la mission synchronisée à la liste des missions synchronisées
                    mission_dict = {
                        'date_releve': date_releve,
                        'volume': volume,
                        'conso': conso,
                        'num_compteur': num_compteur,
                        'utilisateur_id': utilisateur_id
                    }
                    missions_synchronisees.append(mission_dict)

          # Après la synchronisation des missions, exécuter la fonction get_liste_mission
        liste_contrats_info = self.get_liste_contrats(request)

        # Retourner les utilisateurs, les missions synchronisées et la liste des contrats
        return JsonResponse(
            {
                'utilisateurs': utilisateurs_synchronises,
                'missions': missions_synchronisees,
                'liste_contrats_info': liste_contrats_info
            }
        )

    permission_classes = [permissions.IsAuthenticated]
    
    def get_liste_contrats(self, request):
        # Récupérer l'identifiant de la commune à partir de l'utilisateur actuel
        cp_commune_id = request.user.cp_commune_id
        print(cp_commune_id)
        
        # Récupérer la fin du mois actuel
        end_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)      
        print(end_of_month)

        # Récupérer les contrats de la commune avec les statistiques de relevés
        contrats_commune = self.get_contrats_commune(cp_commune_id)       
        print(contrats_commune)
        # Mettre à jour le statut des contrats en fonction de la date du dernier relevé
        for contrat in contrats_commune:
            contrat.date_releve, contrat.statut = self.get_date_releve_et_statut(contrat, end_of_month)

        # Générer la liste d'informations sur les contrats
        liste_contrats_info = self.generate_contrats_info(contrats_commune)

        return liste_contrats_info

    def get_contrats_commune(self, cp_commune_id):
        # Récupérer les contrats de la commune avec les statistiques de relevés
        contrats_commune = Contrat.objects.filter(cp_commune_id=cp_commune_id)\
            .select_related('client', 'num_compteur')\
            .annotate(
                conso_dernier_releve=Sum('num_compteur__relevecompteurs__conso'),
                volume_dernier_releve=Sum('num_compteur__relevecompteurs__volume')
            )

        return contrats_commune

    def get_date_releve_et_statut(self, contrat, end_of_month):
        # Récupérer la date du dernier relevé pour le contrat
        dernier_releve = ReleveCompteur.objects.filter(num_compteur=contrat.num_compteur)\
            .aggregate(max_date=Max('date_releve'))
        date_releve = dernier_releve['max_date'] if dernier_releve['max_date'] else None

        # Comparer les mois pour définir le statut du contrat
        statut = 1 if date_releve and date_releve.month == end_of_month.month else 0

        return date_releve, statut

    def generate_contrats_info(self, contrats_commune):
        # Générer la liste d'informations sur les contrats
        liste_contrats_info = []
        for contrat in contrats_commune:
            contrat_info = {
                'nom_client': contrat.client.nom_client,
                'prenom_client': contrat.client.prenom_client,
                'adresse_client': contrat.client.adresse_client,
                'num_compteur': contrat.num_compteur_id,
                'conso_dernier_releve': contrat.conso_dernier_releve,
                'volume_dernier_releve': contrat.volume_dernier_releve,
                'date_releve': contrat.date_releve,
                'statut': contrat.statut
            }
            liste_contrats_info.append(contrat_info)

        return liste_contrats_info