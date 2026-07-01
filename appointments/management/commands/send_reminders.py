from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from appointments.models import Appointment
from notifications.emails import send_appointment_reminder

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        tomorrow = timezone.now().date() + timedelta(days=1)
        appointments = Appointment.objects.filter(appointment_date=tomorrow, status__in=['confirmed', 'pending']).select_related('patient', 'doctor')

        for apt in appointments:
            send_appointment_reminder(apt)
            self.stdout.write(f"Remdinder send to {apt.patient.email}")