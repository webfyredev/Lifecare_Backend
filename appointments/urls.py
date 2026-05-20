from django.urls import path
from .views import PatientAppointmentsView, BookAppointmentView, CancelAppointmentView, AvailableDoctorsView
urlpatterns = [
    path('', PatientAppointmentsView.as_view(), name='patient-appointments'),
    path('book/', BookAppointmentView.as_view(), name='book-appointments'),
    path('<int:pk>/cancel/', CancelAppointmentView.as_view(), name='cancel-appointments'),
    path('doctors/', AvailableDoctorsView.as_view(), name='available-doctors')

]