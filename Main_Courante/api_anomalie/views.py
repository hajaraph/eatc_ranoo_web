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

        # Récupérer les données directement (synchrone)
        main_courantes = StatutMC.objects.exclude(realise=True).all()
        main_courante_list = []
        commentaire = []

        for main_courante in main_courantes:
            photomc = PhotoMC.objects.filter(main_courante_id=main_courante.main_courante_id)
            suivie = SuivieMC.objects.filter(main_courante_id=main_courante.main_courante_id)

            if suivie:
                for suivi in suivie:
                    commentaires = {
                        'id': suivi.pk,
                        'id_mc': suivi.main_courante_id,
                        'id_suivie': suivi.pk,
                        'date_suivie': suivi.date_suivie.strftime('%Y-%m-%d %H:%M'),
                        'commentaire_suivie': suivi.commentaire_suivie
                    }
                    commentaire.append(commentaires)

            # Initialiser les attributs photo_anomalie_1 à photo_anomalie_5 à None
            photo_attributes = {f'photo_anomalie_{i}': "null" for i in range(1, 6)}

            # Remplir les attributs avec les URLs des photos disponibles
            for i, photo in enumerate(photomc[:5], start=1):
                if photo.photo_anomalie:
                    photo_attributes[f'photo_anomalie_{i}'] = photo.photo_anomalie.url

            main_courante_info = {
                'id': int(main_courante.main_courante_id),
                'id_mc': int(main_courante.main_courante_id),
                'type_mc': str(main_courante.main_courante.type_anomalie),
                'date_declaration': str(main_courante.main_courante.date_mc),
                'longitude_mc': str(main_courante.main_courante.longitude_mc),
                'latitude_mc': str(main_courante.main_courante.latitude_mc),
                'description_mc': str(main_courante.main_courante.description_mc),
                'client_declare': str(
                    main_courante.main_courante.client.nom_client) if main_courante.main_courante.client_id else '',
                'cp_commune': str(
                    main_courante.main_courante.cp_commune_id) if main_courante.main_courante.cp_commune_id else '',
                'commune': str(
                    main_courante.main_courante.cp_commune.commune) if main_courante.main_courante.cp_commune_id else '',
                'status': 0 if main_courante.non_traite else (1 if main_courante.en_cours else 2),
                **photo_attributes,
            }
            main_courante_list.append(main_courante_info)

        response = JsonResponse({
            'main_courante_list': main_courante_list,
            'commentaire': commentaire,
        })

        logger.info(f"Fin GET DeclareMaincourate: {time.time() - start_time:.2f}s")
        return response

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