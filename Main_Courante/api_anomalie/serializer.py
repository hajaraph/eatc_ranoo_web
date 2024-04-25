from rest_framework import serializers


class AnomalieSerializer(serializers.ModelSerializer):
    class Meta:
        model = 'Main_Courante'
        fields = '__all__'


class MainCouranteSerializer(serializers.ModelSerializer):
    class Meta:
        model = 'Main_Courante'
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
        model = 'PhotoMC'
        fields = '__all__'
