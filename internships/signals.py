
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Internship, Interview, Evaluation
from notifications.utils import create_notification

@receiver(post_save, sender=Internship)
def update_internship_embedding(sender, instance, created, **kwargs):
    if created or any(field in ['title', 'description', 'requirements'] 
                   for field in instance.get_dirty_fields()):
        instance.update_embedding()


@receiver(post_save, sender=Interview)
def handle_interview_scheduling(sender, instance, created, **kwargs):
    if created:
        # Notify student
        create_notification(
            user=instance.application.student,
            notification_type='interview_scheduled',
            title='Interview Scheduled',
            message=f"Your interview for {instance.application.internship.title} has been scheduled.",
            interview=instance,
            application=instance.application
        )
        
        # Notify interviewers
        for interviewer in instance.interviewers.all():
            create_notification(
                user=interviewer,
                notification_type='interviewer_assigned',
                title='You have been assigned an interview',
                message=f"You have been assigned to interview {instance.application.student.get_full_name()} for {instance.application.internship.title}.",
                interview=instance,
                application=instance.application
            )

@receiver(post_save, sender=Evaluation)
def handle_evaluation_submission(sender, instance, created, **kwargs):
    if created:
        # Notify hiring manager
        create_notification(
            user=instance.interview.application.internship.company.user,
            notification_type='evaluation_submitted',
            title=f"New Evaluation for {instance.interview.application.student.get_full_name()}",
            message=f"{instance.evaluator.get_full_name()} submitted their evaluation",
            interview=instance.interview
        )
        
        # Notify student if all evaluations are complete
        if instance.interview.is_fully_evaluated():
            create_notification(
                user=instance.interview.application.student,
                notification_type='interview_completed',
                title=f"Interview Process Complete",
                message=f"All evaluations for your {instance.interview.get_interview_type_display()} interview have been submitted",
                interview=instance.interview
            )