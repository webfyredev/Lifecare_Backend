from django.contrib import admin
from .models import Conversation, Message

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'created_at', 'updated_at')
    search_fields = ('patient__first_name', 'doctor__first_name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'conversation', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('sender__first_name', 'body')
    readonly_fields = ('created_at',)
