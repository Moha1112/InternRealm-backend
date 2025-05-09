from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "ST", "Student"
        COMPANY = "CO", "Company"
        ADMIN = "AD", "Admin"
        CAREER_SERVICES = "CS", "Career Services"

    # Remove username field (use email instead)
    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=2, choices=Role.choices)
    is_verified = models.BooleanField(default=False)
    
    # Required for custom user model
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['role']

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    university = models.CharField(max_length=100)
    major = models.CharField(max_length=100)
    graduation_year = models.PositiveIntegerField()
    skills = models.JSONField(default=list)  # ["Python", "React"]
    resume = models.FileField(upload_to="resumes/", null=True)
    linkedin_url = models.URLField(blank=True)

class CompanyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="company_profile")
    name = models.CharField(max_length=100)
    description = models.TextField()
    industry = models.CharField(max_length=50)
    website = models.URLField()
    logo = models.ImageField(upload_to="company_logos/")
    is_verified = models.BooleanField(default=False)