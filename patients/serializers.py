from rest_framework import serializers
from .models import PatientProfile, Prescription

class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = ('id', 'user', 'blood_type', 'allergies', 'emergency_contact_name', 'emergency_contact_phone', 'insurance_number', 'medical_history')


class PrescriptionSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Prescription
        fields = ('id', 'medication_name', 'dosage', 'frequency', 'duration', 'status', 'notes', 'prescribed_date', 'doctor_name')
    
    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.get_full_name()}"

class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = ('id','hospital_number', 'blood_type', 'allergies', 'emergency_contact_name', 'emergency_contact_phone', 'insurance_number', 'medical_history')
        read_only_fields = ('hospital_number', )