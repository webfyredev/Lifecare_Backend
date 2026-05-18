from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('admin', 'Admin'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return f'{self.get_full_name()} ({self.role})'

    @property
    def is_patient(self):
        return self.role == 'patient'

    @property
    def is_doctor(self):
        return self.role == 'doctor'