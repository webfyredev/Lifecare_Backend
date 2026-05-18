from django.contrib import admin
from .models import PatientProfile
from django import forms
from accounts.models import User

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
    

