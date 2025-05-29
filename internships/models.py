from django.db import models
from django.db import migrations
from django.forms import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from pgvector.django import VectorField
from users.models import User
from profiles.models import CompanyProfile
from .validations import validate_future_date, validate_salary

class Internship(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('closed', 'Closed')
    ]
    
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='internships')
    title = models.CharField(max_length=200)
    description = models.TextField()
    requirements = models.TextField()
    duration_months = models.PositiveIntegerField()
    is_paid = models.BooleanField(default=False)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=100)
    remote_option = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    application_deadline = models.DateField(validators=[validate_future_date])
    embedding = VectorField(dimensions=384, null=True, blank=True)  # For storing embeddings

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(latitude__isnull=True) | 
                (models.Q(latitude__gte=-90) & models.Q(latitude__lte=90)),
                name="valid_latitude"
            ),
            models.CheckConstraint(
                check=models.Q(longitude__isnull=True) | 
                (models.Q(longitude__gte=-180) & models.Q(longitude__lte=180)),
                name="valid_longitude"
            ),
        ]

    @property
    def coordinates(self):
        if self.latitude and self.longitude:
            return {'lat': self.latitude, 'lng': self.longitude}
        return None

    def update_embedding(self):
        from .utils import generate_embedding  # Local import to avoid circular imports
        self.embedding = generate_embedding(self.get_search_text())
        self.save()

    def clean(self):
        validate_salary({
            'is_paid': self.is_paid,
            'salary': self.salary
        })
        super().clean()
    
    def get_search_text(self):
        return f"{self.title} {self.description} {self.requirements}"

    def __str__(self):
        return f"{self.title} at {self.company.company_name}"

class Application(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('rejected', 'Rejected'),
        ('hired', 'Hired')
    ]
    
    internship = models.ForeignKey(Internship, on_delete=models.CASCADE, related_name='applications')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    cover_letter = models.TextField()
    cv = models.ForeignKey('profiles.StudentCV', on_delete=models.SET_NULL, 
                         null=True, blank=True, related_name='applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('internship', 'student')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status = self.status
    
    def clean(self):
        if self.status != self._original_status:
            from .validations import validate_application_status
            validate_application_status(self._original_status, self.status)
        super().clean()
    
    def __str__(self):
        return f"{self.student.email} application for {self.internship.title}"


class Interview(models.Model):
    INTERVIEW_TYPES = [
        ('phone', 'Phone Screen'),
        ('video', 'Video Call'),
        ('onsite', 'On-site'),
        ('technical', 'Technical Test'),
        ('case', 'Case Study')
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled')
    ]

    application = models.ForeignKey(
        'Application',
        on_delete=models.CASCADE,
        related_name='interviews'
    )
    interview_type = models.CharField(
        max_length=20,
        choices=INTERVIEW_TYPES,
        default='video'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )
    meeting_url = models.URLField(
        max_length=500,
        blank=True,
        null=True
    )
    notes = models.TextField(blank=True)
    interviewers = models.ManyToManyField(User, related_name='interviews_to_conduct')

    class Meta:
        ordering = ['start_time']
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_time__gt=models.F('start_time')),
                name='end_time_after_start_time'
            ),
            models.CheckConstraint(
                check=~models.Q(interview_type='onsite') | models.Q(location__isnull=False),
                name='onsite_interviews_require_location'
            ),
            models.CheckConstraint(
                check=~models.Q(interview_type='video') | models.Q(meeting_url__isnull=False),
                name='video_interviews_require_url'
            )
        ]

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time")
        
        if self.interview_type == 'onsite' and not self.location:
            raise ValidationError("Location is required for on-site interviews")
            
        if self.interview_type == 'video' and not self.meeting_url:
            raise ValidationError("Meeting URL is required for video interviews")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def duration_minutes(self):
        return int((self.end_time - self.start_time).total_seconds() / 60)
    
    def get_calendar_event_details(self):
        return {
            'title': f"{self.application.internship.title} Interview",
            'description': f"Interview with {self.application.student.get_full_name()}",
            'start': self.start_time.isoformat(),
            'end': self.end_time.isoformat(),
            'location': self.location or self.meeting_url,
            'attendees': [
                self.application.student.email
            ] + [
                u.email for u in self.interviewers.all()
            ]
        }
    
    def send_calendar_invite(self):
        # Integration with calendar APIs would go here
        event_details = self.get_calendar_event_details()
        # Implement actual calendar API calls
        return True
    
    def get_average_score(self):
        from django.db.models import Avg
        return self.evaluation.aggregate(
            avg_score=Avg('overall_score')
        )['avg_score']
    
    def is_fully_evaluated(self):
        return self.evaluation.count() >= self.interviewers.count()

    def __str__(self):
        return f"{self.get_interview_type_display()} - {self.application.student.email}"

class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL('CREATE EXTENSION IF NOT EXISTS vector;'),
        migrations.RunSQL('''
            CREATE INDEX ON internships_internship 
            USING hnsw (embedding vector_l2_ops) 
            WITH (m = 16, ef_construction = 64);
        '''),
        migrations.RunSQL('''
            ALTER SYSTEM SET pgvector.hnsw.ef_search = 40;
            SELECT pg_reload_conf();
        ''')
    ]


class Evaluation(models.Model):
    interview = models.OneToOneField(
        Interview,
        on_delete=models.CASCADE,
        related_name='evaluation'
    )
    evaluator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='evaluations'
    )
    
    # Core ratings (1-5 scale)
    technical_skills = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    problem_solving = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    communication = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    cultural_fit = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    
    # Overall assessment
    overall_score = models.FloatField(null=True, blank=True)
    recommendation = models.CharField(
        max_length=20,
        choices=[
            ('strong_yes', 'Strong Yes'),
            ('yes', 'Yes'),
            ('neutral', 'Neutral'),
            ('no', 'No'),
            ('strong_no', 'Strong No')
        ]
    )
    
    # Qualitative feedback
    strengths = models.TextField()
    areas_for_improvement = models.TextField()
    additional_comments = models.TextField(blank=True)
    
    # Metadata
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('interview', 'evaluator')
    
    def save(self, *args, **kwargs):
        # Calculate overall score if ratings exist
        if all([
            self.technical_skills,
            self.problem_solving,
            self.communication,
            self.cultural_fit
        ]):
            self.overall_score = (
                self.technical_skills + 
                self.problem_solving + 
                self.communication + 
                self.cultural_fit
            ) / 4
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Evaluation for {self.interview} by {self.evaluator}"
