from rest_framework import serializers
from .models import PatientProfile

class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = ('id', 'user', 'blood_type', 'allergies', 'emergency_contact_name', 'emergency_contact_phone', 'insurance_number', 'medical_history')