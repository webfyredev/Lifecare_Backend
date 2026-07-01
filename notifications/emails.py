from django.core.mail import send_mail
from django.template.loader import render_to_string

def send_appointment_reminder(appointment):
    patient = appointment.patient
    send_mail(
        subject='Appointment Reminder - LifeCare',
        message=f"""

Hi {patient.first_name},

This is a reminder that you have an upcoming appointment:

Doctor: Dr. {appointment.doctor.get_full_name()}
Date: {appointment.appointment_date.strftime('%A, %B %d, %Y')}
Time: {appointment.appointment_time.strftime('%I:%M %P')}
Location: {appointment.location}

Log in to your portal to reschedule or cancel.
https://life-care-websites.vercel.app/login

- LifeCare Team
        """,
        from_email=None,
        recipient_list=[patient.email],
        fail_silently=True
    )


def send_appointment_confirmed(appointment):
    patient = appointment.patient
    send_mail(
        subject='Appointment Confirmed - LifeCare',
        message=f"""
Hi {patient.first_name},

Your appointment has been confirmed by Dr. {appointment.doctor.get_full_name()}.

Date: {appointment.appointment_date.strftime('%A, %B %d, %Y')}
Time: {appointment.appointment_time.strftime('%I:%M %p')}

See you soon!
- LifeCare Team

        """,
        from_email=None,
        recipient_list=[patient.email],
        fail_silently=True,

    )


def send_unread_message_alert(message):
    recipient = message.conversation.patient if message.sender.role == 'doctor' else message.conversation.doctor
    sender_name = f"Dr. {message.sender.get_full_name()}" if message.sender.role == 'doctor' else message.sender.get_full_name()

    send_mail(
        subject=f"New message from {sender_name} -- LifeCare",
        message=f"""
Hi {recipient.first_name},

You have an unread message from {sender_name}

Log in to your portal to respond:
https://life-care-websites.vercel.app/login

- LifeCare Team

        """,
        from_email=None,
        recipient_list=[recipient.email],
        fail_silently=True,
    )


def send_welcome_email(user, hospital_number=None):
    send_mail(
        subject="Welcome to LifeCare",
        message=f"""
Hi {user.first_name},

Welcome to LifeCare! Your account has been created successsfully.

{"Your hospital number is: " + hospital_number if hospital_number else ""}

Log in to complete your profile:
https://life-care-websites.vercel.app/login

- LifeCare Team
        """,
        from_email=None,
        recipient_list=[user.email],
        fail_silently=True
    )