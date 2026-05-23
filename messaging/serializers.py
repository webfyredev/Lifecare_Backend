from rest_framework import serializers
from accounts.models import User
from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ('id', 'body', 'sender_name', 'is_mine', 'is_read', 'created_at')

    def get_sender_name(self, obj):
        return obj.sender.get_full_name()

    def get_is_mine(self, obj):
        request = self.context.get('request')
        return obj.sender == request.user

class ConversationSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    doctor_specialization = serializers.SerializerMethodField()
    doctor_picture = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ('id', 'doctor_name', 'doctor_specialization', 'doctor_picture', 'last_message', 'unread_count')

    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.get_full_name()}"

    def get_doctor_specialization(self, obj):
        try:
            return obj.doctor.doctor_profile.specialization
        except:
            return ''
    
    def get_doctor_picture(self, obj):
        request = self.context.get('request')
        if obj.doctor.profile_picture and request:
            return request.build_absolute_uri(obj.doctor.profile_picture.url)
        return None
    
    def get_last_message(self, obj):
        last = obj.messages.last()
        if last:
            return {"body" : last.body, "created_at" : last.created_at}
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()