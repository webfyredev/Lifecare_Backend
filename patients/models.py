from django.db import models
from accounts.models import User

class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    blood_type = models.CharField(max_length=5, blank=True)
    allergies = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    insurance_number = models.CharField(max_length=50, blank=True)
    medical_history = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Patient: {self.user.get_full_name()}"

class Prescription(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescribed_by')
    medication_name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50)        # e.g. "500mg"
    frequency = models.CharField(max_length=50)     # e.g. "Twice daily"
    duration = models.CharField(max_length=50)      # e.g. "30 days"
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True)
    prescribed_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.medication_name} for {self.patient.get_full_name()}"
