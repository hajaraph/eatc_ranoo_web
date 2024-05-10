from rest_framework import serializers

from Main_Courante.models import MainCourante, PhotoMC


class PhotosSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoMC
        fields = '__all__'


class MainCouranteSerializer(serializers.ModelSerializer):
    anomalie_id = serializers.IntegerField(required=False)
    photo_mc = PhotosSerializer(many=True, required=False)

    class Meta:
        model = MainCourante
        fields = [
            'anomalie_id',
            'date_mc',
            'type_anomalie',
            'longitude_mc',
            'latitude_mc',
            'description_mc',
            'client',
            'cp_commune',
            'utilisateur',
            'photo_mc'
        ]
