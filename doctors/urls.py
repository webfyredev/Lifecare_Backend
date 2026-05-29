from django.urls import path
from .views import DoctorDashboardView, DoctorPatientView, PatientDetailsView, DoctorPrescriptionView, DoctorPrescriptionDetailsView, DoctorProfileUpdateView

urlpatterns = [
    path('dashboard/', DoctorDashboardView.as_view(), name='doctor-dashboard'),
    path('patients/', DoctorPatientView.as_view(), name='doctor-patients'),
    path('patients/<int:patient_id>/', PatientDetailsView.as_view(), name='patient-detail'),
    path('prescriptions/', DoctorPrescriptionView.as_view(), name='doctor-prescriptions'),
    path('prescriptions/<int:pk>/', DoctorPrescriptionDetailsView.as_view(), name='doctor-prescription-detail'),
    path('profile/', DoctorProfileUpdateView.as_view(), name='doctor-profile')
]