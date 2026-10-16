from django.urls import path
from .views import PatientDashboardView, PatientPrescriptionView, PatientProfileUpdateView, PatientRecordsView, VitalsLogView, DrugInfoView, AllergyInfoView, AddRecordView, RecordsDetailsView

urlpatterns = [
    path('dashboard/', PatientDashboardView.as_view(), name='patient-dashboard'),
    path('prescriptions/', PatientPrescriptionView.as_view(), name='patient-prescriptions'),
    path('profile/update/', PatientProfileUpdateView.as_view(), name='patient-profile-update'),
    path('records/', PatientRecordsView.as_view(), name='patient-records'),
    path('vitals/', VitalsLogView.as_view(), name='vitals'),
    path('drug-info/', DrugInfoView.as_view(), name='drugs-details'),
    path('allergy_info/', AllergyInfoView.as_view(), name='allergy_info'),
    path('records/add/', AddRecordView.as_view(), name='add-record'),
    path('records/<int:pk>/', RecordsDetailsView.as_view(), name='manage-records'),
]