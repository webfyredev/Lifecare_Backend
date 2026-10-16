from django.contrib import admin
from django import forms
from accounts.models import User
from .models import MedicalNotes
class MedicalNoteAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doctor'].queryset = User.objects.filter(role='doctor')
        self.fields['patient'].queryset = User.objects.filter(role='patient')
    
    class Meta:
        model = MedicalNotes
        fields = '__all__'

@admin.register(MedicalNotes)

class MedicalNotesAdmin(admin.ModelAdmin):
    form = MedicalNoteAdminForm
    list_display = ('title', 'doctor', 'patient', 'severity', 'category', 'created_at')
    list_filter = ('severity', 'category')
    search_fields = ('title', 'doctor__last_name', 'patient__last_name')
    readonly_fields = ('created_at', 'updated_at')
