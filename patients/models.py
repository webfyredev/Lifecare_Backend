from django.db import models
from accounts.models import User
import uuid

class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    hospital_number = models.CharField(max_length=20, unique=True, blank=True)
    blood_type = models.CharField(max_length=5, blank=True)
    allergies = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    insurance_number = models.CharField(max_length=50, blank=True)
    medical_history = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_hospital_number(self):
        from django.utils import timezone
        year = timezone.now().year
        uid = str(uuid.uuid4().int)[:6]
        return f"LC-{year}-{uid}"
    
    def save(self, *args, **kwargs):
        if not self.hospital_number:
            number = self.generate_hospital_number()
            while PatientProfile.objects.filter(hospital_number=number).exists():
                number = self.generate_hospital_number()
            self.hospital_number = number
        
        super().save(*args, **kwargs)
    def __str__(self):
        return f"Patient: {self.user.get_full_name()} [{self.hospital_number}]"

class Prescription(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescribed_by')
    medication_name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50)   
    frequency = models.CharField(max_length=50)
    duration = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True)
    prescribed_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.medication_name} for {self.patient.get_full_name()}"


class MedicalRecords(models.Model):
    
    RECORDS_TYPE_CHOICES = (
        ('lab_result', 'Lab Result'),
        ('imaging', 'Imaging'),
        ('diagnosis', 'Diagnosis'),
        ('surgery', 'Surgery'),
        ('vaccination', 'Vaccination'),
        ('allergy', 'Allergy'),
        ('general', 'General')

    )

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medical_records')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='records_created', null=True, blank=True)
    title = models.CharField(max_length=200)
    record_type = models.CharField(max_length=20, choices=RECORDS_TYPE_CHOICES, default='general')
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='medical_records/', blank=True, null=True)
    date_recorded = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'MedicalRecords'
        verbose_name_plural = 'MedicalRecords'

        ordering = ['-date_recorded']
    
    def __str__(self):
        return f"{self.title} - {self.patient.get_full_name()}"

