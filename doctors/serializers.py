from rest_framework import serializers
from .models import DoctorProfile

class DoctorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorProfile
        fields = ('id', 'user', 'specialization', 'license_number', 'years_of_experience', 'bio', 'consultation_fee', 'available_days', 'is_avaiable')