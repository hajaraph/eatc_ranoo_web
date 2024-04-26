from rest_framework import serializers

from Main_Courante.models import MainCourante, PhotoMC


class MainCouranteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainCourante
        fields = [
            'date_mc',
            'type_anomalie',
            'longitude_mc',
            'latitude_mc',
            'description_mc',
            'client',
            'cp_commune',
            'utilisateur'
        ]


class PhotosSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoMC
        fields = '__all__'
