from rest_framework.views import APIView
from rest_framework.response import Response
from accounts.permissions import IsPatient
from appointments.models import Appointment

class PatientDashboardView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        patient = request.user
        upcoming_appointments = Appointment.objects.filter(patient=patient, status__in=['pending', 'confirmed']).select_related('doctor')[:5]

        return Response({
            "user" : {
                "name" : patient.get_full_name(),
                "email" : patient.email,
            },
            "upcoming_appointments": [
                {
                    "id": appt.id,
                    "doctor_name":f"Dr. {appt.doctor.get_full_name()}",
                    "appointment_date": appt.appointment_date,
                    "appointment_time": appt.appointment_time,
                    "status": appt.status,
                }
                for appt in upcoming_appointments
            ],
            "total_appointments": Appointment.objects.filter(patient=patient).count(),
        })