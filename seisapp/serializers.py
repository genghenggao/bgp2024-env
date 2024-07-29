from rest_framework import serializers
from .models import GeoDiskIn

class GeoDiskInSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeoDiskIn
        fields = '__all__'
