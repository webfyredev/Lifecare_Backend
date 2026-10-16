from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'type', 'is_read', 'created_at')
    list_filter = ('type', 'is_read')
    search_fields = ('title', 'recipient__first_name', 'recipient__last_name')
    list_editable = ('is_read',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        from accounts.models import User
        form.base_fields['recipient'].queryset = User.objects.all()
        return form