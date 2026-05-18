from django.urls import path
from .views import DoctorDashboardView

urlpatterns = [
    path('dashboard/', DoctorDashboardView.as_view(), name='doctor-dashboard'),
]