import time
import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes

from Main_Courante.api_anomalie.serializer import MainCouranteSerializer, PhotosSerializer, SuivieSerializer
from Main_Courante.models import MainCourante, StatutMC
from Tenants.middleware import schema_use_api
from Rel_Compteur.api_utils import ApiResponse


class DeclareMaincourate(APIView):
    """API pour la gestion des anomalies (Main Courante)."""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @staticmethod
    @schema_use_api
    def get(request):
        """
        Récupère la liste des anomalies.
        """
        
        try:
            modified_since_str = request.GET.get('modified_since')
            include_sync_meta = request.GET.get('include_sync_meta', 'true').lower() == 'true'
            
            # Requête de base avec optimisations
            queryset = MainCourante.all_objects.all().select_related(
                'client', 'cp_commune', 'cp_commune__region', 'utilisateur'
            ).prefetch_related('photomcs', 'suiviemcs', 'statuts')

            if modified_since_str:
                # Delta Sync : éléments modifiés depuis la date donnée
                modified_since = parse_datetime(modified_since_str)
                if modified_since:
                    queryset = queryset.filter(updated_at__gte=modified_since)
            else:
                # Full Sync : anomalies actives uniquement
                queryset = queryset.filter(
                    Q(is_deleted=False) | Q(is_deleted__isnull=True)
                ).exclude(statuts__realise=True)

            # Filtre par commune (API utilisée par les Releveurs)
            if request.user.cp_commune:
                # Inclut les anciennes anomalies qui n'avaient pas de commune rattachée
                queryset = queryset.filter(
                    Q(cp_commune_id=request.user.cp_commune_id) | Q(cp_commune__isnull=True)
                )

            main_courante_list = []
            commentaire_global = []

            for mc in queryset:
                # Statut (On utilise list(mc.statuts.all()) pour exploiter le prefetch_related et éviter les requêtes N+1)
                statuts_list = list(mc.statuts.all())
                statut_obj = statuts_list[0] if statuts_list else None
                
                is_realise = statut_obj.realise if statut_obj else False
                is_en_cours = statut_obj.en_cours if statut_obj else False
                
                status_code = 2 if is_realise else (1 if is_en_cours else 0)

                # Commentaires/Suivis
                for suivi in mc.suiviemcs.all():
                    commentaire_global.append({
                        'id': suivi.pk,
                        'id_mc': suivi.main_courante_id,
                        'id_suivie': suivi.pk,
                        'date_suivie': suivi.date_suivie.strftime('%Y-%m-%d %H:%M'),
                        'commentaire_suivie': suivi.commentaire_suivie
                    })

                # Photos
                photo_attributes = {f'photo_anomalie_{i}': "null" for i in range(1, 6)}
                for i, photo in enumerate(mc.photomcs.all()[:5], start=1):
                    if photo.photo_anomalie:
                        photo_attributes[f'photo_anomalie_{i}'] = photo.photo_anomalie.url

                # Construction de l'objet
                main_courante_list.append({
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
                })

            # Réponse
            response_data = {
                'main_courante_list': main_courante_list,
                'commentaire': commentaire_global,
            }

            if include_sync_meta:
                return ApiResponse.sync_response(
                    data=response_data,
                    server_time=timezone.now().isoformat()
                )
            else:
                return ApiResponse.success(data=response_data)
                
        except Exception as e:
            return ApiResponse.server_error(f"Erreur serveur: {str(e)}")

    @staticmethod
    @schema_use_api
    def post(request):
        """Crée une nouvelle anomalie."""
        data = request.data
        date_declaration = data.get('date_declaration')
        type_anomalie = data.get('type_mc')
        
        if not date_declaration or not type_anomalie:
            return ApiResponse.error(
                "Les champs 'date_declaration' et 'type_mc' sont requis", 
                code="MISSING_PARAM"
            )

        try:
            with transaction.atomic():
                cp_commune = data.get('cp_commune')
                # Automatiser la commune (API utilisée par les Releveurs)
                if request.user.cp_commune:
                    cp_commune = request.user.cp_commune_id

                maincourante_data = {
                    'date_mc': date_declaration,
                    'type_anomalie': type_anomalie,
                    'longitude_mc': data.get('longitude_mc'),
                    'latitude_mc': data.get('latitude_mc'),
                    'description_mc': data.get('description_mc'),
                    'client': data.get('client_declare'),
                    'cp_commune': cp_commune,
                    'utilisateur': request.user.id_utilisateur
                }
                serializer = MainCouranteSerializer(data=maincourante_data)

                if not serializer.is_valid():
                    return ApiResponse.error("Erreur de validation", code="VALIDATION_ERROR", details=serializer.errors)

                main_courante = serializer.save()

                # Photos
                for i in range(1, 6):
                    photo_data = data.get(f'photo_anomalie_{i}')
                    if photo_data:
                        photo_serializer = PhotosSerializer(data={
                            'photo_anomalie': photo_data,
                            'main_courante': main_courante.pk
                        })
                        if not photo_serializer.is_valid():
                            return ApiResponse.error("Erreur de validation photo", code="VALIDATION_ERROR", details=photo_serializer.errors)
                        photo_serializer.save()

                StatutMC.objects.create(
                    main_courante_id=main_courante.pk,
                    date_status=date_declaration
                )
                return ApiResponse.created(data={'id': main_courante.pk}, message="Données enregistrées avec succès")

        except Exception as e:
            return ApiResponse.server_error(f"Erreur serveur: {str(e)}")


@api_view(['POST'])
@schema_use_api
@permission_classes([permissions.IsAuthenticated])
def suivie_mc(request):
    """Ajoute un suivi/commentaire à une anomalie."""
    statut = request.data.get('statut')
    id_mc = request.data.get('id_mc')
    date_suivie = request.data.get('date_suivie')
    commentaire_suivie = request.data.get('commentaire_suivie')

    if not all([statut, id_mc, date_suivie]):
        return ApiResponse.error(
            "Les champs 'statut', 'id_mc' et 'date_suivie' sont requis", 
            code="MISSING_PARAM"
        )

    try:
        with transaction.atomic():
            if int(statut) != 1:
                return ApiResponse.error("Statut non valide !", code="INVALID_PARAM")
                
            serializer = SuivieSerializer(data={
                'date_suivie': date_suivie,
                'commentaire_suivie': commentaire_suivie,
                'main_courante': id_mc,
                'utilisateur': request.user.id_utilisateur
            })

            if not serializer.is_valid():
                return ApiResponse.error("Erreur de validation", code="VALIDATION_ERROR", details=serializer.errors)

            serializer.save()
            return ApiResponse.success(message=f'Commentaire MC ({id_mc}) enregistré avec succès')

    except Exception as e:
        return ApiResponse.server_error(f"Erreur serveur: {str(e)}")