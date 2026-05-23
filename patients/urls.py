from django.urls import path
from .views import PatientDashboardView, PatientPrescriptionView, PatientProfileUpdateView

urlpatterns = [
    path('dashboard/', PatientDashboardView.as_view(), name='patient-dashboard'),
    path('prescriptions/', PatientPrescriptionView.as_view(), name='patient-prescriptions'),
    path('profile/update/', PatientProfileUpdateView.as_view(), name='patient-profile-update')
    # path('profile/', Profile/)
]