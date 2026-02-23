import time
from asyncio.log import logger

import pandas as pd
from asgiref.sync import async_to_sync, sync_to_async
from django.db import transaction
from django.db.models import Count
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from Clients.models import Contrat
from Parametre.views import enregistre_historique
from Tenants.middleware import schema_use_api
from Rel_Compteur.api_utils import ApiResponse

from .serializer import MissionSerializer
from Tasks.tasks import TaskMission, process_compteur_details, TaskFactureDetail
from Compteurs.models import Compteur, ReleveCompteur
from Facturation.models import Facture
from Facturation.views import facture_creation
from Main_Courante.models import MainCourante
from pandas.tseries.offsets import MonthEnd

from ..views import relever, ReleveMod


async def calculer_nombre_relever_effectuer(cp_commune_id):
    # Calcul de la fin du mois actuel avec pandas (synchrone, pas besoin de @sync_to_async)
    end_of_month = (
        pd.to_datetime('now')
        .to_period('M')
        .to_timestamp()
        + MonthEnd(0)
    )

    # Encapsuler les opérations synchrones à la base de données
    @sync_to_async
    def get_counts():
        # Nombre total de compteurs dans cette commune (via les contrats)
        nombre_total_compteur = Contrat.objects.filter(
            cp_commune_id=cp_commune_id
        ).count()

        # Compter les compteurs qui ont au moins un relevé ce mois-ci
        nombre_relever_effectuer = ReleveCompteur.objects.filter(
            num_compteur__contrats__cp_commune_id=cp_commune_id,
            date_releve__month=end_of_month.month,
            date_releve__year=end_of_month.year
        ).values('num_compteur').distinct().count()

        # Calcul des factures
        nombre_facture = Facture.objects.filter(
            relevecompteur__num_compteur__contrats__cp_commune_id=cp_commune_id
        ).count()

        nombre_total_facture_payer = Facture.objects.filter(
            relevecompteur__num_compteur__contrats__cp_commune_id=cp_commune_id,
            statut=True
        ).count()

        nombre_total_facture_impayer = nombre_facture - nombre_total_facture_payer

        # Calculer le nombre de compteurs restants à relever
        nombre_restant_a_relever = nombre_total_compteur - nombre_relever_effectuer

        return (
            nombre_total_compteur,
            nombre_relever_effectuer,
            nombre_restant_a_relever,
            nombre_total_facture_impayer,
            nombre_total_facture_payer
        )

    # Attendre les résultats des appels synchrones
    return await get_counts()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@schema_use_api
@async_to_sync
async def accueil(request):

    cp_commune_id = request.user.cp_commune_id

    # Encapsuler les appels synchrones à la base de données
    @sync_to_async
    def get_anomalie_counts():
        non_traites = MainCourante.objects.filter(statuts__non_traite=True).count()
        realises = MainCourante.objects.filter(statuts__realise=True).count()
        en_courss = MainCourante.objects.filter(statuts__en_cours=True).count()
        return non_traites, realises, en_courss

    # Attendre les comptes d'anomalies
    non_traite, realise, en_cours = await get_anomalie_counts()
    total_anomalie = non_traite + en_cours

    # Appeler la fonction asynchrone pour les compteurs et factures
    (
        nombre_total_compteur,
        nombre_relever_effectuer,
        nombre_restant_a_relever,
        nombre_total_facture_impayer,
        nombre_total_facture_payer
    ) = await calculer_nombre_relever_effectuer(cp_commune_id)

    response_data = {
        'non_traite': non_traite,
        'realise': realise,
        'en_cours': en_cours,
        'totale_anomalie': total_anomalie,
        'nombre_total_compteur': nombre_total_compteur,
        'nombre_relever_effectuer': nombre_relever_effectuer,
        'nombre_restant_a_relever': nombre_restant_a_relever,
        'nombre_total_facture_impayer': nombre_total_facture_impayer,
        'nombre_total_facture_payer': nombre_total_facture_payer
    }

    return JsonResponse(response_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@schema_use_api
@async_to_sync()
async def relever_client(request):
    compteur_id = request.GET.get('num_compteur')

    if not compteur_id:
        return JsonResponse({'erreur': "Le paramètre 'num_compteur' est requis"}, status=400)

    try:
        resultat = await process_compteur_details(compteur_id)
        return JsonResponse(resultat, status=200)
    except ValueError as e:
        return JsonResponse({'erreur': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'erreur': f"Erreur du serveur: {str(e)}"}, status=500)


class Missions(APIView):
    """
    API pour les missions de relevé.
    
    GET: Récupère la liste des compteurs à relever
        Paramètres optionnels:
        - modified_since: ISO datetime - Retourne uniquement les modifications après cette date (delta sync)
        - include_sync_meta: bool - Inclure les métadonnées de synchronisation (défaut: true)
    
    POST: Enregistre un nouveau relevé
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    @staticmethod
    @schema_use_api
    @async_to_sync
    async def get(request):
        """
        Récupère la liste des missions (compteurs à relever).
        
        Query params:
        - modified_since: ISO datetime - Pour la synchronisation incrémentielle
        - include_sync_meta: bool (défaut: true) - Inclure server_time et métadonnées
        - limit: int (défaut: tous) - Nombre max de résultats
        - offset: int (défaut: 0) - Décalage pour la pagination
        - status: int (0 ou 2) - Filtrer par statut (0=non-relevé, 2=relevé)
        """
        logger.info("Début get /api/missions")
        start_time = time.time()
        cp_commune = request.user.cp_commune_id
        end_of_month = pd.to_datetime('now').to_period('M').to_timestamp() + MonthEnd(0)
        
        # Paramètres de synchronisation
        modified_since_str = request.GET.get('modified_since')
        include_sync_meta = request.GET.get('include_sync_meta', 'true').lower() == 'true'
        
        # Paramètres de pagination
        limit_str = request.GET.get('limit')
        limit = int(limit_str) if limit_str else None
        offset = int(request.GET.get('offset', 0))
        
        # Paramètre de filtrage par statut
        status_str = request.GET.get('status')
        status_filter = int(status_str) if status_str in ('0', '2') else None
        
        # Parser la date de modification si fournie
        modified_since = None
        if modified_since_str:
            modified_since = parse_datetime(modified_since_str)
            if not modified_since:
                return ApiResponse.error(
                    "Format de date invalide pour 'modified_since'. Utilisez ISO 8601.",
                    code="INVALID_DATE"
                )

        try:
            # OPTIMISATION DELTA-SYNC : On délègue tout le filtre à PostgreSQL
            # en lui passant modified_since. Le résultat ne contiendra QUE les éléments modifiés.
            result = await TaskMission.process_liste_mission(
                cp_commune, 
                end_of_month,
                limit=limit,
                offset=offset,
                status_filter=status_filter,
                bypass_cache=bool(modified_since),
                modified_since=modified_since
            )
            
            if 'status' in result and result['status'] == 'error':
                return ApiResponse.error(result['message'], code="SERVER_ERROR", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            missions_list = result['liste']
            has_more = result.get('has_more', False)
            total_count = result.get('total_count', len(missions_list))
            
            logger.info(f"Fin get /api/missions (Delta Sync Optimisé SQL): {time.time() - start_time:.2f}s, {len(missions_list)} missions renvoyées")
            
            # Construire la réponse avec ou sans métadonnées de sync
            if include_sync_meta:
                return ApiResponse.sync_response(
                    data={
                        'compteurs_liste': missions_list,
                        'total_count': total_count,
                        'returned_count': len(missions_list),
                        'offset': offset,
                        'limit': limit,
                    },
                    server_time=timezone.now().isoformat(),
                    has_more=has_more
                )
            else:
                # Format de réponse original pour compatibilité
                return Response({'compteurs_liste': missions_list}, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Erreur inattendue: {str(e)}", exc_info=True)
            return ApiResponse.error(f"Erreur du serveur: {str(e)}", code="SERVER_ERROR", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @staticmethod
    @schema_use_api
    @async_to_sync
    async def post(request):
        logger.info("Début de la requête POST /api/missions")

        # Accès à request.user dans un contexte synchrone grâce à @async_to_sync
        utilisateur = request.user.id_utilisateur
        serializer = await sync_to_async(MissionSerializer)(instance=None, data=request.data)

        is_valid = await sync_to_async(serializer.is_valid)(raise_exception=False)
        if not is_valid:
            errors = await sync_to_async(lambda: serializer.errors)()
            return JsonResponse({'erreur': errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            @sync_to_async
            def process_post():
                with transaction.atomic():
                    validated_data = serializer.validated_data
                    id_releve = validated_data.get('releve_id')
                    compteur_id = validated_data.get('num_compteur')
                    date_releve = validated_data.get('date_releve')
                    volume = validated_data.get('volume')
                    image_compteur = request.FILES.get('image_compteur')

                    if id_releve is not None:
                        compteur = get_object_or_404(Compteur, relevecompteurs__id_releve=id_releve)
                        dernier_releve = compteur.relevecompteurs.order_by('-id_releve')[1]

                        if dernier_releve.volume >= volume:
                            return JsonResponse({
                                'erreur': "Assurez-vous d'envoyer les chiffres correctement et réessayez !"
                            }, status=status.HTTP_400_BAD_REQUEST)

                        if date_releve <= dernier_releve.date_releve:
                            return JsonResponse({'erreur': "Veuillez fournir une date valide"},
                                                status=status.HTTP_400_BAD_REQUEST)

                        mod_releve = ReleveMod.mod_relever_facture(id_releve, compteur, date_releve, volume,
                                                                   image_compteur, dernier_releve)
                        # La facture sera créée lors de la confirmation par le gestionnaire
                        # facture_creation(date_releve, compteur.num_compteur, mod_releve)
                        
                        # Retourner avec les métadonnées de sync
                        return {
                            'success': True,
                            'enregistre': 'Mise à jour effectuée avec succès !',
                            'id_releve': mod_releve.id_releve,
                            'sync_id': str(mod_releve.sync_id),
                            'version': mod_releve.version,
                        }

                    else:
                        if ReleveCompteur.objects.filter(num_compteur=compteur_id, date_releve=date_releve).exclude(statut_validation='REJETE').exists():
                            return JsonResponse({'erreur': "La date de relevé existe déjà dans la base de données"},
                                                status=status.HTTP_400_BAD_REQUEST)

                        dernier_volume = ReleveCompteur.objects.filter(num_compteur=compteur_id).exclude(statut_validation='REJETE').latest('date_releve')

                        if dernier_volume:
                            if date_releve <= dernier_volume.date_releve:
                                return JsonResponse({'erreur': "Veuillez fournir une date valide"},
                                                    status=status.HTTP_400_BAD_REQUEST)

                            if dernier_volume.volume > volume:
                                return JsonResponse({
                                    'erreur': "Assurez-vous de saisir les chiffres correctement et réessayez !"
                                }, status=status.HTTP_400_BAD_REQUEST)

                            conso = volume - dernier_volume.volume
                        else:
                            conso = volume

                        releve = relever(dernier_volume.num_compteur_id, date_releve,
                                         volume, conso, image_compteur, utilisateur)
                        # La facture sera créée lors de la confirmation par le gestionnaire
                        # facture_creation(date_releve, dernier_volume.num_compteur_id, releve)

                    historique = f"Relevé du compteur {compteur_id} en attente de validation"
                    enregistre_historique(historique, utilisateur)
                    
                    # Retourner avec les métadonnées de sync
                    return {
                        'success': True,
                        'enregistre': True,
                        'id_releve': releve.id_releve,
                        'sync_id': str(releve.sync_id),
                        'version': releve.version,
                    }

            result = await process_post()
            
            # Si c'est un dict de succès, retourner avec ApiResponse
            if isinstance(result, dict) and result.get('success'):
                return ApiResponse.created(data={
                    'enregistre': result.get('enregistre'),
                    'id_releve': result.get('id_releve'),
                    'sync_id': result.get('sync_id'),
                    'version': result.get('version'),
                })
            
            # Sinon c'est une JsonResponse d'erreur
            return result
        except ValueError as e:
            return ApiResponse.error(str(e), code="VALIDATION_ERROR")
        except Exception as e:
            logger.error(f"Erreur inattendue dans post: {str(e)}", exc_info=True)
            return ApiResponse.error(f"Erreur du serveur: {str(e)}", code="SERVER_ERROR", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FactureDetail(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @staticmethod
    @schema_use_api
    @async_to_sync  # Ajouté pour adapter la vue asynchrone à DRF
    async def get(request):
        id_releve = request.GET.get('id_releve')
        if not id_releve:
            logger.error("Paramètre 'id_releve' manquant dans la requête GET")
            return JsonResponse({'erreur': "Le paramètre 'id_releve' est requis"}, status=400)

        try:
            logger.info(f"Début GET pour id_releve={id_releve}")
            resultat = await TaskFactureDetail.process_facture_list(id_releve)
            logger.info(f"Fin GET pour id_releve={id_releve}")

            if resultat.get('status') == 'error':
                return JsonResponse({'erreur': resultat['message']}, status=400)
            return JsonResponse({'facture': resultat}, status=200)

        except ValueError as e:
            logger.error(f"Erreur de valeur dans GET: {str(e)}")
            return JsonResponse({'erreur': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Erreur inattendue dans GET: {str(e)}", exc_info=True)
            return JsonResponse({'erreur': f"Erreur du serveur: {str(e)}"}, status=500)

    @staticmethod
    @schema_use_api
    @async_to_sync  # Ajouté pour adapter la vue asynchrone à DRF
    async def post(request):
        id_releve = request.data.get('relevecompteur_id')
        logger.info(id_releve)
        try:
            montant_payer = float(request.data.get('paiement'))
        except (TypeError, ValueError):
            logger.error("Paramètre 'paiement' invalide ou manquant dans la requête POST")
            return JsonResponse({'erreur': "Le paramètre 'paiement' doit être un nombre valide"}, status=400)

        utilisateur = request.user.id_utilisateur

        if not id_releve:
            logger.error("Paramètre 'relevecompteur_id' manquant dans la requête POST")
            return JsonResponse({'erreur': "Le paramètre 'relevecompteur_id' est requis"}, status=400)

        try:
            logger.info(f"Début POST pour id_releve={id_releve}")
            resultat = await TaskFactureDetail.process_facture_paiement(id_releve, montant_payer, utilisateur)
            logger.info(f"Fin POST pour id_releve={id_releve}")

            if resultat.get('status') == 'error':
                return JsonResponse({'erreur': resultat['message']}, status=400)
            return JsonResponse(resultat, status=200)

        except ValueError as e:
            logger.error(f"Erreur de valeur dans POST: {str(e)}")
            return JsonResponse({'erreur': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Erreur inattendue dans POST: {str(e)}", exc_info=True)
            return JsonResponse({'erreur': f"Erreur du serveur: {str(e)}"}, status=500)


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
