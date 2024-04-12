from django.http import JsonResponse
from rest_framework import permissions
from rest_framework.views import APIView

from Main_Courante.models import StatutMC


class DeclareMaincourate(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
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
