from rest_framework.views import APIView
from rest_framework.response import Response
from accounts.permissions import IsDoctor
from appointments.models import Appointment
from accounts.models import User
from django.utils import timezone
from patients.models import PatientProfile, Prescription
from patients.serializers import PatientProfileSerializer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

class DoctorDashboardView(APIView):
    permission_classes = [IsDoctor]

    def get(self, request):
        doctor = request.user
        today = timezone.now().date()

        today_appointments = Appointment.objects.filter(doctor=doctor, appointment_date=today).select_related('patient', 'patient__patient_profile').order_by('appointment_date')
        upcoming_appointments = Appointment.objects.filter(doctor=doctor, status__in=['pending', 'confirmed'], appointment_date__gt=today).select_related('patient', 'patient__patient_profile').order_by('appointment_date', 'appointment_time')[:5]
        pending_count = Appointment.objects.filter(doctor=doctor, status='pending').count()
        total_patients = Appointment.objects.filter(doctor=doctor).values('patient').distinct().count()
        
        critical_count = Appointment.objects.filter(doctor=doctor, status='pending', appointment_date=today).count()
        from datetime import timedelta

        weekly_data = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            count = Appointment.objects.filter(doctor=doctor, appointment_date=day).count()
            weekly_data.append({"day" : day.strftime('%a'), "date" : str(day), "count" : count})

        def serialize_apt(a):
            return {
                "id" : a.id,
                "patient_name" : a.patient.get_full_name(),
                "patient_initials" : f"{a.patient.first_name[:1]}{a.patient.last_name[:1]}".upper(),
                "patient_picture" : request.build_absolute_uri(a.patient.profile_picture.url) if a.patient.profile_picture else None,
                "date" : a.appointment_date,
                "time" : a.appointment_time, 
                "reason" : a.reason,
                "status" : a.status
            }
        

        return Response({
            "doctor_name" : f"Dr. {doctor.get_full_name()}",
            "specialization" : getattr(doctor.doctor_profile, 'specialization', ''),
            "is_available" : getattr(doctor.doctor_profile, 'is_available', True),
            "today_appointments" : [serialize_apt(a) for a in today_appointments],
            "today_appointment_counts" : today_appointments.count(),
            "upcoming_appointments" : [serialize_apt(a) for a in upcoming_appointments],
            "upcoming_appointment_count" : upcoming_appointments.count(),
            "total_patients" : total_patients,
            "pending_count" : pending_count,
            "critical_count" : critical_count,
            "weekly_data" : weekly_data,
        })

class DoctorPatientView(APIView):
    permission_classes = [IsDoctor]

    def get(self, request):
        doctor = request.user
        filter_type = request.query_params.get('filter', 'all')
        search = request.query.params.get('search', '')

        patient_ids = Appointment.objects.filter(doctor=doctor).values_list('patient', flat=True).distinct()

        print(f"DEBUG → doctor: {doctor}, patient_ids: {list(patient_ids)}")

        patients = User.objects.filter(id__in=patient_ids).select_related('patient_profile')

        if search:
            patients = User.objects.filter(id__in=patient_ids).filter(first_name__icontains=search) | User.objects.filter(id__in=patient_ids, last_name__icontains=search)
            # patients = patients.filter(first_name__icontains=search) | patients.filter(last_name__icontains=search)
        
        data = []
        for p in patients:
            last_apt = Appointment.objects.filter(doctor=doctor, patients=p).order_by('-appointment_date').first()
            status = 'monitor' if last_apt and last_apt.status == 'pending' else 'stable'
            
            data.append({
                "id" : p.id,
                "name" : p.get_full_name(),
                "initials" : f"{p.first_name[:1]} {p.last_name[:1]}".upper(),
                "profile_picture" : request.build_absolute_uri(p.profile_picture.url) if p.profile_picture else None,
                "gender" : p.gender,
                "date_of_birth" : p.date_of_birth,
                "blood_type" : getattr(p.patient_profile, 'blood_type', '') if hasattr(p, 'patient_profile') else '',
                "last_visit" : last_apt.appointment_date if last_apt else None,
                "allergies" : getattr(p.patient_profile, 'allergies', ''),
                "medical_history" : getattr(p.patient_profile, 'medical_history', '')
            })
        
        return Response(data)


class PatientDetailsView(APIView):
    permission_classes = [IsDoctor]

    def get(self, request, patient_id):
        doctor = request.user
        has_relation = Appointment.objects.filter(doctor=doctor, patient_id=patient_id).exists()
        
        if not has_relation:
            return Response({"error" : "Patient not Found"}, status=404)

        try:
            patient = User.objects.get(id=patient_id)
        except User.DoesNotExist:
            return Response({"error" : "Not Found"}, status=404)
        
        profile = getattr(patient, 'patient_profile', None)

        appointments = Appointment.objects.filter(doctor=doctor, patient=patient).order_by('-appointment_date')[:5]
        prescriptions = Prescription.objects.filter(doctor=doctor, patient=patient, status='active')

        from messaging.models import Conversation

        conversation = Conversation.objects.filter(doctor=doctor, patient=patient).first()

        return Response({
            "id" : patient.id,
            "name" : patient.get_full_name(),
            "initials" : f"{patient.first_name[:1]} {patient.last_name[:1]}".upper(),
            "profile_picture" : request.build_absolute_uri(patient.profile_picture.url) if patient.profile_picture else None,
            "email" : patient.email,
            "phone" : patient.phone_number,
            "gender" : patient.gender,
            "date_of_birth" : patient.date_of_birth,
            "address" : patient.address,
            "blood_type" : getattr(profile, 'blood_type', ''),
            "allergies" : getattr(profile, 'allergies', ''),
            "emergency_contact_name" : getattr(profile, "emergency_contact_name", ''),
            "emergency_contact_phone" : getattr(profile, "emergency_contact_phone", ''),
            "insurance_number" : getattr(profile, 'insurance_number', ''),
            "medical_history" : getattr(profile, 'medical_history', ''),
            "recent_appointments" : [
                {
                    "id" : a.id,
                    "date" : a.appointment_date,
                    "time" : a.appointment_time,
                    "reason" : a.reason,
                    "status" : a.status,
                    "notes" : a.notes
                } for a in appointments
            ],
            "active_prescriptions" : [
                {
                    "id" : p.id,
                    "medication_name" : p.medication_name,
                    "dosage" : p.dosage,
                    "frequency" : p.frequency,
                    "duration" : p.duration,
                    "notes" : p.notes,

                } for p in prescriptions
            ],
            "conversation_id" : conversation.id if conversation else None
        })


class DoctorPrescriptionView(APIView):
    permission_classes = [IsDoctor]

    def get(self, request):
        doctor = request.user
        filter_type = request.query_params.get('filter', 'all')
        
        qs = Prescription.objects.filter(doctor=doctor).select_related('patient').order_by('-prescribed_date')

        if filter_type == 'active':
            qs = qs.filter(status='active')
        elif filter_type == 'completed':
            qs = qs.filter(status='completed')
        
        return Response([
            {
                "id" : p.id,
                "medication_name" : p.medication_name,
                "dosage" : p.dosage,
                "frequency" : p.frequency,
                "duration" : p.duration,
                "notes" : p.notes,
                "status" : p.status,
                "prescribed_date" : p.prescribed_date,
                "patient_name" : p.patient.get_full_name(),
                "patient_id" : p.patient_id
            } for p in qs
        ])
    
    def post(self, request):
        doctor = request.user
        patient_id = request.data.get('patient_id')

        try:
            patient = User.objects.get(id=patient_id, role='patient')
        except User.DoesNotExist:
            return Response({"error" : "Patient not found"}, status=404)

        prescription = Prescription.objects.create(
            doctor=doctor,
            patient=patient,
            medication_name = request.data.get('medication_name', ''),
            dosage = request.data.get('dosage', ''),
            frequency = request.data.get('frequency', ''),
            duration = request.data.get('duration', ''),
            notes = request.data.get('notes', ''),
            status = 'active'
        )

        return Response({
            "id" : prescription.id,
            "medication_name" : prescription.medication_name,
            "patient_name" : patient.get_full_name(),
            "status" : prescription.status,

        }, status=201)


class DoctorPrescriptionDetailsView(APIView):
    permission_classes = [IsDoctor]

    def patch(self, request, pk):
        try:
            p = Prescription.objects.get(pk=pk, doctor=request.user)
            p.medication_name = request.data.get('medication_name', p.medication_name)
            p.dosage = request.data.get('dosage', p.dosage)
            p.frequency = request.data.get('frequency', p.frequency)
            p.duration = request.data.get('duration', p.duration)
            p.notes = request.data.get('notes', p.notes)
            p.status = request.data.get('status', p.status)
            p.save()
            return Response({"message" : "Prescription updated."})
        except Prescription.DoesNotExist:
            return Response({"error" : "Not Found"}, status=404)

class DoctorProfileUpdateView(APIView):
    permission_classes = [IsDoctor]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        doctor = request.user
        profile = doctor.doctor_profile
        return Response({
            "first_name" : doctor.first_name,
            "last_name" : doctor.last_name, 
            "email" : doctor.email,
            "phone_number" : doctor.phone_number,
            "gender" : doctor.gender,
            "address" : doctor.address,
            "profile_picture" : request.build.uri(doctor.profile_picture.url) if doctor.profile_picture else None,
            "specialization" : profile.specialization,
            "license_number" : profile.license_number,
            "years_of_experience" : profile.years_of_experience,
            "bio" : profile.bio,
            "consultation_fee" : str(profile.consultation_fee),
            "available_days" : profile.available_days,
            "is_available" : profile.is_available
        })

    def patch(self, request):
        doctor = request.user
        profile = doctor.doctor_profile

        for field in ["first_name", "last_name", "phone_number", "gender", "address"]:
            if field in request.data:
                setattr(doctor, field, request.data[field])
        
        if 'profile_picture' in request.FILES:
            doctor.profile_picture = request.FILES['profile_picture']

        doctor.save()

        for field in ['specialization', 'years_of_experience', 'bio', 'consultation_fee', 'available_days', 'is_available']:
            if field in request.data:
                setattr(profile, field, request.data[field])
        
        profile.save()

        return Response({"message" : "Profile Updated Successfully."})