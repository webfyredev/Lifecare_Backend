from django.contrib import admin
from .models import DoctorProfile
from django import forms
from accounts.models import User

class DoctorProfileAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(role='doctor')
    class Meta:
        model = DoctorProfile
        fields = '__all__'

@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    form = DoctorProfileAdminForm
    list_display = ('user', 'specialization', 'license_number', 'is_available')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'specialization', 'license_number')
    list_filter = ('specialization', 'is_available')