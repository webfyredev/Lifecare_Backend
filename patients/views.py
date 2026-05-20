from rest_framework.views import APIView
from rest_framework.response import Response
from accounts.permissions import IsPatient
from appointments.models import Appointment
from django.utils import timezone
from .models import Prescription

class PatientDashboardView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        patient = request.user
        today = timezone.now().date()
        upcoming_appointments = Appointment.objects.filter(patient=patient, status__in=['pending', 'confirmed'], appointment_date__gte=today).select_related('doctor', 'doctor__doctor_profile').order_by('appointment_date', 'appointment_time')[:5]
        total_visits = Appointment.objects.filter(patient=patient, status='completed').count()
        active_prescriptions  = Prescription.objects.filter(patient=patient, status='active').select_related('doctor')[:5]
        return Response({
            "user" : {
                "name" : patient.get_full_name(),
                "email" : patient.email,
            },
            "upcoming_appointments": [
                {
                    "id": appt.id,
                    "doctor_name":f"Dr. {appt.doctor.get_full_name()}",
                    "specialization": getattr(a.doctor.doctor_profile, 'specialization', ''),
                    "appointment_date": appt.appointment_date,
                    "appointment_time": appt.appointment_time,
                    "status": appt.status,
                } 
                for appt in upcoming_appointments
            ],
            "upcoming_appointments_count": upcoming_appointments.count(),
            "total_visits": total_visits,
            "total_appointments": Appointment.objects.filter(patient=patient).count(),
            "active_prescriptions_count" : active_prescriptions.count(),
            "active_prescriptions" : [
                {
                    "id" : p.id,
                    "medication_name" : p.medication_name,
                    "dosage" : p.dosage,
                    "frequency" : p.frequency,
                    "duration" : p.duration,
                    "doctor_name" : f"Dr. {p.doctor.get_full_name()}",
                    "status" : p.status,
                } for p in active_prescriptions
                
            ]
            # "active_prescriptions_count": active_prescriptions.count(),

        })