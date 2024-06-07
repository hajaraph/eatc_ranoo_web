from rest_framework import serializers

from Main_Courante.models import MainCourante, PhotoMC, SuivieMC


class MainCouranteSerializer(serializers.ModelSerializer):
    status = serializers.IntegerField(required=True)

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


class SuivieSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuivieMC
        fields = [
            'date_suivie',
            'commentaire_suivie',
            'main_courante'
        ]


class PhotosSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoMC
        fields = '__all__'
