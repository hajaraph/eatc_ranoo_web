from rest_framework import serializers


class AnomalieSerializer(serializers.ModelSerializer):
    class Meta:
        model = 'Main_Courante'
        fields = '__all__'
