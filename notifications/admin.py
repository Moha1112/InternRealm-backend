from django.contrib import admin
from .models import Notification

# Register your models here.
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'message', 'is_read')
    list_filter = ('notification_type', 'is_read', 'created_at')  # Removed is_active
    search_fields = ('user', 'title', 'message')
    readonly_fields = ('created_at',)
