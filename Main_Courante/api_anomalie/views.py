import time

from django.db import transaction
from django.http import JsonResponse
from rest_framework import permissions
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.views import APIView
from rest_framework.decorators import api_view, parser_classes
from asgiref.sync import async_to_sync, sync_to_async
from Main_Courante.api_anomalie.serializer import MainCouranteSerializer, PhotosSerializer, SuivieSerializer
from Main_Courante.models import StatutMC, PhotoMC, SuivieMC
from Tenants.middleware import schema_use_api
import logging

logger = logging.getLogger(__name__)

class DeclareMaincourate(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @staticmethod
    @schema_use_api
    def get(request):
        start_time = time.time()
        logger.info("Début GET DeclareMaincourate")
        
        try:
            from django.utils.dateparse import parse_datetime
            from django.utils import timezone
            from Main_Courante.models import MainCourante

            # --- GESTION SYNC ---
            modified_since_str = request.GET.get('modified_since')
            include_sync_meta = request.GET.get('include_sync_meta', 'true').lower() == 'true'
            
            # On utilise all_objects pour accéder aussi aux supprimés (nécessaire pour Delta Sync)
            queryset = MainCourante.all_objects.all().select_related('client', 'cp_commune', 'cp_commune__region', 'utilisateur').prefetch_related('photomcs', 'suiviemcs', 'statuts')

            if modified_since_str:
                modified_since = parse_datetime(modified_since_str)
                if modified_since:
                    # Delta Sync : Tout ce qui a bougé (modif, création, suppression, changement statut)
                    queryset = queryset.filter(updated_at__gte=modified_since)
                    logger.info(f"Delta Sync Anomalies depuis {modified_since}")
            else:
                # Full Sync : Seulement les anomalies actives (non réalisées)
                # On exclut les réalisées pour ne pas charger tout l'historique
                # On inclut is_deleted=False OU is_deleted=NULL (données pré-migration)
                from django.db.models import Q
                queryset = queryset.filter(Q(is_deleted=False) | Q(is_deleted__isnull=True)).exclude(statuts__realise=True)

            main_courante_list = []
            commentaire_global = []

            for mc in queryset:
                # Récupération du statut (relation one-to-many mais logiquement one-to-one ici ?)
                statut_obj = mc.statuts.first()
                is_realise = statut_obj.realise if statut_obj else False
                is_en_cours = statut_obj.en_cours if statut_obj else False
                is_non_traite = statut_obj.non_traite if statut_obj else True

                # Traitement des suivis
                for suivi in mc.suiviemcs.all():
                    commentaires = {
                        'id': suivi.pk,
                        'id_mc': suivi.main_courante_id,
                        'id_suivie': suivi.pk,
                        'date_suivie': suivi.date_suivie.strftime('%Y-%m-%d %H:%M'),
                        'commentaire_suivie': suivi.commentaire_suivie
                    }
                    commentaire_global.append(commentaires)

                # Traitement des photos
                photo_attributes = {f'photo_anomalie_{i}': "null" for i in range(1, 6)}
                photos = list(mc.photomcs.all()[:5])
                for i, photo in enumerate(photos, start=1):
                    if photo.photo_anomalie:
                        photo_attributes[f'photo_anomalie_{i}'] = photo.photo_anomalie.url

                # Construction de l'objet info
                # Note: status 0=non_traite, 1=en_cours, 2=realise
                status_code = 0 
                if is_realise: status_code = 2
                elif is_en_cours: status_code = 1
                
                main_courante_info = {
                    'id': int(mc.pk),
                    'id_mc': int(mc.pk),
                    'type_mc': str(mc.type_anomalie),
                    'date_declaration': str(mc.date_mc),
                    'longitude_mc': str(mc.longitude_mc) if mc.longitude_mc else '',
                    'latitude_mc': str(mc.latitude_mc) if mc.latitude_mc else '',
                    'description_mc': str(mc.description_mc),
                    'client_declare': str(mc.client.nom_client) if mc.client else '',
                    'cp_commune': str(mc.cp_commune_id) if mc.cp_commune_id else '',
                    'commune': str(mc.cp_commune.commune) if mc.cp_commune else '',
                    'status': status_code,
                    'is_deleted': mc.is_deleted if mc.is_deleted is not None else False,
                    **photo_attributes,
                }
                main_courante_list.append(main_courante_info)

            logger.info(f"Fin GET DeclareMaincourate: {len(main_courante_list)} items en {time.time() - start_time:.2f}s")

            if include_sync_meta:
                try:
                    from Rel_Compteur.api_utils import ApiResponse
                    return ApiResponse.sync_response(
                        data={
                            'main_courante_list': main_courante_list,
                            'commentaire': commentaire_global,
                        },
                        server_time=timezone.now().isoformat()
                    )
                except Exception as api_err:
                    logger.error(f"Erreur ApiResponse: {api_err}")
                    # Fallback vers format simple
                    return JsonResponse({
                        'success': True,
                        'data': {
                            'main_courante_list': main_courante_list,
                            'commentaire': commentaire_global,
                        },
                        'sync': {'server_time': timezone.now().isoformat()}
                    })
            else:
                return JsonResponse({
                    'main_courante_list': main_courante_list,
                    'commentaire': commentaire_global,
                })
                
        except Exception as e:
            logger.error(f"Erreur dans GET DeclareMaincourate: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

    @staticmethod
    @schema_use_api
    @async_to_sync  # Ajouté pour adapter la vue asynchrone à DRF
    async def post(request):
        start_time = time.time()
        logger.info("Début POST DeclareMaincourate")

        # Récupération des données de la requête
        data = request.data
        date_declaration = data.get('date_declaration')
        type_anomalie = data.get('type_mc')
        longitude_mc = data.get('longitude_mc')
        latitude_mc = data.get('latitude_mc')
        description_mc = data.get('description_mc')
        client_declare = data.get('client_declare')
        cp_commune = data.get('cp_commune')
        photos = [data.get(f'photo_anomalie_{i}') for i in range(1, 6)]

        if not date_declaration or not type_anomalie:
            logger.error("Paramètres 'date_declaration' ou 'type_mc' manquants")
            return JsonResponse({'erreur': "Les champs 'date_declaration' et 'type_mc' sont requis"}, status=400)

        try:
            @sync_to_async
            def save_main_courante():
                with transaction.atomic():
                    maincourante_data = {
                        'date_mc': date_declaration,
                        'type_anomalie': type_anomalie,
                        'longitude_mc': longitude_mc,
                        'latitude_mc': latitude_mc,
                        'description_mc': description_mc,
                        'client': client_declare,
                        'cp_commune': cp_commune,
                        'utilisateur': request.user.id_utilisateur
                    }
                    maincourante_serializer = MainCouranteSerializer(data=maincourante_data)

                    if not maincourante_serializer.is_valid():
                        return {'error': maincourante_serializer.errors}

                    main_courant = maincourante_serializer.save()
                    main_courante_id = main_courant.pk

                    # Création des instances de PhotoMC
                    for i, photo_data in enumerate(photos, start=1):
                        if photo_data:
                            photo_instance = {
                                'photo_anomalie': photo_data,
                                'main_courante': main_courant.pk
                            }
                            photo_serializer = PhotosSerializer(data=photo_instance)
                            if not photo_serializer.is_valid():
                                return {'error': photo_serializer.errors}
                            photo_serializer.save()

                    StatutMC.objects.create(
                        main_courante_id=main_courante_id,
                        date_status=date_declaration
                    )
                    return {'success': True, 'main_courante_id': main_courante_id}

            result = await save_main_courante()
            if 'error' in result:
                logger.error(f"Erreur de validation: {result['error']}")
                return JsonResponse({'message': result['error']}, status=400)

            logger.info(f"Fin POST DeclareMaincourate: {time.time() - start_time:.2f}s")
            return JsonResponse({'message': 'Données enregistrées avec succès'}, status=200)

        except ValueError as e:
            logger.error(f"Erreur de valeur dans POST: {str(e)}")
            return JsonResponse({'erreur': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Erreur inattendue dans POST: {str(e)}", exc_info=True)
            return JsonResponse({'erreur': f"Erreur du serveur: {str(e)}"}, status=500)


@api_view(['POST'])
@schema_use_api
@async_to_sync  # Ajouté pour adapter la vue asynchrone à DRF
async def suivie_mc(request):
    start_time = time.time()
    logger.info("Début POST suivie_mc")

    statut = request.data.get('statut')
    id_mc = request.data.get('id_mc')
    date_suivie = request.data.get('date_suivie')
    commentaire_suivie = request.data.get('commentaire_suivie')

    if not all([statut, id_mc, date_suivie]):
        logger.error("Paramètres 'statut', 'id_mc' ou 'date_suivie' manquants")
        return JsonResponse({'erreur': "Les champs 'statut', 'id_mc' et 'date_suivie' sont requis"}, status=400)

    try:
        @sync_to_async
        def save_suivie():
            with transaction.atomic():
                if int(statut) == 1:
                    suivie = {
                        'date_suivie': date_suivie,
                        'commentaire_suivie': commentaire_suivie,
                        'main_courante': id_mc,
                        'utilisateur': request.user.id_utilisateur
                    }
                    suivieserialize = SuivieSerializer(data=suivie)

                    if not suivieserialize.is_valid():
                        return {'error': suivieserialize.errors}

                    suivieserialize.save()
                    return {'success': True}
                else:
                    return {'error': "Status non valide !"}

        result = await save_suivie()
        if 'error' in result:
            logger.error(f"Erreur dans suivie_mc: {result['error']}")
            return JsonResponse({'message': result['error']}, status=400)

        logger.info(f"Fin POST suivie_mc: {time.time() - start_time:.2f}s")
        return JsonResponse({'message': f'Commentaire MC ({id_mc}) enregistrées avec succès'}, status=200)

    except ValueError as e:
        logger.error(f"Erreur de valeur dans suivie_mc: {str(e)}")
        return JsonResponse({'erreur': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Erreur inattendue dans suivie_mc: {str(e)}", exc_info=True)
        return JsonResponse({'erreur': f"Erreur du serveur: {str(e)}"}, status=500)