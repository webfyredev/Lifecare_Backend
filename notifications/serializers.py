from rest_framework import serializers
from .models import Notification

class NotificationSerializers(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('id', 'title', 'body', 'type', 'is_read', 'created_at')