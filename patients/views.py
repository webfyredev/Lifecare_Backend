from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from accounts.permissions import IsDoctor, IsPatient, IsDoctorOrAdmin
from appointments.models import Appointment
from django.utils import timezone
from .models import Prescription, MedicalRecords, PatientProfile, VitalsLog
from .serializers import PrescriptionSerializer, PatientProfileSerializer
from datetime import timedelta
from django.core.cache import cache
import requests as http_requests
class PatientDashboardView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        patient = request.user
        today = timezone.now().date()
        upcoming_appointments = Appointment.objects.filter(patient=patient, status__in=['pending', 'confirmed'], appointment_date__gte=today).select_related('doctor', 'doctor__doctor_profile').order_by('appointment_date', 'appointment_time')[:5]
        total_visits = Appointment.objects.filter(patient=patient, status='completed').count()
        active_prescriptions  = Prescription.objects.filter(patient=patient, status='active').select_related('doctor')[:5]
        alerts = []

        for p in active_prescriptions:
            try:
                duration_text = p.duration.lower().strip()
                if 'day' in duration_text:
                    days = int(''.join(filter(str.isdigit, duration_text)))
                elif 'week' in duration_text:
                    days = int(''.join(filter(str.isdigit, duration_text))) * 7
                elif 'month' in duration_text:
                    days = int(''.join(filter(str.isdigit, duration_text))) * 30
                else:
                    continue

                end_date = p.prescribed_date + timedelta(days=days)
                days_left = (end_date - today).days

                if 0 <= days_left <= 7:
                    alerts.append({
                        "type" : "prescription_expiry",
                        "severity" : "warning",
                        "title" : f"{p.medication_name} prescription ending soon",
                        "message" : f"Your {p.medication_name} prescriptions ends in {days_left} day{'s' if days_left != 1 else ''}. Contact Dr. {p.doctor.get_full_name()} to renew",
                        "action_label" : 'Message Doctor',
                        "action_path" : "/patient/messages"

                    })
            except (ValueError, AttributeError):
                continue
        

        last_appointment = Appointment.objects.filter(patient=patient).order_by('appointment_date').first()
        if last_appointment:
            days_since = (today - last_appointment.appointment_date).days
            if days_since >= 60:
                alerts.append({
                    "type" : "overdue checkup",
                    "severity" : "danger",
                    "title" : "You're overdue for checkup",
                    "message" : f"You haven't seen a doctor in {days_since} days. Regular checkups help catch issues early.",
                    "action_label" : "Book Appointment",
                    "action_path" : "/patient/appointments",
                })
        else:
            alerts.append({
                "type" : "overdue_checkup",
                "severity" : "info",
                "title" : "Book your first appointment",
                "message" : "You haven't booked appointments yet. Start your healthcare journey with LifeCare.",
                "action_label" : "Book Now",
                "action_path" : "/patient/appointments",
            })
        
        

        new_lab = MedicalRecords.objects.filter(patient=patient, record_type='lab_result', created_at__gte = timezone.now() - timedelta(days=7)).first()
        if new_lab:
            alerts.append({
                "type" : "lab_result",
                "severity" : "info",
                "title" : "New lab result available",
                "message" : f"Your doctor added a new lab result: {new_lab.title}. Review it in your records.",
                "action_label" : "View Records",
                "action_path" : "/patient/records"
            })
        
        latest_vitals = VitalsLog.objects.filter(patient=patient).order_by('-logged_at').first()
        
        next_apt = upcoming_appointments.first()

        days_until = None
        if next_apt:
            days_until = (next_apt.appointment_date - today).days
        
        from messaging.models import Message, Conversation

        unread_messages = Message.objects.filter(conversation__patient=patient, is_read=False).exclude(sender=patient).count()

        today_meds = [
            {
                "id" : p.id,
                "medication_name" : p.medication_name,
                "dosage" : p.dosage,
                "frequency" : p.frequency,
                "doctor_name" : f"Dr. {p.doctor.get_full_name()}",
            } for p in Prescription.objects.filter(patient=patient, status='active')
        ]

        recent_records = MedicalRecords.objects.filter(patient=patient).order_by('-date_recorded')[:3]

        return Response({
            "alerts" : alerts,
            "latest_vitals" : {
                "blood_pressure" : f"{latest_vitals.blood_pressure_systolic}/{latest_vitals.blood_pressure_diastolic}" if latest_vitals and latest_vitals.blood_pressure_systolic else None,
                "weight_kg" : float(latest_vitals.weight_kg) if latest_vitals and latest_vitals.weight_kg else None,
                "heart_rate_bpm" : latest_vitals.heart_rate_bpm if latest_vitals else None,
                "blood_sugar_mgdl" : latest_vitals.blood_sugar_mgdl if latest_vitals else None,
                "logged_at" : latest_vitals.logged_at if latest_vitals else None,
            } if latest_vitals else None,
            "user" : {
                "name" : patient.get_full_name(),
                "email" : patient.email,
            },
            "upcoming_appointments": [
                {
                    "id": appt.id,
                    "doctor_name":f"Dr. {appt.doctor.get_full_name()}",
                    "specialization": getattr(appt.doctor.doctor_profile, 'specialization', ''),
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
                
            ],
            "next_appointment" : {
                "doctor_name" : f"Dr. {next_apt.doctor.get_full_name()}",
                "specialization" : getattr(next_apt.doctor.doctor_profile, 'specialization', ''),
                "date" : next_apt.appointment_date,
                "time" : next_apt.appointment_time,
                "days_until" : days_until
            } if next_apt else None,
            "unread_messages" : unread_messages,
            "today_medications" : today_meds,
            "recent_records" : [
                {
                    "id" : r.id,
                    "title" : r.title,
                    "record_type" : r.record_type,
                    "date_recorded" : r.date_recorded
                } for r in recent_records
            ]
        })
        
    

class PatientPrescriptionView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        filter_type = request.query_params.get('filter', 'all')
        qs = Prescription.objects.filter(patient=request.user).select_related('doctor').order_by('-prescribed_date')
        if filter_type == 'active':
            qs = qs.filter(status='active')
        elif filter_type == 'completed':
            qs = qs.filter(status='completed')
        
        active_count = Prescription.objects.filter(patient=request.user, status ='active').count()
        completed_count = Prescription.objects.filter(patient=request.user, status='completed').count()
        total_count = Prescription.objects.filter(patient=request.user).count()

        serializer = PrescriptionSerializer(qs, many=True)
        return Response({
            "prescriptions" : serializer.data,
            "active_count" : active_count,
            "completed_count" : completed_count,
            "total_count" : total_count
        })

class PatientProfileUpdateView(APIView):
    permission_classes = [IsPatient]

    def patch(self, request):
        profile = request.user.patient_profile
        serializer = PatientProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class PatientRecordsView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        filter_type = request.query_params.get('filter', 'all')

        qs = MedicalRecords.objects.filter(patient=request.user).select_related('doctor')

        if filter_type != 'all':
            qs = qs.filter(record_type=filter_type)
        
        total = MedicalRecords.objects.filter(patient=request.user).count()
        
        type_counts = {}

        for choice in MedicalRecords.RECORDS_TYPE_CHOICES:
            type_counts[choice[0]] = MedicalRecords.objects.filter(patient=request.user, record_type=choice[0]).count()


        return Response({
            "records" : [
                {
                    "id" : r.id,
                    "title" : r.title,
                    "record_type" : r.record_type,
                    "description" : r.description,
                    "file" : request.build_absolute_uri(r.file.url) if r.file else None,
                    "date_recorded" : r.date_recorded,
                    "doctor_name" : f"Dr. {r.doctor.get_full_name()} " if r.doctor else "LifeCare",
                } for r in qs
            ],
            "total" : total,
            "type_counts": type_counts
        })      

class VitalsLogView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        vitals = VitalsLog.objects.filter(patient=request.user).order_by('-logged_at')[:10]

        return Response([
            {
                "id" : v.id,
                "blood_pressure" : f"{v.blood_pressure_systolic}/{v.blood_pressure_diastolic}" if v.blood_pressure_systolic else None,
                "blood_pressure_diastolic" : v.blood_pressure_diastolic,
                "weight_kg" : float(v.weight_kg) if v.weight_kg else None,
                "temperature_celsius" : float(v.temperature_celsius) if v.temperature_celsius else None,
                "blood_sugar_mgdl" : v.blood_sugar_mgdl,
                "heart_rate_bpm" : v.heart_rate_bpm,
                "notes" : v.notes,
                "logged_at" : v.logged_at
            } for v in vitals
        ])

    def post(self, request):
        data = request.data

        fields = ['blood_pressure_systolic', 'blood_pressure_diastolic', 'weight_kg', 'temperature_celsius', 'blood_sugar_mgdl', 'heart_rate_bpm']

        if not any(data.get(f) for f in fields):
            return Response({"error" : "Please fill at least one vital"}, status=400)
        

        vital = VitalsLog.objects.create(
            patient=request.user,
            blood_pressure_systolic = data.get('blood_pressure_systolic') or None,
            blood_pressure_diastolic = data.get('blood_pressure_diastolic') or None,
            weight_kg = data.get('weight_kg') or None,
            temperature_celsius = data.get('temperature_celsius') or None,
            blood_sugar_mgdl = data.get('blood_sugar_mgdl') or None,
            heart_rate_bpm = data.get('heart_rate_bpm') or None,
            notes = data.get('notes', ''),
        )

        return Response({
            "id" : vital.id,
            "message" : "Vitals logged successfully",
            "logged_at" : vital.logged_at
        }, status=201)

class DrugInfoView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        drug_name = request.query_params.get('name', '').strip()
        if not drug_name:
            return Response({"error": "Drug name is required"}, status=400)
        
        cache_key = f"drug_info_{drug_name.lower().replace(' ', '_')}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        try:
            response = http_requests.get(
                'https://api.fda.gov/drug/label.json',
                params={
                    'search' : f'openfda.brand_name: "{drug_name}" OR openfda.generic_name: "{drug_name}"',
                    'limit' : 1,
                },

                timeout=10
            )

            data = response.json()

            if not data.get('results'):
                response = http_requests.get(
                    'https://api.fda.gov/drug/label.json',
                    params={
                        'search' : f'openfda.generic_name:"{drug_name}"',
                        'limit' : 1,
                    },
                    timeout=5
                )
                data = response.json()
            if not data.get('results'):
                return Response({"found" : False, "drug_name" : drug_name})
            
            result = data['results'][0]

            drug_info = {
                "found" : True,
                "drug_name" : drug_name,
                "brand_names" : result.get('openfda', {}).get('brand_name', []),
                "generic_name" : result.get('openfda', {}).get('generic_name', []),
                "purpose" : self._get_first(result, 'purpose', 'indications_and_usage'),
                "warnings" : self._get_first(result, 'warnings', 'warnings and cautions'),
                "side_effects" : self._get_first(result, 'adverse_reactions'),
                "dosage" : self._get_first(result, 'dosage_and_administration'),
                "interactions" : self._get_first(result, 'drug_interactions'),
                "contraindications" : self._get_first(result, 'contraindications'),
                "storage" : self._get_first(result, 'storage_and_handling'),
                "when_to_call_doctor" : self._get_first(result, 'ask_doctor', 'ask_doctor_or_pharmacist')
            }

            cache.set(cache_key, drug_info, 86400)
            return Response(drug_info)
        except Exception as e:
            print(f"Drug info fetch failed: {e}")
            return Response({"found" : False, "drug_name" : drug_name, "error": str(e)})

    def _get_first(self, result, *keys):
        for key in keys:
            val = result.get(key)
            if val:
                if isinstance(val, list):
                    text = val[0]
                else:
                    text = val
                return text[:500].strip() if len(text) > 500 else text.strip()

        return None

class AllergyInfoView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        allergen = request.query_params.get('allergen', '').strip()
        if not allergen:
            return Response({"error": "Allergen name is required."}, status=400)

        cache_key = f"allergy_info_{allergen.lower().replace(' ', '_')}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        allergy_info = {
            "found": True,
            "allergen": allergen,
            "related_drugs": [],
            "general_warning": f"You have a recorded allergy to {allergen}. Always inform healthcare providers before receiving any treatment.",
        }

        try:
            response = http_requests.get(
                'https://api.fda.gov/drug/label.json',
                params={
                    'search': f'warnings:"{allergen}" OR contraindications:"{allergen}"',  # ← fixed
                    'limit': 3,
                },
                timeout=5
            )
            data = response.json()

            if data.get('results'):
                for r in data['results'][:3]:
                    brand = r.get('openfda', {}).get('brand_name', [])
                    generic = r.get('openfda', {}).get('generic_name', [])
                    if brand or generic:
                        allergy_info['related_drugs'].append({
                            "brand": brand[0] if brand else '',
                            "generic": generic[0] if generic else '',
                            "warning": (r.get('warnings') or r.get('contraindications') or [''])[0][:200],  # ← fixed brackets
                        })

            cache.set(cache_key, allergy_info, 86400)

        except http_requests.exceptions.Timeout:
            print(f"FDA API timed out for allergen: {allergen}")

        except http_requests.exceptions.ConnectionError:
            print(f"FDA API connection error for allergen: {allergen}")

        except Exception as e:
            print(f"Allergy info fetch failed: {e}")

        return Response(allergy_info)

from notifications.emails import send_medical_record_added
from notifications.models import Notification

class AddRecordView(APIView):
    permission_classes = [IsDoctorOrAdmin]

    def post (self, request):
        from accounts.models import User

        patient_id = request.data.get('patient_id')
        doctor_id = request.data.get('doctor_id')
        title = request.data.get('title', '').strip()
        record_type = request.data.get('record_type', 'general')
        description = request.data.get('description', '').strip()
        date_recorded = request.data.get('date_recorded')
        file = request.FILES.get('file')

        if not patient_id or not title or not date_recorded:
            return Response({"error" : "patient_id, title and date_recorded are required"}, status=400)
        if request.user.role == 'admin' or request.user.is_staff:
            if not doctor_id:
                return Response({"error" : "Admin must specify a doctor when creating a medical record"}, status=400)
            try:
                doctor = User.objects.get(id=doctor_id, role='doctor')
            except User.DoesNotExist:
                return Response({"error" : "Assign doctor not found"}, status=404)
        else:
            doctor = request.user


        try:
            patient = User.objects.get(id=patient_id, role='patient')
        except User.DoesNotExist:
            return Response({"error" : "Patient not found"}, status=404)

        record = MedicalRecords.objects.create(
            patient=patient, 
            doctor=doctor, 
            title=title,
            record_type = record_type,
            description = description,
            date_recorded = date_recorded,
            file = file or None

            )

        try:
            send_medical_record_added(record)
        except Exception as e:
            print(f"Medical record email failed: {e}")

        try:
            Notification.objects.create(
                recipient=patient,
                title= f'New {record.get_record_type_display()} added',
                body = f"Dr {request.user.get_full_name()} added a new {record.get_record_type_display()}: {title}. Check your medical records.",
                type='general'
            )
        except Exception as e:
            print(f"Notification creation failed: {e}")

        return Response({
            "message"  : "Medical record added successfully.",
            "id" : record.id,
            "title" : record.title,
            "doctor" : doctor.get_full_name() if hasattr(doctor, 'get_full_name') else f"{doctor.first_name} {doctor.last_name}",
            "patient" : patient.get_full_name() if hasattr(patient, 'get_full_name') else f"{patient.first_name} {patient.last_name}",
            "record_type" : record.record_type,
        } , status=201)

class RecordsDetailsView(APIView):
    permission_classes = [IsDoctorOrAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, pk):
        from accounts.models import User
        try:
            if request.user.role == 'admin' or request.user.is_staff:
                r = MedicalRecords.objects.get(pk=pk)
            else:
                r = MedicalRecords.objects.get(pk=pk, doctor=request.user)

            r.title = request.data.get('title', r.title)
            r.record_type = request.data.get('record_type', r.record_type)
            r.description = request.data.get('description', r.description)
            # r.file = request.data.get('file', r.file)
            if 'file' in request.FILES:
                r.file = request.FILES['file']

            doctor_id = request.data.get('doctor_id')
            if doctor_id and (request.user.role == 'admin' or request.user.is_staff):
                try:
                    r.doctor = User.objects.get(id=doctor_id, role='doctor')
                except User.DoesNotExist:
                    return Response({"error" : "Doctor not found"}, status=404)

            r.save()
            return Response({"message" : "Records updated successfully."})

        except MedicalRecords.DoesNotExist:
            return Response({"error" : "Medical Records not found"}, status=404)

    def delete(self, request, pk):
        try:
            record = MedicalRecords.objects.get(pk=pk)
            record.delete()
            return Response({"message" : "Record Deleted"})
        except MedicalRecords.DoesNotExist:
            return Response({"error" : "Records not found"}, status=404)

            


