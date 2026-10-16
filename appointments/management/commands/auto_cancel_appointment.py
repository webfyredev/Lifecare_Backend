from django.core.management import BaseCommand
from django.utils import timezone
from datetime import timedelta
from appointments.models import Appointment
from notifications.models import Notification
from notifications.emails import send_appointment_cancelled

class Command(BaseCommand):
    help = 'Auto-cancel appointments not confirmed 24hrs before time'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        cutoff = now + timedelta(hours=24)
        appointments = Appointment.objects.filter(status='pending', appointment_date=cutoff.date(), appointment_time__lte=cutoff.time()).select_related('patient', 'doctor')
        cancelled = 0
        for apt in appointments:
            apt.status = 'cancelled'
            apt.notes = 'Automatically cancelled - doctor did not confirm within 24 hours.'
            apt.save()
            apt.refresh_from_db()

            Notification.objects.create(
                recipient=apt.patient,
                title = 'Appointment Cancelled',
                body = f'Your appointment with Dr. {apt.doctor.get_full_name()} on {apt.appointment_date.strftime("%B %d, %Y")} was automatically cancelled because it was not confirmed in time. Please book a new appointment.',
                type = 'appointment',
            )

            Notification.objects.create(
                recipient = apt.doctor,
                title = 'Appointment Auto-Cancelled',
                body=f'The appointment with {apt.patient.get_full_name()} on {apt.appointment_date.strftime("%B %d, %Y")} was automatically cancelled because it was not confirmed within 24 hours.',
                type = 'appointment',
            )

            try:
                send_appointment_cancelled(apt, cancelled_by='system')
            except Exception as e:
                print(f"Email failed: {e}")
            
            cancelled +=1
            self.stdout.write(f"Cancelled: {apt.patient.get_full_name()} - Dr. {apt.doctor.get_full_name()}")
        self.stdout.write(f"Auto-cancelled {cancelled} appointments")
        
