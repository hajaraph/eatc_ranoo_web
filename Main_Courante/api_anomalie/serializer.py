from rest_framework import serializers

from Main_Courante.models import MainCourante, PhotoMC, SuivieMC


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
            'utilisateur',
        ]

    def __init__(self, *args, **kwargs):
        super(MainCouranteSerializer, self).__init__(*args, **kwargs)
        # Rendre tous les champs non obligatoires
        for field in self.fields.values():
            field.required = False


class SuivieSerializer(serializers.ModelSerializer):
    date_suivie = serializers.DateTimeField(required=False)
    commentaire_suivie = serializers.CharField(required=False)

    class Meta:
        model = SuivieMC
        fields = [
            'date_suivie',
            'commentaire_suivie',
            'main_courante',
            'utilisateur',
        ]


class PhotosSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoMC
        fields = '__all__'
