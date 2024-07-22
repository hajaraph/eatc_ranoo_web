from django.db import transaction
from django.http import JsonResponse
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from rest_framework.decorators import parser_classes, api_view
from Main_Courante.api_anomalie.serializer import MainCouranteSerializer, PhotosSerializer, SuivieSerializer
from Main_Courante.models import StatutMC, PhotoMC, SuivieMC


class DeclareMaincourate(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        main_courantes = StatutMC.objects.exclude(realise=True).all()

        main_courante_list = []
        commentaire = []

        for main_courante in main_courantes:
            photomc = PhotoMC.objects.filter(main_courante_id=main_courante.main_courante_id)

            suivie = SuivieMC.objects.filter(main_courante_id=main_courante.main_courante_id)
            if suivie.exists():
                for suivi in suivie:
                    commentaires = {
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
                if photo.photo_anomalie.url:
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
                'commune': str(main_courante.main_courante.cp_commune.commune
                               ) if main_courante.main_courante.cp_commune_id else '',
                'status': 0 if main_courante.non_traite else (1 if main_courante.en_cours else 2),
                **photo_attributes,
            }
            main_courante_list.append(main_courante_info)

        return JsonResponse(
            {
                'main_courante_list': main_courante_list,
                'commentaire': commentaire,
            }
        )

    @staticmethod
    @parser_classes((MultiPartParser, FormParser))
    def post(request):
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

        # print('status:', statut)
        # print('id:', id_mc)
        # print('date:', date_suivie)
        # print('commentaire:', commentaire_suivie)

        try:
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

                if maincourante_serializer.is_valid():
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
                            if photo_serializer.is_valid():
                                photo_serializer.save()
                            else:
                                return JsonResponse(
                                    {'message': photo_serializer.errors},
                                    status=status.HTTP_400_BAD_REQUEST
                                )

                    StatutMC.objects.create(
                        main_courante_id=main_courante_id,
                        date_status=date_declaration
                    )

                    return JsonResponse({'message': 'Données enregistrées avec succès'}, status=status.HTTP_200_OK)
                else:
                    return JsonResponse(
                        {'message': maincourante_serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        except ValueError as e:
            return JsonResponse({'erreur': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse(
                {'erreur': f"Erreur du serveur: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
def suivie_mc(request):
    statut = request.data.get('status')
    id_mc = request.data.get('id_mc')
    date_suivie = request.data.get('date_suivie')
    commentaire_suivie = request.data.get('commentaire_suivie')

    try:
        with transaction.atomic():
            if int(statut) == 1:
                suivie = {
                    'date_suivie': date_suivie,
                    'commentaire_suivie': commentaire_suivie,
                    'main_courante': id_mc,
                    'utilisateur': request.user.id_utilisateur,
                }
                suivieserialize = SuivieSerializer(data=suivie)

                if suivieserialize.is_valid():
                    suivieserialize.save()
                    return JsonResponse(
                        {'message': f'Commentaire MC ({id_mc}) enregistrées avec succès'},
                        status=status.HTTP_200_OK
                    )
                else:
                    return JsonResponse({'message': suivieserialize.errors}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return JsonResponse({'message': "Status non valide !"}, status=status.HTTP_400_BAD_REQUEST)

    except ValueError as e:
        return JsonResponse({'erreur': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return JsonResponse(
            {'erreur': f"Erreur du serveur: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
