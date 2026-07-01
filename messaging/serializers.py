from rest_framework import serializers
from accounts.models import User
from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ('id', 'body', 'sender_name', 'is_mine', 'is_read', 'created_at', 'file_url', 'file_type', 'is_edited')

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None
    def get_sender_name(self, obj):
        return obj.sender.get_full_name()

    def get_is_mine(self, obj):
        request = self.context.get('request')
        return obj.sender == request.user

class ConversationSerializer(serializers.ModelSerializer):
    other_person_name = serializers.SerializerMethodField()
    other_person_picture = serializers.SerializerMethodField()
    other_person_subtitle = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ('id', 'other_person_name', 'other_person_picture', 'other_person_subtitle', 'last_message', 'unread_count')

    def get_other_person(self, obj):
        request = self.context.get('request')
        if request.user.role == 'doctor':
            return obj.patient
        return obj.doctor
    
    def get_other_person_name(self, obj):
        other = self.get_other_person(obj)
        request = self.context.get('request')
        if request.user.role == 'doctor':
            return other.get_full_name()
        return f"Dr. {other.get_full_name()}"
    
    def get_other_person_picture(self, obj):
        other = self.get_other_person(obj)
        request = self.context.get('request')
        if other.profile_picture and request:
            return request.build_absolute_uri(other.profile_picture.url)
        return None

    def get_other_person_subtitle(self, obj):
        request = self.context.get('request')
        if request.user.role == 'doctor':
            try:
                return obj.patient.patient_profile.blood_type or ''
            except:
                return ''
        else:
            try:
                return obj.doctor.doctor_profile.specialization
            except:
                return ''
    
    def get_last_message(self, obj):
        last = obj.messages.last()
        if last:
            return {"body" : last.body, "created_at" : last.created_at}
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()