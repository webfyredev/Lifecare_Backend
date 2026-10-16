from django.db import models
from accounts.models import User
# from appointments.models import Appointment

class MedicalNotes(models.Model):
    SEVERITY_CHOICES = (
        ('normal', 'Normal'),
        ('monitor', 'Monitor'),
        ('critical', 'Critical'),
    )
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes_written')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name= 'medical_notes')
    appointment = models.ForeignKey('appointments.Appointment', on_delete=models.SET_NULL, null=True, blank=True, related_name='medical_notes')
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=50, blank=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='normal')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'MedicalNotes'
        verbose_name_plural = 'MedicalNotes'
    
    def __str__(self):
        return f"{self.title} - {self.patient.get_full_name()}"
    