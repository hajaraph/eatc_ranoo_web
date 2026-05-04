from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from Login.views import authentification_requis
from Acommune.models import Province, Region, Commune
from .serializers import (
    ProvinceSerializer, 
    RegionSerializer, 
    CommuneSerializer,
    RegionCascadeSerializer,
    ProvinceCascadeSerializer
)


# Vue existante pour compatibilité
@authentification_requis
def commune_list(request, province, *args, **kwargs):
    # Récupérer les régions distinctes pour la province
    regions = Region.objects.filter(province__province=province).order_by('region').distinct('region').values('region')

    # Récupérer toutes les communes associées à cette province
    communes = Commune.objects.filter(region__province__province=province).order_by('commune').values('commune',
                                                                                                      'cp_commune',
                                                                                                      'region__region')

    return JsonResponse({
        'regions': list(regions),  # Liste des régions sans doublons
        'communes': list(communes)  # Liste des communes avec leur région associée
    })


# ===== API REST pour la cascade Province → Région → Commune =====

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def province_list_api(request):
    """
    API pour lister toutes les provinces
    GET /api/communes/provinces/
    """
    provinces = Province.objects.all().order_by('province')
    serializer = ProvinceSerializer(provinces, many=True)
    
    return Response({
        'success': True,
        'data': serializer.data,
        'count': len(serializer.data)
    })


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def regions_by_province_api(request, province_id):
    """
    API pour lister les régions d'une province spécifique
    GET /api/communes/provinces/{province_id}/regions/
    """
    try:
        province = Province.objects.get(id_province=province_id)
        regions = Region.objects.filter(province=province).order_by('region')
        serializer = RegionSerializer(regions, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': len(serializer.data),
            'province': {
                'id_province': province.id_province,
                'province': province.province
            }
        })
    except Province.DoesNotExist:
        return Response({
            'success': False,
            'error': {
                'message': 'Province non trouvée',
                'code': 'PROVINCE_NOT_FOUND'
            }
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def communes_by_region_api(request, region_id):
    """
    API pour lister les communes d'une région spécifique
    GET /api/communes/regions/{region_id}/communes/
    """
    try:
        region = Region.objects.get(id_region=region_id)
        communes = Commune.objects.filter(region=region).order_by('commune')
        serializer = CommuneSerializer(communes, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': len(serializer.data),
            'region': {
                'id_region': region.id_region,
                'region': region.region,
                'province': region.province.province
            }
        })
    except Region.DoesNotExist:
        return Response({
            'success': False,
            'error': {
                'message': 'Région non trouvée',
                'code': 'REGION_NOT_FOUND'
            }
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def communes_by_province_api(request, province_id):
    """
    API pour lister toutes les communes d'une province (cascade complète)
    GET /api/communes/provinces/{province_id}/communes/
    """
    try:
        province = Province.objects.get(id_province=province_id)
        
        # Récupérer les régions avec leurs communes
        regions = Region.objects.filter(province=province).prefetch_related('commune_set').order_by('region')
        serializer = RegionCascadeSerializer(regions, many=True)
        
        # Format pour compatibilité avec le code JavaScript existant
        regions_data = []
        communes_data = []
        
        for region_data in serializer.data:
            regions_data.append({
                'region': region_data['region']
            })
            
            for commune in region_data['communes']:
                communes_data.append({
                    'cp_commune': commune['cp_commune'],
                    'commune': commune['commune'],
                    'region__region': commune['region_name']
                })
        
        return Response({
            'success': True,
            'data': {
                'regions': regions_data,
                'communes': communes_data
            },
            'province': {
                'id_province': province.id_province,
                'province': province.province
            },
            'count': {
                'regions': len(regions_data),
                'communes': len(communes_data)
            }
        })
    except Province.DoesNotExist:
        return Response({
            'success': False,
            'error': {
                'message': 'Province non trouvée',
                'code': 'PROVINCE_NOT_FOUND'
            }
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def commune_detail_api(request, cp_commune):
    """
    API pour les détails d'une commune spécifique
    GET /api/communes/{cp_commune}/
    """
    try:
        commune = Commune.objects.get(cp_commune=cp_commune)
        serializer = CommuneSerializer(commune)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Commune.DoesNotExist:
        return Response({
            'success': False,
            'error': {
                'message': 'Commune non trouvée',
                'code': 'COMMUNE_NOT_FOUND'
            }
        }, status=status.HTTP_404_NOT_FOUND)