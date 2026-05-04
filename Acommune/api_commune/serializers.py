from rest_framework import serializers
from ..models import Province, Region, Commune


class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ['id_province', 'province']


class RegionSerializer(serializers.ModelSerializer):
    province_name = serializers.CharField(source='province.province', read_only=True)
    
    class Meta:
        model = Region
        fields = ['id_region', 'region', 'province', 'province_name']


class CommuneSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source='region.region', read_only=True)
    province_name = serializers.CharField(source='region.province.province', read_only=True)
    
    class Meta:
        model = Commune
        fields = ['cp_commune', 'commune', 'region', 'region_name', 'province_name']


class RegionCascadeSerializer(serializers.ModelSerializer):
    """Serializer pour les régions avec leurs communes associées"""
    communes = CommuneSerializer(many=True, read_only=True)
    
    class Meta:
        model = Region
        fields = ['id_region', 'region', 'province', 'communes']


class ProvinceCascadeSerializer(serializers.ModelSerializer):
    """Serializer pour les provinces avec leurs régions et communes"""
    regions = RegionCascadeSerializer(many=True, read_only=True)
    
    class Meta:
        model = Province
        fields = ['id_province', 'province', 'regions']
