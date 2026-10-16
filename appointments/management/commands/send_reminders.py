from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from appointments.models import Appointment
from notifications.emails import send_appointment_reminder

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        tomorrow = timezone.now().date() + timedelta(days=1)
        appointments = Appointment.objects.filter(appointment_date=tomorrow, status__in=['confirmed', 'pending']).select_related('patient', 'doctor')

        sent = 0

        for apt in appointments:
            try:
                send_appointment_reminder(apt)
                sent+=1
            except Exception as e:
                self.stdout.write(f"Failed for {apt.patient.email}: {e}")

        self.stdout.write(f"Sent {sent} reminders for tomorrow")