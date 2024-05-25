from django.http import JsonResponse
from rest_framework import permissions, status
from rest_framework.decorators import parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from Main_Courante.api_anomalie.serializer import MainCouranteSerializer, PhotosSerializer
from Main_Courante.models import StatutMC, PhotoMC
 

class DeclareMaincourate(APIView):
    
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        main_courantes = StatutMC.objects.all()

        main_courante_list = []
        for main_courante in main_courantes:
            photomc = PhotoMC.objects.filter(main_courante_id=main_courante.main_courante_id)

            # Initialiser les attributs photo_anomalie_1 à photo_anomalie_5 à None
            photo_attributes = {f'photo_anomalie_{i+1}': "null" for i in range(5)}

            # Remplir les attributs avec les URLs des photos disponibles
            for i, photo in enumerate(photomc[:5]):
                if photo.photo_anomalie.url:
                    photo_attributes[f'photo_anomalie_{i+1}'] = photo.photo_anomalie.url

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
                'status': 0 if main_courante.non_traite else (1 if main_courante.en_cours else 2 if main_courante.realise else 3 ),
                **photo_attributes,
            }
            main_courante_list.append(main_courante_info)

        return JsonResponse({'main_courante_list': main_courante_list})


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

        print('date_declaration:', date_declaration)
        print('type_anomalie:', type_anomalie)
        print('longitude_mc:', longitude_mc)
        print('latitude_mc:', latitude_mc)
        print('description_mc:', description_mc)
        print('client_declare:', client_declare)
        print('cp_commune:', cp_commune)
        print('photos:', photos)


        # Création de l'instance MainCourante
        maincourante_data = {
            'date_mc': date_declaration,
            'type_anomalie': type_anomalie,
            'longitude_mc': longitude_mc,
            'latitude_mc': latitude_mc, 
            'description_mc': description_mc,
            'client': client_declare,
            'cp_commune': cp_commune,
            'utilisateur': request.user.id_utilisateur  # Assurez-vous d'avoir l'utilisateur actuel ici
        }
        maincourante_serializer = MainCouranteSerializer(data=maincourante_data)

        if maincourante_serializer.is_valid():
            main_courant = maincourante_serializer.save()  # Crée le MainCourant
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
                        return JsonResponse({'message': photo_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            # Création de l'instance de StatutMC
            StatutMC.objects.create(
                main_courante_id=main_courante_id,
                date_status=date_declaration
            )

            return JsonResponse({'message': 'Données enregistrées avec succès'}, status=status.HTTP_200_OK)
        else:
            return JsonResponse({'message': maincourante_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



