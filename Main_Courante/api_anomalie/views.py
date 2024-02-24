from django.http import JsonResponse
from rest_framework import permissions
from rest_framework.views import APIView

from Main_Courante.models import StatutMC


class DeclareMaincourate(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def get(request):
        main_courantes = StatutMC.objects.all()

        main_courante_list = [
            {
                'id_mc': main_courante.main_courante_id,
                'type_mc': main_courante.main_courante.type_anomalie,
                'date_declaration': main_courante.main_courante.date_mc,
                'longitude_mc': main_courante.main_courante.longitude_mc,
                'latitude_mc': main_courante.main_courante.latitude_mc,
                'description_mc': main_courante.main_courante.description_mc,

                'client_declare': main_courante.main_courante.client.nom_client
                if main_courante.main_courante.client_id else '',

                'cp_commune': main_courante.main_courante.cp_commune_id
                if main_courante.main_courante.cp_commune_id else '',
                'commune': main_courante.main_courante.cp_commune.commune
                if main_courante.main_courante.cp_commune_id else '',

                'status': 'Non traiter' if main_courante.non_traite else
                (
                    'En Cours' if main_courante.en_cours else
                    'Realise' if main_courante.realise else ''
                )
            }
            for main_courante in main_courantes
        ]

        return JsonResponse(
            {
                'main_courante_list': main_courante_list
            }
        )


