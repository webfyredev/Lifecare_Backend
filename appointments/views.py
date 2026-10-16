from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from accounts.permissions import IsPatient, IsDoctor, IsPatientOrAdmin
from .models import Appointment
from .serializers import AppointmentSerializer
from notifications.emails import send_appointment_confirmed, send_appointment_booked, send_appointment_cancelled, send_appointment_rescheduled
from datetime import datetime


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
    permission_classes = [IsPatientOrAdmin]

    def patch(self, request, pk):
        try: 
            if getattr(request.user, 'role', None) == 'admin':
                appointment = Appointment.objects.get(pk=pk)
            else:
                appointment = Appointment.objects.get(pk=pk, patient=request.user)

            new_date = request.data.get('appointment_date')
            new_time = request.data.get('appointment_time')

            if not new_date or not new_time:
                return Response({"error" : "Date and time are required."}, status=400)
            
            appointment.appointment_date = new_date

            if isinstance(new_time, str):
                try:
                    appointment.appointment_time = datetime.strptime(new_time, '%H:%M').time()
                except ValueError:
                    appointment.appointment_time = datetime.strptime(new_time, '%H:%M:%S').time()
            else:
                appointment.appointment_time = new_time
            
            appointment.status = 'pending'
            appointment.save()

            appointment.refresh_from_db()

            rescheduled_by = 'system' if getattr(request.user, 'role', None) == 'admin' else 'patient'

            try:
                send_appointment_rescheduled(appointment, rescheduled_by=rescheduled_by)
            except Exception as e:
                print(f"Email error: {e}")
            return Response({"message" : "Rescheduled successfully!."})
        except Appointment.DoesNotExist:
            return Response({"error" : "Appointment Not Found."}, status=404)


class BookAppointmentView(generics.CreateAPIView):
    permission_classes = [IsPatientOrAdmin]
    serializer_class = AppointmentSerializer

    def perform_create(self, serializer):
        from accounts.models import User
        doctor = serializer.validated_data.get('doctor')
        patient_id = serializer.validated_data.get('patient_id')
        appointment_date = serializer.validated_data.get('appointment_date')

        if getattr(self.request.user, 'role', None) == 'admin' and patient_id:
            try:
                patient = User.objects.get(id=patient_id, role='patient')
            except User.DoesNotExist:
                return Response({"error" : "Selected patient does not exist."})
        else:
            patient = self.request.user

        if doctor and appointment_date:
            try:
                profile = doctor.doctor_profile
                existing_count = Appointment.objects.filter(doctor=doctor, appointment_date=appointment_date, status__in=['pending', 'confirmed']).count()
                if existing_count >= profile.max_patient_per_day:
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({"error" : f"Dr. {doctor.get_full_name()} is fully booked on this date. Please choose another date."})
                day_name = appointment_date.strftime('%A')
                if profile.available_days and day_name not in profile.available_days:
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({"error" : f"Dr {doctor.get_full_name()} is not available on {day_name}s. Available days: {', '.join(profile.available_days)}"})
            except AttributeError:
                pass
        
        appointment = serializer.save(patient=patient)
        appointment.refresh_from_db()
        try:
            send_appointment_booked(appointment)
        except Exception as e:
            print(f"Email error: {e}")

class CancelAppointmentView(APIView):
    permission_classes = [IsPatientOrAdmin]

    def patch(self, request, pk):
        try:
            if getattr(request.user, 'role', None) == 'admin':
                appointment = Appointment.objects.get(pk=pk)
            else:
                appointment = Appointment.objects.get(pk=pk, patient=request.user)

            if appointment.status in ['completed', 'cancelled']:
                return Response(
                    {"error" : "Cannot cancel this appointment"},
                    status = status.HTTP_400_BAD_REQUEST
                )
            appointment.status = 'cancelled'
            appointment.save()

            appointment.refresh_from_db()

            cancelled_by = 'system' if getattr(request.user, 'role', None) == 'admin' else 'patient'
            try:
                send_appointment_cancelled(appointment, cancelled_by=cancelled_by)
            except Exception as e:
                print(f"Email error: {e}")
            return Response({"message" : "Appointment cancelled successfully."})
        except Appointment.DoesNotExist:
            return Response({"error" : "Appointment Not found or unauthorized."}, status=404)
    


class AvailableDoctorsView(APIView):
    permission_classes = [IsPatientOrAdmin]

    def get(self, request):
        from accounts.models import User
        selected_date = request.query_params.get('date')
        doctors = User.objects.filter(role='doctor', doctor_profile__is_available=True).select_related('doctor_profile')

        today = timezone.now().date()
        check_date = None

        if selected_date:
            try:
                from datetime import date
                check_date = date.fromisoformat(selected_date)
            except ValueError:
                check_date = today
        else:
            check_date = today

        day_name = check_date.strftime('%A')
        data = []
        for d in doctors:
            profile = d.doctor_profile
            appointments_that_day = Appointment.objects.filter(doctor=d, appointment_date = check_date, status__in=['pending', 'confirmed']).count()
            max_patients = profile.max_patient_per_day
            is_fully_booked = appointments_that_day >= max_patients
            slots_remaining = max(0, max_patients - appointments_that_day)
            works_that_day = day_name in  (profile.available_days or [])

            data.append({
                "id" : d.id,
                "name" : f"Dr. {d.get_full_name()}",
                "specialization" : profile.specialization,
                "consultation_fee" : str(profile.consultation_fee),
                "available_days" : profile.available_days,
                "max_patients_per_day" : max_patients,
                "appointments_today" : appointments_that_day,
                "slots_remaining" :  slots_remaining,
                "is_fully_booked" : is_fully_booked,
                "works_on_selected_day" : works_that_day,
                "is_available" : profile.is_available and not is_fully_booked and works_that_day

            })
        data.sort(key=lambda x: (not x['is_available'], x['is_fully_booked']))
        return Response(data)


class DoctorAppointmentsView(APIView):
    permission_classes = [IsDoctor]

    def get(self, request):
        doctor = request.user
        filter_type = request.query_params.get('filter', 'all')
        today = timezone.now().date()
        qs = Appointment.objects.filter(doctor=doctor).select_related('patient', 'patient__patient_profile').order_by('-appointment_date', 'appointment_time')

        if filter_type == 'today':
            qs = qs.filter(appointment_date=today)
        elif filter_type == 'upcoming':
            qs = qs.filter(appointment_date__gt=today, status__in=['pending', 'confirmed'])
        elif filter_type == 'completed':
            qs = qs.filter(status='completed')
        
        return Response([
            {
                "id" : a.id,
                "patient_name" : a.patient.get_full_name(),
                "patient_initials" : f"{a.patient.first_name[:1]}{a.patient.last_name[:1]}".upper(),
                "patient_picture" : request.build_absolute_uri(a.patient.profile_picture.url) if a.patient.profile_picture else None,
                "date" : a.appointment_date,
                "time" : a.appointment_time,
                "reason" : a.reason,
                "notes" : a.notes,
                "status" : a.status,
                "location" : a.location
            } for a in qs
        ])

class ConfirmAppointmentView(APIView):
    permission_classes = [IsDoctor]

    def patch(self, request, pk):
        try : 
            apt = Appointment.objects.get(pk=pk, doctor=request.user)
            apt.status = 'confirmed'
            apt.save()

            apt.refresh_from_db()
            from messaging.models import Conversation
            from notifications.models import Notification
            conversation, conv_created = Conversation.objects.get_or_create(patient=apt.patient, doctor=apt.doctor)
            if conv_created:
                Notification.objects.create(
                    recipient=apt.patient, 
                    title = "You can now message your doctor",
                    body=f"Your appointment with Dr {apt.doctor.get_full_name()} has been confirmed. You can now send them a message directly.",
                    type="message"
                )
                Notification.objects.create(
                    recipient=apt.doctor, 
                    title = "New patient conversation started",
                    body=f"A conversation has been opened with {apt.patient.get_full_name()} following their confirmed appointment.",
                    type="message"
                )
                
            try:
                send_appointment_confirmed(apt)
            except Exception as e:
                print(f"Confirmation email failed: {e}")

            return Response({"message" : "Appointment Confirmed.", "conversation_id" : conversation.id})
        except Appointment.DoesNotExist:
            return Response({"error" : "Not Found"}, status=404)

class CompleteAppointmentView(APIView):
    permission_classes = [IsDoctor]

    def patch(self, request, pk):
        try:
            apt = Appointment.objects.get(pk=pk, doctor=request.user)
            if apt.status in ['completed', 'cancelled']:
                return Response({"error" : "Cannot complete this appointment"}, status=400)

            apt.status = 'completed'
            apt.notes = request.data.get('notes', '').strip()
            apt.save()
            return Response({"message" : "Appointment Completed."})
        except Appointment.DoesNotExist:
            return Response({"error" : "Not Found"}, status=404)

