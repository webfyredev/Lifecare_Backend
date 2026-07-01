from django.db import models
from accounts.models import User

class Conversation(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name = 'patient_conversations')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = ('patient', 'doctor')

    def __str__(self):
        return f"{self.patient.get_full_name()} - Dr. {self.doctor.get_full_name()}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    body = models.TextField(blank=True)
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    file_type = models.CharField(max_length=20, blank=True)
    is_read = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from Dr. {self.conversation.doctor.get_full_name()} to (Patient -- ({self.conversation.patient.get_full_name()}))"