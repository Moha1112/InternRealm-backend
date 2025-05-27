from .models import Internship, Interview, Evaluation
from notifications.utils import create_notification
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction


@receiver(post_save, sender=Internship)
def update_internship_embedding(sender, instance, created, **kwargs):
    """
    Update vector embedding when internship is created or text fields change.
    Uses transaction.on_commit to ensure it runs after successful save.
    """
    # Check if we need to update the embedding
    fields_to_check = ['title', 'description', 'requirements']
    update_needed = False

    if created:
        update_needed = True
    else:
        # Get the original instance before update
        try:
            original = Internship.objects.get(pk=instance.pk)
            for field in fields_to_check:
                if getattr(original, field) != getattr(instance, field):
                    update_needed = True
                    break
        except Internship.DoesNotExist:
            pass

    if update_needed:
        # Use transaction.on_commit to avoid race conditions
        transaction.on_commit(lambda: instance.update_embedding())

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