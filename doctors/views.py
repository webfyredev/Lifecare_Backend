from rest_framework.views import APIView
from rest_framework.response import Response
from accounts.permissions import IsDoctor
from appointments.models import Appointment
from accounts.models import User

class DoctorDashboardView(APIView):
    permission_classes = [IsDoctor]

    def get(self, request):
        doctor = request.user
        today_appointments = Appointment.objects.filter( doctor=doctor, status='confirmed').select_related('patient')[:10]
        total_patients = Appointment.objects.filter( doctor=doctor).values('patient').distinct().count()

        return Response({
            "user" : {
                "name" : f"Dr. {doctor.get_full_name()}",
                "specialization" : doctor.doctor_profile.specialization,
            },
            "today_appointments": [
                {
                    "id": appt.id,
                    "patient_name": appt.patient.get_full_name(),
                    "appointment_date": appt.appointment_date,
                    "appointment_time": appt.appointment_time,
                    "reason" : appt.reason,
                }
                for appt in today_appointments
            ],
            "total_appointments": total_patients,
        })