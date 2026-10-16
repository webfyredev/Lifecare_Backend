from django.urls import path
from .views import (
    PatientAppointmentsView, BookAppointmentView, CancelAppointmentView, 
    AvailableDoctorsView, RescheduleAppointmentView, DoctorAppointmentsView,
    ConfirmAppointmentView, CompleteAppointmentView
)
urlpatterns = [
    path('', PatientAppointmentsView.as_view(), name='patient-appointments'),
    path('book/', BookAppointmentView.as_view(), name='book-appointments'),
    path('<int:pk>/cancel/', CancelAppointmentView.as_view(), name='cancel-appointments'),
    path('doctors/', AvailableDoctorsView.as_view(), name='available-doctors'),
    path('<int:pk>/reschedule/', RescheduleAppointmentView.as_view(), name='reschedule-appointment'),

    # Doctor routes

    path('doctor/', DoctorAppointmentsView.as_view(), name='doctor-appointments'),
    path('<int:pk>/confirm/', ConfirmAppointmentView.as_view(), name='confirm-appointments'),
    path('<int:pk>/complete/', CompleteAppointmentView.as_view(), name='complete-appointments')

]