from rest_framework import serializers
from .models import Appointment
from accounts.models import User

class DoctorBriefSerializer(serializers.ModelSerializer):
    specialization = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'specialization', 'profile_picture')
    
    def get_specialization(self, obj):
        try:
            return obj.doctor_profile.specialization
        except:
            return ''
    def get_profile_picture(self, obj):
        request = self.context.get('request')
        if obj.profile_picture and request:
            return request.build_absolute_uri(obj.profile_picture.url)
        return None

class AppointmentSerializer(serializers.ModelSerializer):
    doctor = DoctorBriefSerializer(read_only=True)
    doctor_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role='doctor'), source='doctor', write_only=True)

    class Meta:
        model = Appointment
        fields = (
            'id', 'doctor', 'doctor_id', 'appointment_date',
            'appointment_time', 'location', 'status', 'reason', 'notes'
        )
        read_only_fields = ('status')