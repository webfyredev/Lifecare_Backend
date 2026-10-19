from django.core.mail import send_mail
from django.conf import settings
import resend
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = getattr(settings, 'BREVO_API_KEY', '')

def _send(subject, message, recipient):
    try:
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        sender_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'oyinbook@gmail.com')
        
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": recipient}],
            html_content=message.replace("\n", "<br>"),
            sender={"name": "LifeCare Team", "email": sender_email},
            subject=subject
        )
        
        response = api_instance.send_transac_email(send_smtp_email)
        print(f"Email sent via Brevo to {recipient}: {subject}")
        return response
    except ApiException as e:
        print(f"Brevo API error for {recipient}: {e}")
    except Exception as e:
        print(f"Email failed to {recipient}: {e}")

    

def send_welcome_email(user, hospital_number=None):

    role = getattr(user, 'role', 'patient').lower()
    if role == 'doctor':
        subject = "Welcome to LifeCare - Doctor Portal"
        greeting = f"Hi Dr. {user.first_name} {user.last_name},"
        specific_line = "Your license number is: PENDING-LC. Kindly log in to update it on your portal."
    elif role == 'admin':
        subject = "Welcome to LifeCare - Admin Portal"
        greeting = f"Hi {user.first_name} {user.last_name},"
        specific_line = "Your administrative account has been created successfully."
    else:
        subject = "Welcome to LifeCare - Patient Portal"
        greeting = f"Hi {user.first_name} {user.last_name},"
        hospital_line = f"Your hospital number is: {hospital_number}\n" if hospital_number else ""
        specific_line = f"{hospital_line} Keep this email - your hospital number is your unique identifier at LifeCare."

    
    message = f"""{greeting}
Welcome to LifeCare! Your account has been created successfully.

{specific_line}

Log in to your portal:

https://life-care-websites.vercel.app/login


- The LifeCare Team"""

    _send(
        subject=subject,
        message=message,
        recipient=user.email,
    )


def send_appointment_booked(appointment):
    patient = appointment.patient
    _send(
        subject="Appointment Booked - LifeCare",
        message= f"""Hi {patient.first_name}

Your appointment has been booked successfully.

Doctor: Dr. {appointment.doctor.get_full_name()}
Date : {appointment.appointment_date.strftime('%A, %B %d, %Y')}
Time: {appointment.appointment_time.strftime('%I:%M %p')}
Location: {appointment.location}
Status: Pending confirmation

You will recieve another email once the doctor confirms

Log in to manage your appointments

https://life-care-websites.vercel.app/login

-The LifeCare Team""",
        recipient=patient.email,
    )

def send_appointment_reminder(appointment):
    patient = appointment.patient
    _send(
        subject='Appointment Reminder - LifeCare',
        message=f"""

Hi {patient.first_name},

This is a reminder that you have an upcoming appointment:

Doctor: Dr. {appointment.doctor.get_full_name()}
Date: {appointment.appointment_date.strftime('%A, %B %d, %Y')}
Time: {appointment.appointment_time.strftime('%I:%M %p')}
Location: {appointment.location}

Need to reschedule? Log in here:

Log in to your portal to reschedule or cancel.
https://life-care-websites.vercel.app/login

- LifeCare Team
        """,
        recipient=patient.email,
    )


def send_appointment_confirmed(appointment):
    patient = appointment.patient
    _send(
        subject="Appointment Confirmed - LifeCare",
        message= f"""Hi {patient.first_name},

Great news! Your appointment has been confirmed.

Doctor: Dr. {appointment.doctor.get_full_name()}
Date: {appointment.appointment_date.strftime('%A, %B %d, %Y')}
Time: {appointment.appointment_time.strftime('%I:%M %p')}
Location: {appointment.location}

Please arrive 10 minutes early.

See you soon!

- The LifeCare Team""",
        recipient=patient.email,
    )

def send_appointment_cancelled(appointment, cancelled_by='patient'):
    if cancelled_by == 'patient':
        recipient = appointment.doctor
        message = f"""Hi Dr. {appointment.doctor.get_full_name()},
    
A patient has cancelled their appointment with you.

Patient: {appointment.patient.get_full_name()}
Date: {appointment.appointment_date.strftime('%A, %B %d, %Y')}
Time: {appointment.appointment_time.strftime('%I:%M %p')}

Log in to your portal to view your updated schedule

https://life-care-websites.vercel.app/login

-The LifeCare Team"""
        _send(
            subject="Appointment Cancelled - LifeCare",
            message= message,
            recipient= recipient.email
        )
    elif cancelled_by == 'system':
        _send(
            subject = 'Appointment Automatically Cancelled - LifeCare',
            message=f"""Hi {appointment.patient.first_name},
Your appointment was automatically cancelled because the doctor did not confirm it within 24 hours before the scheduled time.
Doctor: Dr. {appointment.doctor.get_full_name()}
Date: {appointment.appointment_date.strftime("A, %B %d, %Y")}
Time: {appointment.appointment_time.strftime("I:%M %p")}

Please book a new appointment at your convinience:
https://life-care-websites.vercel.app/login

We apologise for the inconvinience.
- The LifeCare Team""",
         recipient=appointment.patient.email,   
        )

        _send(
            subject = 'Appointment Auto-Cancelled - LifeCare',
            message=f"""Hi Dr. {appointment.doctor.get_full_name()},
An appointment was automatically cancelled because it was not confirmed withing 24 hours.

Patient: Dr. {appointment.patient.get_full_name()}

Date: {appointment.appointment_date.strftime("A, %B %d, %Y")}

Time: {appointment.appointment_time.strftime("I:%M %p")}

Please log in to your portal to manage your schedule.
https://life-care-websites.vercel.app/login

- The LifeCare Team""",
         recipient=appointment.doctor.email,   
        )
        
    else:
        _send(
            subject= "Appointment Cancelled - LifeCare",
            message = f"""Hi Dr. {appointment.patient.get_full_name()},

Your appointment has cancelled by the doctor.

Patient: {appointment.doctor.get_full_name()}
Date: {appointment.appointment_date.strftime('%A, %B %d, %Y')}
Time: {appointment.appointment_time.strftime('%I:%M %p')}

Please book a new appointment at your convinience:

https://life-care-websites.vercel.app/login

-The LifeCare Team""",
            recipient=appointment.patient.email
        )


def send_appointment_rescheduled(appointment, rescheduled_by='patient'):
    if rescheduled_by == 'patient':
        recipient_name = f"Dr. {appointment.doctor.get_full_name()}"
        recipient_email = appointment.doctor.email
        by_name = appointment.patient.get_full_name()
    else:
        recipient_name = appointment.patient.get_full_name()
        recipient_email = appointment.patient.email
        by_name = f"Dr. {appointment.doctor.get_full_name()}"
    
    _send(
        subject="Appointment Rescheduled - LifeCare",
        message= f"""Hi {recipient_name},

An appointment has been rescheduled by {by_name}.
Date: {appointment.appointment_date.strftime('%A, %B %d, %Y')}
Time: {appointment.appointment_time.strftime('%I:%M %p')}
Location: {appointment.location}

Log in to your portal for details: 

https://life-care-websites.vercel.app/login
    
-The LifeCare Team""",
        recipient=recipient_email
    )


def send_unread_message_alert(message):
    recipient = message.conversation.patient if message.sender.role == 'doctor' else message.conversation.doctor
    sender_name = f"Dr. {message.sender.get_full_name()}" if message.sender.role == 'doctor' else message.sender.get_full_name()

    _send(
        subject=f"New message from {sender_name} -- LifeCare",
        message=f"""
Hi {recipient.first_name},

You have an unread message from {sender_name}

Log in to your portal to respond:
https://life-care-websites.vercel.app/login

- LifeCare Team

        """,
        recipient=recipient.email,
    )


def send_notification_email(notification):
    type_subjects = {
        "appointment" : "New Appointment Notification - LifeCare",
        "message" : "New Message Notification - LifeCare",
        "prescription" : "New Prescription Notification - LifeCare",
        "lab_result" : "New Lab Result - LifeCare",
        "general" : "New Notification - LifeCare",

    }
    subject = type_subjects.get(notification.type, 'New Notification - LifeCare')


    _send(
        subject=subject,
        message= f"""Hi {notification.recipient.first_name},

You have a new notification on your LifeCare portal

{notification.title},

{notification.body}


Login in to your portal to view details:
https://life-care-websites.vercel.app/login


-The LifeCare Team""",
        recipient=notification.recipient.email,
    )

def send_new_prescription(prescription):
    patient = prescription.patient
    _send(
        subject="New Prescription - LifeCare",
        message= f"""Hi {patient.first_name},

Dr. {prescription.doctor.get_full_name()} has issued a new prescription.

Medication: {prescription.medication_name},
Dosage: {prescription.dosage}
Frequency: {prescription.frequency}
Duration: {prescription.duration}
Instructions: {prescription.notes or 'None'}

View your full prescription history:
https://life-care-websites.vercel.app/login


-The LifeCare Team""",
        recipient=patient.email,
    )


def send_medical_record_added(record):
    patient = record.patient
    doctor_name = f"Dr {record.doctor.get_full_name()}" if record.doctor else "LifeCare"

    record_type_display = {
        "lab_result" : "Lab Result",
        "imaging" : "Imaging",
        "diagnosis" : "Diagnosis",
        "surgery" : "Surgery",
        "vaccination" : "Vaccination",
        "allergy" : "Allergy",
        "general" : "General"
    }.get(record.record_type, 'Medical Record')

    _send(
        subject = f"New {record_type_display} Added to your Records - LifeCare.",
        message = f"""Hi {patient.first_name},

{doctor_name} has added a new medical record to your LifeCare portal.

Record Details:

Title : {record.title}
Type: {record_type_display}
Date: {record.date_recorded.strftime('%A, %B %d', '%Y')}
{f'Notes: {record.description}' if record.description else ''}

Log in to your protal to view the full record {'and downalod the attached file' if record.file else ''}:
https://life-care-websites.vercel.app/login

If you have any questions about this record, you can message {doctor_name} directly through your portal.

- The LifeCare Team """,
        recipient = patient.email
    )