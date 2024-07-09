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

        liste_contrats_info = []
        for contrat in contrats_commune:
            dernier_releve = ReleveCompteur.objects.filter(num_compteur=contrat.num_compteur).aggregate(
                max_date=Max('date_releve'))
            date_releve = dernier_releve['max_date'] if dernier_releve['max_date'] else end_of_month

            # Comparaison des mois pour définir le statut
            if date_releve and date_releve.month != end_of_month.month:
                statut = 0
            else:
                statut = 2

            dernier_releve_obj = contrat.num_compteur.relevecompteurs.order_by('id_releve').last()
            contrat_info = {
                'id': dernier_releve_obj.pk if dernier_releve_obj else '',
                'nom_client': contrat.client.nom_client,
                'prenom_client': contrat.client.prenom_client if contrat.client.prenom_client else '',
                'adresse_client': contrat.client.adresse_client,
                'num_compteur': contrat.num_compteur_id,
                'conso_dernier_releve': contrat.conso_dernier_releve,
                'volume_dernier_releve': dernier_releve_obj.volume if dernier_releve_obj else 0,
                'date_releve': dernier_releve_obj.date_releve if dernier_releve_obj else '',
                'statut': statut
            }
            liste_contrats_info.append(contrat_info)

        # Trier la liste par id_releve
        liste_contrats_info = sorted(liste_contrats_info, key=lambda x: x['id'])

        return liste_contrats_info

    def get(self, request):
        try:
            with transaction.atomic():
                liste_contrats_info = self.get_liste_mission(request)
                return JsonResponse({'compteurs_liste': liste_contrats_info})
        except ValueError as e:
            return JsonResponse({'erreur': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'erreur': f"Erreur du serveur: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @staticmethod
    @parser_classes((MultiPartParser, FormParser))
    def post(request):
        serializer = MissionSerializer(data=request.data)
        utilisateur = request.user.id_utilisateur

        if not serializer.is_valid():
            return JsonResponse({'erreur': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                id_releve = serializer.validated_data.get('releve_id')
                compteur_id = serializer.validated_data.get('num_compteur')
                date_releve = serializer.validated_data.get('date_releve')
                volume = serializer.validated_data.get('volume')
                image_compteur = request.FILES.get('image_compteur')

                if id_releve is not None:
                    compteur = get_object_or_404(Compteur, relevecompteurs__id_releve=id_releve)
                    dernier_releve = compteur.relevecompteurs.order_by('-id_releve')[1]

                    if dernier_releve.volume >= volume:
                        return JsonResponse({
                            'erreur': "Assurez-vous d'envoyer les chiffres correctement et réessayez !"
                        }, status=status.HTTP_400_BAD_REQUEST)

                    if date_releve <= dernier_releve.date_releve:
                        return JsonResponse({'erreur': "Veuillez fournir une date valide"}, status=status.HTTP_400_BAD_REQUEST)

                    mod_releve = ReleveMod.mod_relever_facture(id_releve, compteur, date_releve, volume,
                                                               image_compteur, dernier_releve)
                    facture_creation(date_releve, compteur.num_compteur, mod_releve)

                    return JsonResponse({
                        'enregistre': 'Mise à jour effectuer avec succès !'
                    }, status=status.HTTP_201_CREATED)

                else:
                    if ReleveCompteur.objects.filter(num_compteur=compteur_id, date_releve=date_releve).exists():
                        return JsonResponse({'erreur': "La date de relevé existe déjà dans la base de données"},
                                            status=status.HTTP_400_BAD_REQUEST)

                    dernier_volume = ReleveCompteur.objects.filter(num_compteur=compteur_id).latest('date_releve')

                    if dernier_volume:
                        if date_releve <= dernier_volume.date_releve:
                            return JsonResponse({'erreur': "Veuillez fournir une date valide"},
                                                status=status.HTTP_400_BAD_REQUEST)

                        if dernier_volume.volume > volume:
                            return JsonResponse({
                                'erreur': "Assurez-vous de saisir les chiffres correctement et réessayez !"
                            }, status=status.HTTP_400_BAD_REQUEST)

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
        except ValueError as e:
            return JsonResponse({'erreur': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'erreur': f"Erreur du serveur: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Details Facture #


class FactureDetail(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        id_releve = request.GET.get('id_releve')
        try:
            with transaction.atomic():
                releve = get_object_or_404(Facture, relevecompteur_id=id_releve)

                if not releve:
                    return JsonResponse({'error': 'La facture n\'a pas été trouvée pour l\'ID de relevé spécifié'}, status=404)

                montant_ht = get_object_or_404(MontantHT, facture_id=releve.id_facture)

                avoir_avant = releve.avoir_avant if releve.avoir_avant else 0.0
                avoir_utilise = releve.avoir_utilise if releve.avoir_utilise else 0.0
                restant_precedant = releve.restant_precedant if releve.restant_precedant else 0.0
                restant_nouvel = releve.restant_nouvel if releve.restant_nouvel else 0.0
                montant_total_ttc = releve.montant_total_ttc if releve.montant_total_ttc else 0.0

                if montant_total_ttc == 0.0 or restant_nouvel == 0.0 or restant_nouvel == 0.0:
                    montant_payer = 0.0
                else:
                    montant_payer = montant_total_ttc - restant_nouvel
                # Affiche le prix du selon le type de client
                typeclient = releve.num_contrat.client.type_client_id
                cp_commune = releve.num_contrat.cp_commune_id
                tarif = get_object_or_404(Tarif, cp_commune_id=cp_commune)
                if typeclient == 1:
                    tarif_m3 = tarif.prix_m3_bp
                elif typeclient == 2:
                    tarif_m3 = tarif.prix_m3_bs
                elif typeclient == 3:
                    tarif_m3 = tarif.prix_m3_k
                else:
                    tarif_m3 = 0.0

                facture = {
                    'id': int(releve.id_facture),
                    'relevecompteur_id': int(releve.relevecompteur_id),
                    'num_facture': releve.num_facture,
                    'num_compteur': int(releve.num_contrat.num_compteur_id),
                    'date_facture': releve.date_facture,
                    'total_conso_ht': montant_ht.total_conso_ht if montant_ht.total_conso_ht is not None else 0.0,
                    'tarif_m3': tarif_m3,
                    'avoir_avant': avoir_avant,
                    'avoir_utilise': avoir_utilise,
                    'restant_precedant': restant_precedant,
                    'montant_payer': montant_payer,
                    'montant_total_ttc': montant_total_ttc,
                    'statut': 'Payé' if releve.statut else 'Impayé',
                }

                return JsonResponse({'facture': facture})
        except Facture.DoesNotExist:
            return JsonResponse({'error': 'Facture non trouvé'}, status=404)
        except ValueError as e:
            return JsonResponse({'erreur': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'erreur': f"Erreur du serveur: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
