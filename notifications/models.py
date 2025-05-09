# notifications/models.py
from django.db import models
from django.utils import timezone
from users.models import User
from internships.models import Interview, Application


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('interview_scheduled', 'Interview Scheduled'),
        ('interview_updated', 'Interview Updated'),
        ('interview_canceled', 'Interview Canceled'),
        ('application_update', 'Application Status Update'),
        ('evaluation_submitted', 'Evaluation Submitted'),
        ('interview_completed', 'Interview Process Complete'),
        ('reminder', 'Reminder'),
        ('system', 'System Message')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_interview = models.ForeignKey(
        Interview,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    related_application = models.ForeignKey(
        Application,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    scheduled_at = models.DateTimeField(null=True, blank=True)  # For future notifications
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['scheduled_at']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.user.email}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()