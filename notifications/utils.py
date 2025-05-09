from django.core.mail import send_mail
from django.conf import settings
from .models import Notification

def create_notification(user, notification_type, title, message, **kwargs):
    """Core notification creation method"""
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        related_interview=kwargs.get('interview'),
        related_application=kwargs.get('application'),
        scheduled_at=kwargs.get('scheduled_at')
    )
    
    # Immediate email if not scheduled for future
    if not kwargs.get('scheduled_at'):
        send_email_notification(notification)
    
    return notification

def send_email_notification(notification):
    """Send email version of notification"""
    subject = f"[InternHub] {notification.title}"
    send_mail(
        subject,
        notification.message,
        settings.DEFAULT_FROM_EMAIL,
        [notification.user.email],
        fail_silently=True
    )