from django.urls import path
from .views import PatientDashboardView

urlpatterns = [
    path('dashboard/', PatientDashboardView.as_view(), name='patient-dashboard'),
]