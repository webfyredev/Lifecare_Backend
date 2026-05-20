from django.contrib import admin
from .models import Appointment
from django import forms
from accounts.models import User

class AppointmentAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = User.objects.filter(role='patient')
        self.fields['doctor'].queryset = User.objects.filter(role='doctor')

    class Meta:
        model = Appointment
        fields = '__all__'


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    form = AppointmentAdminForm
    list_display = ('patient', 'doctor', 'appointment_date', 'appointment_time', 'status')
    list_filter = ('status', 'appointment_date')
    search_fields = (
        'patient__first_name', 'patient__last_name',
        'doctor__first_name', 'doctor__last_name',
    )