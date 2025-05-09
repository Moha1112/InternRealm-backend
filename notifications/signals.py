# notifications/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from internships.models import Application, Interview
from .utils import create_notification

@receiver(post_save, sender=Interview)
def handle_interview_notifications(sender, instance, created, **kwargs):
    if created:
        # Notify student
        create_notification(
            user=instance.application.student,
            notification_type='interview_scheduled',
            title=f"New {instance.get_interview_type_display()} Interview Scheduled",
            message=f"You have a {instance.get_interview_type_display()} interview scheduled for {instance.start_time.strftime('%B %d, %Y at %I:%M %p')}",
            interview=instance
        )
        
        # Notify interviewers
        for interviewer in instance.interviewers.all():
            create_notification(
                user=interviewer,
                notification_type='interview_scheduled',
                title=f"New Interview Assignment: {instance.application.internship.title}",
                message=f"You're scheduled to interview {instance.application.student.get_full_name()} on {instance.start_time.strftime('%B %d, %Y at %I:%M %p')}",
                interview=instance
            )
    else:
        # Handle interview updates
        if 'status' in kwargs.get('update_fields', []):
            if instance.status == 'canceled':
                create_notification(
                    user=instance.application.student,
                    notification_type='interview_canceled',
                    title="Interview Canceled",
                    message=f"Your {instance.get_interview_type_display()} interview scheduled for {instance.start_time.strftime('%B %d, %Y')} has been canceled",
                    interview=instance
                )

@receiver(post_save, sender=Application)
def handle_application_notifications(sender, instance, **kwargs):
    if 'status' in kwargs.get('update_fields', []):
        create_notification(
            user=instance.student,
            notification_type='application_update',
            title=f"Application Status Update: {instance.internship.title}",
            message=f"Your application status has been updated to {instance.get_status_display()}",
            application=instance
        )