from django.http import JsonResponse
from rest_framework import permissions, status
from rest_framework.decorators import parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from Main_Courante.api_anomalie.serializer import MainCouranteSerializer, PhotosSerializer
from Main_Courante.models import StatutMC


class DeclareMaincourate(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        main_courantes = StatutMC.objects.all()

        main_courante_list = []
        for main_courante in main_courantes:
            main_courante_info = {
                'id': int(main_courante.main_courante_id),
                'id_mc': int(main_courante.main_courante_id),
                'type_mc': str(main_courante.main_courante.type_anomalie),
                'date_declaration': str(main_courante.main_courante.date_mc),
                'longitude_mc': str(main_courante.main_courante.longitude_mc),
                'latitude_mc': str(main_courante.main_courante.latitude_mc),
                'description_mc': str(main_courante.main_courante.description_mc),
                'client_declare': str(main_courante.main_courante.client.nom_client) if main_courante.main_courante.client_id else '',
                'cp_commune': str(main_courante.main_courante.cp_commune_id) if main_courante.main_courante.cp_commune_id else '',
                'commune': str(main_courante.main_courante.cp_commune.commune) if main_courante.main_courante.cp_commune_id else '',
                'status': 0 if main_courante.non_traite else ( 1 if main_courante.en_cours else 2 if main_courante.realise else '')
            }
            main_courante_list.append(main_courante_info)
            # print(main_courante_info)

        # Déplacer l'impression de main_courante_info à l'intérieur de la boucle for

        return JsonResponse({'main_courante_list': main_courante_list})

    @staticmethod
    @parser_classes((MultiPartParser, FormParser))
    def post(request):
        maincourante_data = request.data.copy()
        maincourante_data['utilisateur'] = request.user.id_utilisateur
        maincourante_serializer = MainCouranteSerializer(data=maincourante_data)

        if maincourante_serializer.is_valid():
            datemc = maincourante_serializer.validated_data['date_mc']
            main_courant = maincourante_serializer.save()
            main_courante_id = main_courant.pk

            photomc = request.data.get('photomc', [])
            for photo in photomc:
                photo['main_courante'] = main_courante_id
                photo_serializer = PhotosSerializer(data=photo)

                if photo_serializer.is_valid():
                    photo_serializer.save()
                else:
                    return JsonResponse({'message': photo_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            StatutMC.objects.create(
                main_courante_id=main_courante_id,
                date_status=datemc
            )
            return JsonResponse({'message': 'Données enregistrées avec succès'}, status=200)
        else:
            return JsonResponse({'message': maincourante_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
