from django.shortcuts import render
from rest_framework.views import APIView
from accounts.permissions import IsAdminUser
from accounts.models import User
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from appointments.models import Appointment
from datetime import timedelta
from doctors.models import DoctorProfile
from notifications.models import Notification
from patients.models import Prescription, MedicalRecords
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Max, Count
from django.db import transaction
from patients.models import Prescription, MedicalRecords, PatientProfile
from messaging.models import Conversation, Message


def calculate_capped_change(current, previous, max_cap=100.0):
    if previous == 0:
        val = 100.0 if current > 0 else 0.0
    else:
        val = ((current - previous) / previous) * 100.0

    clamped = max(-100.0, min(val, max_cap))
    return round(clamped, 1)

def format_stat_payload(current_val, prev_val):
    change = calculate_capped_change(current_val, prev_val, max_cap=100.0)

    return{
        "percentage" : abs(change),
        "raw_change" : change,
        "direction" : "up" if change >=0 else "down"
    }

class AdminDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)

        # admin = request.user
        total_users = User.objects.count()
        total_patient = User.objects.filter(role='patient').count()
        total_doctors = User.objects.filter(role='doctor').count()
        total_admin = User.objects.filter(role='admin').count()
        pending_doctors = DoctorProfile.objects.filter(license_number__startswith='PENDING').count()
        total_appointments = Appointment.objects.all().count()
        # open_issues = Appointment.objects.filter(status='pending', appointment_date__lt=today).count()
        patient_percentage = round((total_patient / total_users * 100),1) if total_users > 0 else 0
        doctor_percentage = round((total_doctors / total_users * 100), 1) if total_users > 0 else 0
        admin_percentage = round((total_admin / total_users * 100), 1) if total_users > 0 else 0

        appointment_overview_data = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            count = Appointment.objects.filter(appointment_date=day).count()
            appointment_overview_data.append({"date" : day.strftime('%b %d'), "appointment" : count })

        user_distribution = [
            {
                "name" : "Patients",
                "value" : total_patient,
                "percentage" : patient_percentage,
                "color" : "#3B82F6",
            },
            {
                "name" : "Doctors",
                "value" : total_doctors,
                "percentage" : doctor_percentage,
                "color" : "#8B5CF6"
            },
            {
                "name" : "Admins",
                "value" : total_admin,
                "percentage" : admin_percentage,
                "color" : "#60A5FA"
            },
        ]
        weekly_data = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            count = User.objects.filter(date_joined__date=day).count()
            weekly_data.append({"day" : day.strftime('%a'), "date" : str(day), "count" : count})

        recent_users = User.objects.order_by('-date_joined')[:5]
        recent_appointments = Appointment.objects.select_related('patient', 'doctor').order_by('-created_at')[:5]

        current_month_start = today.replace(day=1)
        previous_month_end = current_month_start - timedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1)
        days_elapsed = (today - current_month_start).days
        previous_month_comparison_date = min(previous_month_start + timedelta(days=days_elapsed), previous_month_end)


        current_users = User.objects.filter(date_joined__date__gte=current_month_start, date_joined__date__lte=today).count()
        previous_users = User.objects.filter(date_joined__date__gte=previous_month_start, date_joined__date__lte=previous_month_comparison_date).count()

        current_patient = User.objects.filter(role='patient', date_joined__date__gte=current_month_start, date_joined__date__lte=today).count()
        previous_patient = User.objects.filter(role='patient', date_joined__date__gte=previous_month_start, date_joined__date__lte=previous_month_comparison_date).count()

        current_doctor = User.objects.filter(role='doctor', date_joined__date__gte=current_month_start, date_joined__date__lte=today).count()
        previous_doctor = User.objects.filter(role='doctor', date_joined__date__gte=previous_month_start, date_joined__date__lte=previous_month_comparison_date).count()

        current_admin = User.objects.filter(role='admin', date_joined__date__gte=current_month_start, date_joined__date__lte=today).count()
        previous_admin = User.objects.filter(role='admin', date_joined__date__gte=previous_month_start, date_joined__date__lte=previous_month_comparison_date).count()

        current_appointment = Appointment.objects.filter(created_at__date__gte=current_month_start, created_at__date__lte=today).count()
        previous_appointment = Appointment.objects.filter(created_at__date__gte=previous_month_start, created_at__date__lte=previous_month_comparison_date).count()


        users_change = format_stat_payload(current_users, previous_users)
        patients_change = format_stat_payload(current_patient, previous_patient)
        doctors_change = format_stat_payload(current_doctor, previous_doctor)
        appointments_change = format_stat_payload(current_appointment, previous_appointment)
        admin_change = format_stat_payload(current_admin, previous_admin)
        return Response({
            "stats": {
                "total_users": total_users,
                "total_patients": total_patient,
                "total_doctors": total_doctors,
                "pending_doctors": pending_doctors,
                "total_appointments": total_appointments,
                "total_admin" : total_admin,
                # "open_issues": open_issues,
                # "patient_perct" : patient_perct,
                # "doctor_perct" : doctor_perct,
                "user_change" : users_change,
                "patient_change" : patients_change,
                "doctor_change" : doctors_change,
                "appointment_change" : appointments_change,
                "admin_change" : admin_change
            },
            "user_distribution" : user_distribution,
            "appointments_overview" : appointment_overview_data,
            "weekly_data" : weekly_data,
            "recent_registration" : [
                {
                    "id" : r.id,
                    "name" : r.get_full_name(),
                    "email" : r.email,
                    "role" : r.role,
                    "initials" : f"{r.first_name[:1]}{r.last_name[:1]}".upper(),
                    "joined" : r.date_joined,
                    "is_active" : r.is_active
                } for r in recent_users
            ],
            "recent_appointment" : [
                {
                    "id" : apt.id,
                    "patient_name" : apt.patient.get_full_name(),
                    "doctor_name" : apt.doctor.get_full_name(),
                    "doctor_speciality": getattr(apt.doctor.doctor_profile, 'specialization', ''),
                    "reason" : apt.reason,
                    "date" : apt.appointment_date,
                    "time" : apt.appointment_time,
                    "status" : apt.status,
                } for apt in recent_appointments
            ]
        })

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class AdminManageUsersView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):

        total_users = User.objects.count()
        total_patient = User.objects.filter(role='patient').count()
        total_doctors = User.objects.filter(role='doctor').count()
        total_admin = User.objects.filter(role='admin').count()
        role = request.query_params.get('role', 'all')
        status_filter = request.query_params.get('status', 'all')
        search = request.query_params.get('search', '')

        qs = User.objects.all().select_related('patient_profile', 'doctor_profile').order_by('-date_joined')
        # patient_info = PatientProfile.objects.all().select_related('user').order_by('-created_at')

        if role != 'all':
            qs = qs.filter(role=role)

        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        if search:
            qs = qs.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(email__icontains=search) | Q(phone_number__icontains=search))


        paginator = CustomPagination()
        paginated_qs = paginator.paginate_queryset(qs, request)

        users_data = [
            {
                "id" : u.id,
                "name" : u.get_full_name() or u.username,
                "email" : u.email,
                "role" : u.role if hasattr(u, 'role') else 'patient',
                "initials" : f"{u.first_name[:1]}{u.last_name[:1]}".upper(),
                "phone" : getattr(u, 'phone_number', 'N/A'),
                "is_active" : u.is_active,
                "address" : u.address,
                "date_joined" : u.date_joined.strftime('%b %d, %Y'),
                "hospital_number" : getattr(getattr(u, 'patient_profile', None), 'hospital_number', ''),
                "blood_type" : getattr(getattr(u, 'patient_profile', None), 'blood_type', ''),
                "allergies" : getattr(getattr(u, 'patient_profile', None), 'allergies', ''),
                "emergency_contact_name" : getattr(getattr(u, 'patient_profile', None), 'emergency_contact_name', ''),
                "emergency_contact_phone" : getattr(getattr(u, 'patient_profile', None), 'emergency_contact_phone', ''),
                "medical_history" : getattr(getattr(u, 'patient_profile', None), 'medical_history', ''),
                "specialization" : getattr(getattr(u, 'doctor_profile', None), 'specialization', ''),
                "license_number" : getattr(getattr(u, 'doctor_profile', None), 'license_number', ''),
                # ""

            } for u in paginated_qs
        ]
        return paginator.get_paginated_response({
            "users" : users_data
        })

class AdminManageUserDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, user_id):
        try:
            user = User.objects.select_related('patient_profile', 'doctor_profile').get(id=user_id)

        except User.DoesNotExist:
            return Response({"error" : "User not found"}, status=404)

        profile_pic_url = None
        if user.profile_picture:
            profile_pic_url = request.build_absolute_uri(user.profile_picture.url)
        data = {
            "id" : user.id,
            "name" : user.get_full_name() or user.username,
            "email" : user.email,
            "role" : user.role,
            "phone" : user.phone_number,
            "profile_picture" : profile_pic_url,
            "date_of_birth" : user.date_of_birth,
            "gender" : user.gender,
            "address" : user.address,
            "is_active" : user.is_active,
            "date_joined" : user.date_joined.strftime('%b %d, %Y') if user.date_joined else None
        }

        if user.role == 'patient':
            profile = getattr(user, "patient_profile", None)

            if profile:
                data['patient_profile'] = {
                    "hospital_number" : profile.hospital_number,
                    "blood_type" : profile.blood_type,
                    "allergies" : profile.allergies,
                    "emergency_contact_name" : profile.emergency_contact_name,
                    "emergency_contact_phone" : profile.emergency_contact_phone,
                    "insurance_number" : profile.insurance_number,
                    "medical_history" : profile.medical_history,

                }
        elif user.role == 'doctor':
            profile = getattr(user, "doctor_profile", None)

            if profile:
                data['doctor_profile'] = {
                    "specialization" : profile.specialization,
                    "license_number" : profile.license_number,
                    "years_of_experience" : profile.years_of_experience,
                    "bio" : profile.bio,
                    "consultation_fee" : profile.consultation_fee,
                    "available_days" : profile.available_days,
                    "is_available" : profile.is_available,
                    "max_patient_per_day" : profile.max_patient_per_day,
                }

        return Response(data)

    @transaction.atomic
    def patch(self, request, user_id):
        try:
            user = User.objects.select_related('patient_profile', 'doctor_profile').get(id=user_id)
        except User.DoesNotExist:
            return Response({"error" : "User not found"}, status=404)

        user_fields = ['first_name', 'last_name', 'phone', 'email', 'is_active', 'role', 'phone_number', 'date_of_birth', 'gender', 'address']
        for field in user_fields:
            if field in request.data:
                target_field = 'phone_number' if field == 'phone' and hasattr(user, 'phone_number') else field
                if hasattr(user, target_field):
                    setattr(user, target_field, request.data[field])
        
        user.save()

        if user.role == 'patient' and 'patient_profile' in request.data:
            patient_data = request.data['patient_profile']
            profile = getattr(user, 'patient_profile', None)

            if profile:
                patient_fields = ['hospital_number', 'blood_type', 'allergies', 'emergency_contact_name', 'emergency_contact_phone', 'insurance_number', 'medical_history']
                for p_field in patient_fields:
                    if p_field in patient_data:
                        setattr(profile, p_field, patient_data[p_field])
                profile.save()
        elif user.role == 'doctor' and 'doctor_profile' in request.data:
            doctor_data = request.data['doctor_profile']
            profile = getattr(user, 'doctor_profile', 'None')

            if profile:
                doctor_fields = ['specialization', 'license_number', 'years_of_experience', 'bio', 'consultation_fee', 'available_days', 'is_available', 'max_patient_per_day']
                for d_field in doctor_fields:
                    if d_field in doctor_data:
                        setattr(profile, d_field, doctor_data[d_field])
                profile.save()
        return Response({"message" : "User and profile updated successfully."})

    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return Response({"message" : "User deleted."}, status=204)
        except User.DoesNotExist:
            return Response({"error" : "User not found."}, status=404)

class AdminSuspendUserView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user.is_active = False
            user.save()
            return Response({"message" : f"{user.get_full_name()} account system suspended."})
        except User.DoesNotExist:
            return Response({"error" : "User not found"}, status=404)

class AdminRestoreUserView(APIView):
    permission_classes  = [IsAdminUser]

    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user.is_active = True
            user.save()
            return Response({"message" : f"{user.get_full_name()} {user.role} account system restored."})
        except User.DoesNotExist:
            return Response({"error" : "User not found"}, status=404)

class AdminManageDoctorView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from django.db.models import Count as Dcount, Q
        today = timezone.now().date()
        status = request.query_params.get('status', 'all')
        search = request.query_params.get('search', '')
        doctors = User.objects.filter(role='doctor').select_related('doctor_profile').order_by('-date_joined')
        specialities = request.query_params.get('specialities', 'all')
        if specialities != 'all':
            doctors = doctors.filter(doctor_profile__specialization__iexact=specialities)
        if status == 'pending':
            doctors = doctors.filter(doctor_profile__license_number__startswith='PENDING')
        elif status == 'approved':
            doctors = doctors.exclude(doctor_profile__license_number__startswith='PENDING')
        elif status == 'suspended':
            doctors = doctors.filter(is_active=False)
        if search:
            doctors = doctors.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(email__icontains=search) | Q(doctor_profile__specialization__icontains=search))

        specialization_counts = DoctorProfile.objects.values('specialization').annotate(count=Dcount('id')).order_by('-count')[:5]  

        paginator = CustomPagination()
        paginated_doctors = paginator.paginate_queryset(doctors, request)
        
        current_month_start = today.replace(day=1)
        previous_month_end = current_month_start - timedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1)
        # total_users = User.objects.count()
        total_doctors = User.objects.filter(role='doctor').count()
        total_active_doctors = User.objects.filter(role='doctor', is_active=True).count()
        total_suspended_doctors = User.objects.filter(role='doctor', is_active=False).count()
        total_pending_approval = User.objects.filter(role='doctor', doctor_profile__license_number__startswith='PENDING').count()
        # doctor_percentage = round((total_doctors / total_users * 100), 1) if total_users > 0 else 0
        # suspended_doctor_percentage = round((total_suspended_doctors / total_doctors * 100), 1) if total_doctors > 0 else 0
        
        days_elapsed = (today - current_month_start).days
        previous_month_comparison_date = min(previous_month_start + timedelta(days=days_elapsed), previous_month_end)        
        current_doctor = User.objects.filter(role='doctor', date_joined__date__gte=current_month_start, date_joined__date__lte=today).count()
        previous_doctor = User.objects.filter(role='doctor', date_joined__date__gte=previous_month_start, date_joined__date__lte=previous_month_comparison_date).count()

        current_active_doctor = User.objects.filter(role='doctor', is_active=True, date_joined__date__gte=current_month_start, date_joined__date__lte=today).count()
        previous_active_doctor = User.objects.filter(role='doctor', is_active=False, date_joined__date__gte=previous_month_start, date_joined__date__lte=previous_month_comparison_date).count()

        current_suspended_doctor = User.objects.filter(role='doctor', is_active=False, date_joined__date__gte=current_month_start, date_joined__date__lte=today).count()
        previous_suspended_doctor = User.objects.filter(role='doctor', is_active=False, date_joined__date__gte=previous_month_start, date_joined__date__lte=previous_month_comparison_date).count()

        current_pending_approval = User.objects.filter(role='doctor', doctor_profile__license_number__startswith='PENDING', date_joined__date__gte=current_month_start, date_joined__date__lte=today).count()
        previous_pending_approval = User.objects.filter(role='doctor', doctor_profile__license_number__startswith='PENDING', date_joined__date__gte=previous_month_start, date_joined__date__lte=previous_month_comparison_date).count()
        
        doctors_change = format_stat_payload(current_doctor, previous_doctor)
        active_change = format_stat_payload(current_active_doctor, previous_active_doctor)
        suspended_change = format_stat_payload(current_suspended_doctor, previous_suspended_doctor)
        pending_change = format_stat_payload(current_pending_approval, previous_pending_approval)
        doctors_data = [
            {
                "id" : d.id,
                "name" : f"Dr. {d.get_full_name()}",
                "email" : d.email,
                "phone" : getattr(d, 'phone_number', ''),
                "initials" : f"{d.first_name[:1]}{d.last_name[:1]}".upper(),
                "specialization" : getattr(getattr(d, 'doctor_profile', None), 'specialization', ''),
                "experience" : getattr(getattr(d, 'doctor_profile', None), 'years_of_experience', ''),
                "bio" : getattr(getattr(d, 'doctor_profile', None), 'bio', ''),
                "consultation_fee" : getattr(getattr(d, 'doctor_profile', None), 'consultation_fee', ''),
                "license_number" : getattr(getattr(d, 'doctor_profile', None), 'license_number', ''),
                "is_pending" : getattr(getattr(d, 'doctor_profile', None), 'license_number', '').startswith('PENDING'),
                "is_active" : d.is_active,
                "is_available_days" : getattr(getattr(d, 'doctor_profile', None), 'available_days', True),
                "date_joined" : d.date_joined.strftime('%b %d, %Y'),

            } for d in paginated_doctors
        ]
        
        return Response({
            "pagination" : {
                "count" : paginator.page.paginator.count,
                "next" : paginator.get_next_link(),
                "previous" : paginator.get_previous_link(),
                "current_page" : paginator.page.number,
                "total_pages" : paginator.page.paginator.num_pages
            },
            "stats" : {
                "total_doctors" : total_doctors,
                "active_doctors" : total_active_doctors,
                "suspended_doctors" : total_suspended_doctors,
                "pending_approval" : total_pending_approval,
                "doctors_change" : doctors_change,
                "active_change" : active_change,
                "suspended_change" : suspended_change,
                "pending_change" : pending_change,
            },
            # "pending_approval" : pending_approval,
            "specialization_counts" : list(specialization_counts),
            "doctors" : doctors_data
        })
        

class AdminApproveDoctorView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, doctor_id):
        try:
            doctor = User.objects.get(id=doctor_id, role='doctor')
            profile = getattr(doctor, 'doctor_profile', None)
            license_number = request.data.get('license_number', '').strip()

            if not license_number and profile:
                license_number = profile.license_number
                # return Response({"error" : "License number is required."}, status=400)

            if license_number.startswith('PENDING'):
                license_number = license_number.replace('PENDING-', '')

            if profile:
                profile.license_number = license_number
                profile.is_available = True
                profile.save()

            doctor.is_active = True
            doctor.save()

            Notification.objects.create(
                recipient = doctor,
                title = 'Your account has been approved',
                body = 'Your LifeCare doctor account has been verified. You can now reciever appointments',
                type='general'
            )

            try:
                from notifications.emails import _send

                _send(
                    subject = "Doctor Account Approved - LifeCare",
                    message=f"""Hi Dr. {doctor.get_full_name()},
Your LifeCare doctor account has been approved and verified.

License number: {license_number}

You can now log in and start recieving patient appointments

https://life-care-websites.vercel.app/login
- The LifeCare Team""",
                    recipient=doctor.email
                )
            except Exception as e:
                print(f"Approval email failed: {e}")

            return Response({"message" : f"Dr. {doctor.get_full_name()} approved."})

        except User.DoesNotExist:
            return Response({"error" : "Doctor not found"}, status=404)

    def delete(self, request, doctor_id):
        try:
            doctor = User.objects.filter(role='doctor', id=doctor_id)
            doctor.delete()
            return Response({"message" : "Doctor deleted."}, status=204)
        except User.DoesNotExist:
            return Response({"error" : "Doctor not found."}, status=404)

        
class AdminRejectDoctorView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, doctor_id):
        try:
            doctor = User.objects.get(id=doctor_id, role='doctor')
            reason = request.data.get('reason', 'Your application did not meet our requirements')
            doctor.is_active = False
            doctor.save()
            try:
                from notifications.emails import _send
                _send(
                    subject='Doctor Account Application - LifeCare',
                    message=f"""Hi Dr. {doctor.get_full_name()}
Thank you for applying to join LifeCare.
After review, we were unable to approve your account at this time.
Reason: {reason}

Please contact support if you have questions.
- The LifeCare Team""",
                    recipient=doctor.email
                )
            except Exception as e:
                print(f"Rejection email failed: {e}")

            return Response({"message" : "Doctor Rejected"})
        except User.DoesNotExist:
            return Response({"error" : "Doctor not found"}, status=404)


class AdminManageAppointmentView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        today = timezone.now().date()
        qs = Appointment.objects.all().select_related('patient', 'doctor').order_by('-created_at')
        status = request.query_params.get('status', 'all')
        search = request.query_params.get('search', '')
        specialities = request.query_params.get('specialities', 'all')

        if specialities != 'all':
            qs = qs.filter(doctor__doctor_profile__specialization__iexact=specialities)

        if status != 'all':
            qs = qs.filter(status=status)

        if search:
            qs = qs.filter(Q(patient__first_name__icontains=search) | Q(patient__last_name__icontains=search) | Q(doctor__first_name__icontains=search) | Q(doctor__last_name__icontains=search) | Q(doctor__doctor_profile__specialization__icontains=search))

        paginator = CustomPagination()
        paginated_appointments = paginator.paginate_queryset(qs, request)

        current_month_start = today.replace(day=1)
        previous_month_end = current_month_start - timedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1)

        days_elapsed = (today - current_month_start).days
        previous_month_comparison_date = min(previous_month_start + timedelta(days=days_elapsed), previous_month_end)
        
        total_appts = Appointment.objects.count()
        confirmed_appts = Appointment.objects.filter(status='confirmed').count()
        pending_appts = Appointment.objects.filter(status='pending').count()
        cancelled_appts = Appointment.objects.filter(status='cancelled').count()

        current_total_apt = Appointment.objects.filter(created_at__date__gte=current_month_start, created_at__date__lte=today).count()
        previous_total_apt = Appointment.objects.filter(created_at__date__gte=previous_month_start, created_at__date__lte=previous_month_comparison_date).count()

        current_confirmed_apt = Appointment.objects.filter(status='confirmed', created_at__date__gte=current_month_start, created_at__date__lte=today).count()
        previous_confirmed_apt = Appointment.objects.filter(status='confirmed', created_at__date__gte=previous_month_start, created_at__date__lte=previous_month_comparison_date).count()

        current_pending_apt = Appointment.objects.filter(status='pending', created_at__date__gte=current_month_start, created_at__date__lte=today).count()
        previous_pending_apt = Appointment.objects.filter(status='pending', created_at__date__gte=previous_month_start, created_at__date__lte=previous_month_comparison_date).count()

        current_cancelled_apt = Appointment.objects.filter(status='cancelled', created_at__date__gte=current_month_start, created_at__date__lte=today).count()
        previous_cancelled_apt = Appointment.objects.filter(status='cancelled', created_at__date__gte=previous_month_start, created_at__date__lte=previous_month_comparison_date).count()

        total_apt_change = format_stat_payload(current_total_apt, previous_total_apt)
        confirmed_change = format_stat_payload(current_confirmed_apt, previous_confirmed_apt)
        pending_change = format_stat_payload(current_pending_apt, previous_pending_apt)
        cancelled_change = format_stat_payload(current_cancelled_apt, previous_cancelled_apt)


        apt_data = [
            {
                "id" : apt.id,
                "patient_name" : apt.patient.get_full_name(),
                "patient_email" : apt.patient.email,
                "doctor_name" : apt.doctor.get_full_name(),
                "doctor_email" : apt.doctor.email,
                "department" : getattr(getattr(apt.doctor, 'doctor_profile', None),'specialization', ''),
                "date" : apt.appointment_date,
                "time" : apt.appointment_time,
                "status" : apt.status,
                "reason": apt.reason,
            } for apt in paginated_appointments
        ]
        return Response({
            "pagination" : {
                "count" : paginator.page.paginator.count,
                "next" : paginator.get_next_link(),
                "previous" : paginator.get_previous_link(),
                "current_page" : paginator.page.number,
                "total_pages" : paginator.page.paginator.num_pages
            },
            "stats" : {
                "total_appts" : total_appts,
                "confirmed_appts" : confirmed_appts,
                "pending_appts" : pending_appts,
                "cancelled_appts" : cancelled_appts,
                "total_apt_change" : total_apt_change,
                "confirmed_change" : confirmed_change,
                "pending_change" : pending_change,
                "cancelled_change" : cancelled_change,

            },
            "apt_data" : apt_data, 
        })

    
class AdminDeleteAppointments(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, apt_id):
        try:
            appt = Appointment.objects.filter(id=apt_id)
            appt.delete()
            return Response({"message" : "Appointment deleted successfully!"}, status=204)
        except Appointment.DoesNotExist:
            return Response({"error" : "Appointment not found"}, status=404)
    
class AdminListPatientsView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        patients = User.objects.filter(role='patient')
        data = [
            {
                "id" : p.id,
                "name" : p.get_full_name() if hasattr(p, 'get_full_name') and p.get_full_name() else f"{p.first_name} {p.last_name}".strip() or p.username,
                "email" : p.email,
            } for p in patients
        ]
        return Response(data)
class AdminListDoctorsView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        doctors = User.objects.filter(role='doctor')
        data = [
            {
                "id" : d.id,
                "first_name" : d.first_name,
                "last_name" : d.last_name,
                "email" : d.email
            } for d in doctors
        ]
        return Response(data)

class AdminListUsersView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        users = User.objects.all()
        data = [
            {
                "id" : u.id,
                "name" : u.get_full_name() if hasattr(u, 'get_full_name') and u.get_full_name() else f"{u.first_name} {u.last_name}".strip() or u.username,
                "email" : u.email,
                "role" : u.role,
            } for u in users
        ]
        return Response(data)


class AdminManagePrescriptions(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        status = request.query_params.get('status', 'all')
        search = request.query_params.get('search', '')
        doctor_id = request.query_params.get('doctors', 'all')
        prescription = Prescription.objects.all().select_related('patient', 'doctor').order_by('-prescribed_date')
        if status != 'all':
            prescription = prescription.filter(status=status)
        if search:
            prescription = prescription.filter(Q(patient__first_name__icontains=search) | Q(patient__last_name__icontains=search) | Q(doctor__first_name__icontains=search) | Q(doctor__last_name__icontains=search) | Q(medication_name__icontains=search))

        if doctor_id !='all':
            prescription = prescription.filter(doctor_id=doctor_id)

        paginator = CustomPagination()
        paginated_prescription = paginator.paginate_queryset(prescription, request)
        
        
        total_prep = Prescription.objects.count()
        completed_prep = Prescription.objects.filter(status='completed').count()
        active_prep = Prescription.objects.filter(status='active').count()
        cancelled_prep = Prescription.objects.filter(status='cancelled').count()

        today = timezone.now().date()
        current_month_start = today.replace(day=1)
        previous_month_end = current_month_start - timedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1)

        days_elapsed = (today - current_month_start).days
        previous_month_comparison_date = min(previous_month_start + timedelta(days=days_elapsed), previous_month_end)

        current_total_prep = Prescription.objects.filter(prescribed_date__gte=current_month_start, prescribed_date__lte=today).count()
        previous_total_prep = Prescription.objects.filter(prescribed_date__gte=previous_month_start, prescribed_date__lte=previous_month_comparison_date).count()

        current_active_prep = Prescription.objects.filter(status='active', prescribed_date__gte=current_month_start, prescribed_date__lte=today).count()
        previous_active_prep = Prescription.objects.filter(status='active', prescribed_date__gte=previous_month_start, prescribed_date__lte=previous_month_comparison_date).count()

        current_completed_prep = Prescription.objects.filter(status='completed', prescribed_date__gte=current_month_start, prescribed_date__lte=today).count()
        previous_completed_prep = Prescription.objects.filter(status='completed', prescribed_date__gte=previous_month_start, prescribed_date__lte=previous_month_comparison_date).count()

        current_cancelled_prep = Prescription.objects.filter(status='cancelled', prescribed_date__gte=current_month_start, prescribed_date__lte=today).count()
        previous_cancelled_prep = Prescription.objects.filter(status='cancelled', prescribed_date__gte=previous_month_start, prescribed_date__lte=previous_month_comparison_date).count()

        total_prep_change = format_stat_payload(current_total_prep, previous_total_prep)
        active_prep_change = format_stat_payload(current_active_prep, previous_active_prep)
        completed_prep_change = format_stat_payload(current_completed_prep, previous_completed_prep)
        cancelled_prep_change = format_stat_payload(current_cancelled_prep, previous_cancelled_prep)

        prep_info = [
            {
                "id" : prep.id,
                "patient" : prep.patient.get_full_name(),
                "patient_email" : prep.patient.email,
                "doctor" : prep.doctor.get_full_name(),
                "doctor_email" : prep.doctor.email,
                "medication" : prep.medication_name,
                "notes" : prep.notes,
                "dosage" : prep.dosage,
                "frequency" : prep.frequency,
                "duration" : prep.duration,
                "status" : prep.status,
                "prescribed_date" : prep.prescribed_date,
            } for prep in paginated_prescription
        ]
        return Response({
            "pagination" : {
                "count" : paginator.page.paginator.count,
                "next" : paginator.get_next_link(),
                "previous" : paginator.get_previous_link(),
                "current_page" : paginator.page.number,
                "total_pages" : paginator.page.paginator.num_pages
            },

            "stats" : {
                "total_prep" : total_prep,
                "completed_prep" : completed_prep,
                "active_prep" : active_prep,
                "cancelled_prep" : cancelled_prep,
                "total_prep_change" : total_prep_change,
                "active_prep_change" : active_prep_change,
                "completed_prep_change" : completed_prep_change,
                "cancelled_prep_change" : cancelled_prep_change,
            },
            "prep_data" : prep_info,
        })

    
class AdminManageRecords(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        record_type = request.query_params.get('recordType', 'all')
        search = request.query_params.get('search', '').strip()    
        patient = request.query_params.get('patients', 'all')            
        records = MedicalRecords.objects.all().select_related('patient', 'doctor').order_by('-created_at')
        if record_type != 'all':
            records = records.filter(record_type=record_type)

        if search:
            records = records.filter(Q(patient__first_name__icontains=search) | Q(patient__last_name__icontains=search) | Q(doctor__first_name__icontains=search) | Q(doctor__last_name__icontains=search) | Q(title__icontains=search))

        if patient != 'all':
            records = records.filter(patient_id=patient)

        paginator = CustomPagination()
        paginated_records = paginator.paginate_queryset(records, request)

        total_records = MedicalRecords.objects.count()
        total_lab_results = MedicalRecords.objects.filter(record_type='lab_result').count()
        total_diagnosis_results = MedicalRecords.objects.filter(record_type='diagnosis').count()
        total_general_results = MedicalRecords.objects.filter(record_type='general').count()

        today = timezone.now().date()
        current_month_start = today.replace(day=1)
        previous_month_end = current_month_start - timedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1)
        days_elapsed = (today - current_month_start).days
        previous_month_comparison_date = min(previous_month_start + timedelta(days=days_elapsed), previous_month_end)

        current_total_records = MedicalRecords.objects.filter(created_at__date__gte=current_month_start, created_at__date__lte=today).count()
        previous_total_records = MedicalRecords.objects.filter(created_at__date__gte=previous_month_start, created_at__date__lte=previous_month_comparison_date).count()

        current_total_lab_results = MedicalRecords.objects.filter(record_type='lab_result', created_at__date__gte=current_month_start, created_at__date__lte=today).count()
        previous_total_lab_results = MedicalRecords.objects.filter(record_type='lab_result', created_at__date__gte=previous_month_start, created_at__date__lte=previous_month_comparison_date).count()

        current_total_diagnosis_results = MedicalRecords.objects.filter(record_type='diagnosis', created_at__date__gte=current_month_start, created_at__date__lte=today).count()
        previous_total_diagnosis_results = MedicalRecords.objects.filter(record_type='diagnosis', created_at__date__gte=previous_month_start, created_at__date__lte=previous_month_comparison_date).count()

        current_total_general_results = MedicalRecords.objects.filter(record_type='general', created_at__date__gte=current_month_start, created_at__date__lte=today).count()
        previous_total_general_results = MedicalRecords.objects.filter(record_type='general', created_at__date__gte=previous_month_start, created_at__date__lte=previous_month_comparison_date).count()

        total_records_change = format_stat_payload(current_total_records, previous_total_records)
        total_lab_result_change = format_stat_payload(current_total_lab_results, previous_total_lab_results)
        total_diagnosis_result_change = format_stat_payload(current_total_diagnosis_results, previous_total_diagnosis_results)
        total_general_result_change = format_stat_payload(current_total_general_results, previous_total_general_results)

        records_data = [
            {
                "id" : r.id,
                "patient" : r.patient.get_full_name() if r.patient else None,
                "doctor" : r.doctor.get_full_name() if r.doctor else None,
                "title" : r.title,
                "record_type" : r.record_type,
                "description" : r.description,
                "file" : r.file.url if r.file else None,
                "date" : r.date_recorded,
                "created_at" : r.created_at,
            } for r in paginated_records
        ]

        return Response({
            "pagination" : {
                "count" : paginator.page.paginator.count,
                "next" : paginator.get_next_link(),
                "previous" : paginator.get_previous_link(),
                "current_page" : paginator.page.number,
                "total_page" : paginator.page.paginator.num_pages
            },
            "stats" : {
                "total_records" : total_records,
                "total_lab_results" : total_lab_results,
                "total_diagnosis_results" : total_diagnosis_results,
                "total_general_results" : total_general_results,
                "total_records_change" : total_records_change,
                "total_lab_results_change" : total_lab_result_change,
                "total_diagnosis_result_change" : total_diagnosis_result_change,
                "total_general_result_change" : total_general_result_change,
            },
            "records_data" : records_data,
            
        })

class AdminManageNotification(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        filter_type = request.query_params.get('filter_type', 'all')
        status = request.query_params.get('status', 'all')
        search = request.query_params.get('search', '')
        notification = Notification.objects.select_related('recipient').order_by('-created_at')
        
        if filter_type != 'all':
            notification = notification.filter(type=filter_type)

        if search:
            notification = notification.filter(Q(recipient__first_name__icontains=search) | Q(recipient__last_name__icontains=search) | Q(title__icontains=search))
        
        if status != 'all':
            notification = notification.filter(is_read=status)
        
        paginator = CustomPagination()
        paginated_notif = paginator.paginate_queryset(notification, request)
        
        notif_data = [
            {
                "id" : notif.id,
                "recipient" : f"{notif.recipient.first_name} {notif.recipient.last_name}".strip() or notif.username,
                "role" : notif.recipient.role,
                "recipient_email" : notif.recipient.email,
                "title" : notif.title,
                "message" : notif.body,
                "type" : notif.type,
                "is_read" : notif.is_read,
                "date" : notif.created_at.strftime('%Y-%m-%d %H:%M:%S') if notif.created_at else None,
            } for notif in paginated_notif
        ]

        return Response({
            "pagination" : {
                "count" : paginator.page.paginator.count,
                "next" : paginator.get_next_link(),
                "previous" : paginator.get_previous_link(),
                "current_page" : paginator.page.number,
                "total_page" : paginator.page.paginator.num_pages,
            },
            "notif_data" : notif_data,
        })

    def post(self, request):
        from notifications.emails import send_notification_email

        title = request.data.get('title', '').strip()
        body = request.data.get('body', '').strip()
        recipient_id = request.data.get('recipient')
        notif_type = request.data.get('type', 'general')

        if not title or not body or not recipient_id:
            return Response({"error" : "Recipient, title and body are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            recipient = User.objects.get(id=recipient_id, is_active=True)
        except User.DoesNotExist:
            return Response({"error" : "Selected user does not exist or is in active"}, status=status.HTTP_404_NOT_FOUND)
        
        
        notif = Notification.objects.create(
            recipient = recipient,
            title=title,
            body=body,
            type=notif_type
        )

        try:
            send_notification_email(notif)
        except Exception as e:
            print(f"Notification email failed: {e}")

        return Response({
            "message" : "Notification created successfully.",
            "notification" : {
                "id" : notif.id,
                "recipient" : {
                    "id" : notif.recipient.id,
                    "name" : notif.recipient.get_full_name(),
                    "role" : notif.recipient.role,
                },
                "title" : notif.title,
                "body" : notif.body,
                "type" : notif.type
            }
        }, status=status.HTTP_201_CREATED)

class AdminDeleteNotification(APIView):
    def delete(self, request, notif_id):
        try:
            notif = Notification.objects.filter(id=notif_id)
            notif.delete()
            return Response({"message" : "Notification deleted. "}, status=status.HTTP_204_NO_CONTENT)
        except Notification.DoesNotExist:
            return Response({"error" : "Notification not found"}, status=status.HTTP_404_NOT_FOUND)


class AdminManageMessage(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        status_filter = request.query_params.get('status', 'all')
        search = request.query_params.get('search', '').strip()

        conversations = Conversation.objects.select_related('patient', 'doctor').annotate(last_activity=Max('messages__created_at')).order_by('-last_activity')
        total_conversations = conversations.count()
        active_conversations = conversations.filter(messages__isnull=False).distinct().count()
        pending_conversations = conversations.filter(messages__is_read=False).distinct().count()
        
        if status_filter != 'all':
            if status_filter == 'active':
                conversations = conversations.filter(messages__isnull=False).distinct()
            elif status_filter == 'pending':
                conversations = conversations.filter(messages__is_read=False).distinct()

        if search:
            conversations = conversations.filter(Q(patient__first_name__icontains=search) | Q(patient__last_name__icontains=search) | Q(patient__username__icontains=search) | Q(doctor__first_name__icontains=search) | Q(doctor__last_name__icontains=search) | Q(messages__body__icontains=search) | Q(doctor__username__icontains=search))

        paginator = CustomPagination()
        paginated_cons = paginator.paginate_queryset(conversations, request)

        conversation_data = []

        for conv in paginated_cons:
            last_msg = conv.messages.order_by('-created_at').first()
            patient_name = conv.patient.get_full_name() if hasattr(conv.patient, 'get_full_name') else f"{conv.patient.first_name} {conv.patient.last_name}".strip()
            patient_display = patient_name or conv.patient.username

            doctor_name = conv.doctor.get_full_name() if hasattr(conv.doctor, 'get_full_name') else f"{conv.doctor.first_name} {conv.doctor.last_name}".strip()
            doctor_display = doctor_name or conv.doctor.username

            patient_initials = "".join([part[0] for part in patient_display.split() if part]).upper() or "P"
            doctor_initials = "".join([part[0] for part in doctor_display.split() if part]).upper() or "D"
            
            conversation_data.append({
                "id" : conv.id,
                "patient" : {
                    "id" : conv.patient.id,
                    "name" : patient_display,
                    "email" : conv.patient.email,
                    "initials" : patient_initials,
                    "avatar" : request.build_absolute_uri(conv.patient.profile_picture.url) if getattr(conv.patient, 'profile_picture', None) else None,

                },
                "doctor" : {
                    "id" : conv.doctor.id,
                    "email" : conv.doctor.email,
                    "name" : doctor_display,
                    "initials" : doctor_initials,
                    "avatar" : request.build_absolute_uri(conv.doctor.profile_picture.url) if getattr(conv.doctor, 'profile_picture', None) else None,
                },
                "last_message" : last_msg.body if last_msg and last_msg.body else ('File attached' if last_msg and last_msg.file else "No messages yet."),
                "last_activity" : conv.updated_at.strftime('%b %d, %Y') if conv.updated_at else None,
                "status" : "Active" if conv.messages.exists() else "Pending"
            })

        return Response({
            "stats" : {
                "total_conversations" : total_conversations,
                "active_conversations" : active_conversations,
                "pending_conversations" : pending_conversations
            },
            "pagination" : {
                'count' : paginator.page.paginator.count,
                "next" : paginator.get_next_link(),
                "previous" : paginator.get_previous_link(),
                "current_page" : paginator.page.number,
                "total_pages" : paginator.page.paginator.num_pages,
            },
            "conversations" : conversation_data
        })

class AdminManageConversationsView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        patient_id = request.data.get('patient_id')
        doctor_id = request.data.get('doctor_id')

        if not patient_id or not doctor_id:
            return Response({"error" : "Both patient and doctor are required"}, status=400)

        try:
            patient = User.objects.get(id=patient_id, role='patient')
            doctor = User.objects.get(id=doctor_id, role='doctor')
        except User.DoesNotExist:
            return Response({"error" : "Selected patient or doctor does not exist."}, status=404)

        conversation, created = Conversation.objects.get_or_create(patient=patient, doctor=doctor)

        if not created:
            return Response({"message" : "Conversation already exists between this patient and doctor"}, status=200)
        
        return Response({
            "message" : "Conversation created successfully.",
            "conversation_id" : conversation.id
        }, status=201)

    def delete(self, request, pk):
        try:
            conversation = Conversation.objects.get(pk=pk)
            conversation.delete()
            return Response({"message" : "Conversation deleted successfully"})
        except Conversation.DoesNotExist:
            return Response({"error" : "Conversation not found."}, status=4-4)
