from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from Acommune.models import Province, Region, Commune
from .serializers import (
    ProvinceSerializer, 
    RegionSerializer, 
    CommuneSerializer,
)
from Rel_Compteur.api_utils import ApiResponse


# ============================================
# API REST pour la gestion des communes
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def province_list_api(request):
    """
    API pour lister toutes les provinces
    
    GET /api/commune/provinces/
    
    Returns:
        - Liste de toutes les provinces avec id et nom
    """
    try:
        provinces = Province.objects.all().order_by('province')
        
        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 50
        result_page = paginator.paginate_queryset(provinces, request)

        return ApiResponse.success(
            data={
                'results': ProvinceSerializer(result_page, many=True).data,
                'count': paginator.page.paginator.count,
                'next': paginator.get_next_link(),
                'previous': paginator.get_previous_link(),
            },
            message="Liste des provinces récupérée avec succès"
        )
    except Exception as e:
        return ApiResponse.error(
            f"Erreur lors de la récupération des provinces: {str(e)}",
            code="PROVINCE_LIST_ERROR",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def regions_by_province_api(request, province_id):
    """
    API pour lister les régions d'une province spécifique
    
    GET /api/commune/provinces/{province_id}/regions/
    
    Params:
        - province_id: ID de la province
        
    Returns:
        - Liste des régions de la province avec id et nom
    """
    try:
        # Vérifier si la province existe
        try:
            province = Province.objects.get(id_province=province_id)
        except Province.DoesNotExist:
            return ApiResponse.error(
                "Province non trouvée",
                code="PROVINCE_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND
            )
        
        regions = Region.objects.filter(province=province).order_by('region')
        
        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 50
        result_page = paginator.paginate_queryset(regions, request)

        return ApiResponse.success(
            data={
                'results': RegionSerializer(result_page, many=True).data,
                'count': paginator.page.paginator.count,
                'next': paginator.get_next_link(),
                'previous': paginator.get_previous_link(),
            },
            message=f"Liste des régions de la province '{province.province}' récupérée avec succès"
        )
    except Exception as e:
        return ApiResponse.error(
            f"Erreur lors de la récupération des régions: {str(e)}",
            code="REGIONS_LIST_ERROR",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def communes_by_region_api(request, region_id):
    """
    API pour lister les communes d'une région spécifique
    
    GET /api/commune/regions/{region_id}/communes/
    
    Params:
        - region_id: ID de la région
        
    Returns:
        - Liste des communes de la région avec id et nom
    """
    try:
        # Vérifier si la région existe
        try:
            region = Region.objects.get(id_region=region_id)
        except Region.DoesNotExist:
            return ApiResponse.error(
                "Région non trouvée",
                code="REGION_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND
            )
        
        communes = Commune.objects.filter(region=region).order_by('commune')
        
        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 50
        result_page = paginator.paginate_queryset(communes, request)

        return ApiResponse.success(
            data={
                'results': CommuneSerializer(result_page, many=True).data,
                'count': paginator.page.paginator.count,
                'next': paginator.get_next_link(),
                'previous': paginator.get_previous_link(),
            },
            message=f"Liste des communes de la région '{region.region}' récupérée avec succès"
        )
    except Exception as e:
        return ApiResponse.error(
            f"Erreur lors de la récupération des communes: {str(e)}",
            code="COMMUNES_LIST_ERROR",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def communes_by_province_api(request, province_id):
    """
    API pour lister toutes les communes d'une province (cascade complète)
    
    GET /api/commune/provinces/{province_id}/communes/
    
    Params:
        - province_id: ID de la province
        
    Returns:
        - Liste des communes avec leurs régions associées
    """
    try:
        # Vérifier si la province existe
        try:
            province = Province.objects.get(id_province=province_id)
        except Province.DoesNotExist:
            return ApiResponse.error(
                "Province non trouvée",
                code="PROVINCE_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND
            )
        
        # Récupérer les régions avec leurs communes
        regions = Region.objects.filter(province=province).prefetch_related('commune_set').order_by('region')
        
        # Formater les données pour correspondre au format attendu par le frontend
        regions_data = []
        communes_data = []
        
        for region in regions:
            regions_data.append({
                'region': region.region
            })
            
            for commune in region.commune_set.all():
                communes_data.append({
                    'cp_commune': commune.cp_commune,
                    'commune': commune.commune,
                    'region__region': region.region
                })
        
        return ApiResponse.success(
            data={
                'regions': regions_data,
                'communes': communes_data
            },
            message=f"Liste des communes de la province '{province.province}' récupérée avec succès"
        )
    except Exception as e:
        return ApiResponse.error(
            f"Erreur lors de la récupération des communes: {str(e)}",
            code="COMMUNES_LIST_ERROR",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def commune_detail_api(request, cp_commune):
    """
    API pour les détails d'une commune spécifique
    
    GET /api/commune/communes/{cp_commune}/
    
    Params:
        - cp_commune: Code postal de la commune
        
    Returns:
        - Détails complets de la commune
    """
    try:
        # Vérifier si la commune existe
        try:
            commune = Commune.objects.get(cp_commune=cp_commune)
        except Commune.DoesNotExist:
            return ApiResponse.error(
                "Commune non trouvée",
                code="COMMUNE_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND
            )
        
        return ApiResponse.success(
            data=CommuneSerializer(commune).data,
            message=f"Détails de la commune '{commune.commune}' récupérés avec succès"
        )
    except Exception as e:
        return ApiResponse.error(
            f"Erreur lors de la récupération des détails de la commune: {str(e)}",
            code="COMMUNE_DETAIL_ERROR",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
