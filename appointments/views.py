from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from accounts.permissions import IsPatient, IsDoctor
from .models import Appointment
from .serializers import AppointmentSerializer

class PatientAppointmentsView(generics.ListAPIView):
    permission_classes = [IsPatient]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        patient = self.request.user
        filter_type = self.request.query_params.get('filter', 'all')
        today = timezone.now().date()
        
        qs = Appointment.objects.filter(patient=patient).select_related('doctor', 'doctor__doctor_profile')
        if filter_type == 'upcoming':
            return qs.filter(appointment_date__gte=today, status__in=['pending', 'confirmed'])
        elif filter_type == 'past':
            return qs.filter(appointment_date__lt=today) | qs.filter(status='completed')
        
        return qs

class RescheduleAppointmentView(APIView):
    permission_classes = [IsPatient]

    def patch(self, request, pk):
        try: 
            appointment = Appointment.objects.get(pk=pk, patient=request.user)
            if appointment.status in ['completed', 'cancelled']:
                return Response({"error" : "Cannot reschedule this appointment"}, status=400)
            
            new_date = request.data.get('appointment_date')
            new_time = request.data.get('appointment_time')
            
            if not new_date or not new_time:
                return Response({"error" : "Both date and time are required."}, status=400)
            
            appointment.appointment_date = new_date
            appointment.appointment_time = new_time
            appointment.status = 'pending'
            appointment.save()

            return Response({"message" : "Appointment rescheduled successfully"})
        except Appointment.DoesNotExist:
            return Response({"error" : "Not found."}, status=404)


class BookAppointmentView(generics.CreateAPIView):
    permission_classes = [IsPatient]
    serializer_class = AppointmentSerializer

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user)

class CancelAppointmentView(APIView):
    permission_classes = [IsPatient]

    def patch(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk, patient=request.user)
            if appointment.status in ['completed', 'cancelled']:
                return Response(
                    {"error" : "Cannot cancel this appointment"},
                    status = status.HTTP_400_BAD_REQUEST
                )
            appointment.status = 'cancelled'
            appointment.save()
            return Response({"message" : "Appointment cancelled."})
        except Appointment.DoesNotExist:
            return Response({"error" : "Not found"}, status=404)

class AvailableDoctorsView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        from accounts.models import User
        doctors = User.objects.filter(role='doctor', doctor_profile__is_available=True).select_related('doctor_profile')

        data = [
            {
                "id" : d.id,
                "name" : f"Dr. {d.get_full_name()}",
                "specialization" : d.doctor_profile.specialization,
                "consultation_fee" : str(d.doctor_profile.consultation_fee),
                "available_days" : d.doctor_profile.available_days
            } for d in doctors
        ]
        return Response(data)
