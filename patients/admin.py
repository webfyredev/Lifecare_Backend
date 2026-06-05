from django.contrib import admin
from .models import PatientProfile, Prescription, MedicalRecords
from django import forms
from accounts.models import User


class PrescriptionAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = User.objects.filter(role='patient')
        self.fields['doctor'].queryset = User.objects.filter(role='doctor')

    class Meta:
        model = Prescription
        fields = '__all__'

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    form = PrescriptionAdminForm
    list_display = ('patient', 'doctor', 'medication_name', 'status', 'prescribed_date')
    list_filter = ('status',)
    search_fields = ('patient__first_name', 'medication_name')


class PatientProfileAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(role='patient')
    class Meta:
        model = PatientProfile
        fields = '__all__'


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    form = PatientProfileAdminForm
    list_display = ('user', 'blood_type', 'insurance_number')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'blood_type', 'insurance_number')
    list_filter = ('blood_type',)

class MedicalRecordAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = User.objects.filter(role='patient')
        self.fields['doctor'].queryset = User.objects.filter(role='doctor')

    class Meta:
        model = MedicalRecords
        fields = "__all__"

@admin.register(MedicalRecords)
class MedicalRecordAdmin(admin.ModelAdmin):
    form = MedicalRecordAdminForm
    list_display = ('title', 'patient', 'record_type', 'date_recorded')
    list_filter = ('record_type',)
    search_fields = ('title', 'patient__first_name', 'patient__last_name')

    

