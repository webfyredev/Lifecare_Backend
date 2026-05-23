from django.db import models
from accounts.models import User


class Notification(models.Model):
    TYPE_CHOICES = (
        ('appointment', 'Appointment'),
        ('message', 'Message'),
        ('prescription', 'Prescription'),
        ('lab_result', 'Lab_Result'),
        ('general', 'General')
    )

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=100)
    body = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='general')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.title} from {self.recipient.get_full_name()}'