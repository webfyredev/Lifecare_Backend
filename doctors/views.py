from rest_framework.views import APIView
from rest_framework.response import Response
from accounts.permissions import IsDoctor, IsDoctorOrAdmin
from appointments.models import Appointment
from accounts.models import User
from django.utils import timezone
from patients.models import PatientProfile, Prescription, MedicalRecords
from patients.serializers import PatientProfileSerializer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from notes.models import MedicalNotes
from notifications.emails import send_new_prescription
import requests as http_requests
from django.conf import settings
from django.core.cache import cache
from rest_framework import status



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
        
        from django.utils.timezone import now
        month_start = today.replace(day=1)
        month_apts = Appointment.objects.filter(doctor=doctor, appointment_date__gte=month_start)
        appointment_breakdown = {
            "confirmed" : month_apts.filter(status='confirmed').count(),
            "pending" : month_apts.filter(status='pending').count(),
            "completed" : month_apts.filter(status='completed').count(),
            "cancelled" : month_apts.filter(status='cancelled').count(),
        }
        thirty_days_ago = today - timedelta(days=30)
        all_patient_ids = Appointment.objects.filter(doctor=doctor).values_list('patient', flat=True).distinct()

        recent_patient_ids = Appointment.objects.filter(doctor=doctor, appointment_date__gte=thirty_days_ago).values_list('patient', flat=True).distinct()

        followup_ids = set(all_patient_ids) - set(recent_patient_ids)

        from accounts.models import User

        followup_patients = User.objects.filter(id__in=followup_ids)[:5]

        recent_notes = MedicalNotes.objects.filter(doctor=doctor).select_related('patient').order_by('-created_at')[:3]
        today_name = today.strftime('%A')
        available_days = getattr(doctor.doctor_profile, 'available_days', []) or []
        works_today = today_name in available_days
        today_booked_count = Appointment.objects.filter(doctor=doctor, appointment_date=today, status__in=['pending', 'confirmed']).count()
        max_per_day = getattr(doctor.doctor_profile, 'max_patient_per_day', 20)
        is_fully_booked_today = today_booked_count >= max_per_day if works_today else False
        slots_left_today = max(0, max_per_day - today_booked_count) if works_today else 0
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
            "appointment_breakdown" : appointment_breakdown,
            "available_days" : available_days,
            "works_today" : works_today,
            "today_name" : today_name,
            "max_patients_per_day" : max_per_day,
            "today_booked_count" : today_booked_count,
            "is_fully_booked_today" : is_fully_booked_today,
            "slots_left_today" : slots_left_today,
            "followup_patients" : [
                {
                    "id" : p.id,
                    "name" : p.get_full_name(),
                    "initials" : f"{p.first_name[:1]}{p.last_name[:1]}",
                    "profile_picture" : request.build_absolute_uri(p.profile_picture.url) if p.profile_picture else None,
                } for p in followup_patients
            ],
            "recent_notes" : [
                {
                    "id" : n.id,
                    "title" : n.title,
                    "patient_name" : n.patient.get_full_name(),
                    "severity" : n.severity,
                    "created_at" : n.created_at
                } for n in recent_notes
            ]
        })

class DoctorPatientView(APIView):
    permission_classes = [IsDoctor]

    def get(self, request):
        doctor = request.user
        filter_type = request.query_params.get('filter', 'all')
        search = request.query_params.get('search', '')

        patient_ids = Appointment.objects.filter(doctor=doctor).values_list('patient', flat=True).distinct()

        # print(f"DEBUG  doctor: {doctor}, patient_ids: {list(patient_ids)}")

        patients = User.objects.filter(id__in=patient_ids).select_related('patient_profile')

        if search:
            patients = User.objects.filter(id__in=patient_ids).filter(first_name__icontains=search) | User.objects.filter(id__in=patient_ids, last_name__icontains=search)
        
        data = []
        for p in patients:
            last_apt = Appointment.objects.filter(doctor=doctor, patient=p).order_by('-appointment_date').first()
            status = 'monitor' if last_apt and last_apt.status == 'pending' else 'stable'
            
            data.append({
                "id" : p.id,
                "name" : p.get_full_name(),
                "initials" : f"{p.first_name[:1]}{p.last_name[:1]}".upper(),
                "profile_picture" : request.build_absolute_uri(p.profile_picture.url) if p.profile_picture else None,
                "gender" : p.gender,
                "date_of_birth" : p.date_of_birth,
                "blood_type" : getattr(p.patient_profile, 'blood_type', '') if hasattr(p, 'patient_profile') else '',
                "last_visit" : last_apt.appointment_date if last_apt else None,
                "allergies" : getattr(p.patient_profile, 'allergies', '') if hasattr(p, 'patient_profile') else '',
                "medical_history" : getattr(p.patient_profile, 'medical_history', '') if hasattr(p, 'patient_profile') else '',
                "status" : status
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
        medical_records = MedicalRecords.objects.filter(patient=patient).order_by('-date_recorded')[:5]

        from messaging.models import Conversation
        from patients.models import VitalsLog
        vital = VitalsLog.objects.filter(patient=patient).order_by('-logged_at').first()
        conversation = Conversation.objects.filter(doctor=doctor, patient=patient).first()

        return Response({
            "id" : patient.id,
            "name" : patient.get_full_name(),
            "initials" : f"{patient.first_name[:1]}{patient.last_name[:1]}".upper(),
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
            "hospital_number" : getattr(profile, 'hospital_number', ''),
            "blood_pressure_systolic" : vital.blood_pressure_systolic if vital else None,
            "blood_pressure_diastolic" : vital.blood_pressure_diastolic if vital else None,
            "heart_rate_bpm" : vital.heart_rate_bpm if vital else None,
            "blood_sugar_mgdl" : vital.blood_sugar_mgdl if vital else None,
            "temperature_celcius" : vital.temperature_celsius if vital else None,
            "vitals_logged_at" : vital.logged_at if vital else None,
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
            "medical_records" : [
                {
                    "id" : r.id,
                    "title" : r.title,
                    "record_type" : r.record_type,
                    "description" : r.description,
                    "date_recorded" : r.date_recorded,
                    "file" : request.build_absolute_uri(r.file.url) if r.file else None,
                } for r in medical_records
            ],
            "conversation_id" : conversation.id if conversation else None
        })


class DoctorPrescriptionView(APIView):
    permission_classes = [IsDoctorOrAdmin]

    def get(self, request):
        # doctor = request.user
        filter_type = request.query_params.get('filter', 'all')
        if request.user.role == 'admin' or request.user.is_staff:
            qs = Prescription.objects.all().select_related('patient', 'doctor').order_by('-prescribed_date')
        else:
            qs = Prescription.objects.filter(doctor=request.user).select_related('patient', 'doctor').order_by('-prescribed_date')

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
                "patient_name" : p.patient.get_full_name() if hasattr(p.patient, 'get_full_name') else f"{p.patient.first_name} {p.patient.last_name}",
                "patient_id" : p.patient_id,
                "doctor_name" : p.doctor.get_full_name() if hasattr(p.doctor, 'get_full_name') else f"{p.doctor.first_name} {p.doctor.last_name}",
                "doctor_id" : p.doctor_id
            } for p in qs
        ])
    
    def post(self, request):
        
        patient_id = request.data.get('patient_id')
        doctor_id = request.data.get('doctor_id')
        if not patient_id:
            return Response({"error" : "Patient ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role =='admin' or request.user.is_staff:
            if not doctor_id:
                return Response({"error" : "Admin must specify a doctor when creating a prescription "}, status=400)
            try:
                doctor = User.objects.get(id=doctor_id, role='doctor')
            except User.DoesNotExist:
                return Response({"error" : "Assigned doctor not found."}, status=404)
        else:
            doctor = request.user

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
        try:
            send_new_prescription(prescription)
        except Exception as e:
            print(f"Email error: {e}")

        return Response({
            "id" : prescription.id,
            "medication_name" : prescription.medication_name,
            "patient_name" : patient.get_full_name() if hasattr(patient, 'get_full_name') else f"{patient.first_name} {patient.last_name}",
            "doctor_name" : doctor.get_full_name() if hasattr(doctor, 'get_full_name') else f"{doctor.first_name} {doctor.last_name}",
            "status" : prescription.status,

        }, status=201)


class DoctorPrescriptionDetailsView(APIView):
    permission_classes = [IsDoctorOrAdmin]

    def patch(self, request, pk):
        # admin = User.objects.filter(role='admin')
        try:
            if request.user.role == 'admin' or request.user.is_staff:
                p = Prescription.objects.get(pk=pk)
            else: 
                p = Prescription.objects.get(pk=pk, doctor=request.user)

            p.medication_name = request.data.get('medication_name', p.medication_name)
            p.dosage = request.data.get('dosage', p.dosage)
            p.frequency = request.data.get('frequency', p.frequency)
            p.duration = request.data.get('duration', p.duration)
            p.notes = request.data.get('notes', p.notes)
            p.status = request.data.get('status', p.status)

            doctor_id = request.data.get('doctor_id')
            if doctor_id and (request.user.role == 'admin' or request.user.is_staff):
                try:
                    p.doctor = User.objects.get(id=doctor_id, role='doctor')
                except User.DoesNotExist:
                    return Response({"error" : "Doctor not found"}, status=404)

            p.save()
            return Response({"message" : "Prescription updated successfully."})

        except Prescription.DoesNotExist:
            return Response({"error" : "Prescription not found"}, status=status.HTTP_404_NOT_FOUND)
    
    
    def delete(self, request, pk):
            try:
                prescription = Prescription.objects.get(pk=pk)
                prescription.delete()
                return Response({"message" : "Prescription deleted"})
            except Prescription.DoesNotExist:
                return Response({"error" : "Prescription not found"}, status=status.HTTP_404_NOT_FOUND)

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

        for field in ['specialization', 'license_number', 'years_of_experience', 'bio', 'consultation_fee', 'available_days', 'is_available']:
            if field in request.data:
                setattr(profile, field, request.data[field])
        
        profile.save()

        return Response({"message" : "Profile Updated Successfully."})


class DoctorNewsView(APIView):
    permission_classes = [IsDoctor]

    def get(self, request):
        doctor = request.user
        specialization = getattr(getattr(doctor, 'doctor_profile', None), 'specialization', 'medicine')

        cache_key = f"doctor_news_{specialization.lower().replace(' ', '_')}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        api_key = settings.NEWS_API_KEY
        query = f"{specialization} medicine health"

        try:
            response = http_requests.get(
                'https://newsapi.org/v2/everything',
                params={
                    'q' : query,
                    'language' : 'en',
                    'sortBy' : 'publishedAt',
                    'pageSize' : 5,
                    'apiKey' : api_key
                },
                timeout=10
            )
            data = response.json()
            
            if data.get('status') != 'ok':
                return Response({"articles" : [], "error" : 'News unavailable'})
            
            articles = [
                {
                    "title" : a.get('title', ''),
                    "description" : a.get('description', ''),
                    "url" : a.get('url', ''),
                    "source" : a.get('source', {}).get('name', ''),
                    "published_at" : a.get('publishedAt', ''),
                    "image" : a.get('urlToImage', ''),

                } for a in data.get('articles', [])[:5]
                if a.get('title') and '[Removed]' not in a.get('title', '')
            ]

            result = {"articles" : articles, "specialization" : specialization}
            cache.set(cache_key, result, 3600)
            return Response(result)

        except Exception as e:
            print(f"News fetch failed: {e}")
            return Response({"articles" : [], "error" : "Could not load  news"})

            