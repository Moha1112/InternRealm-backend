from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from uuid import uuid4

from datetime import timedelta
from django.forms import ValidationError
from django.utils.timezone import now

class User(models.Model):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('company', 'Company'),
        ('admin', 'Admin'),
    )
    
    username = models.CharField(max_length=50)
    email = models.EmailField(max_length=255, unique=True)
    password_hash = models.CharField(max_length=255)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    role = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    is_verified = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    profile_picture_url = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    timezone = models.CharField(max_length=50, default="UTC")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    def __str__(self):
        return self.email

    def set_password(self, raw_password):
        """Hash and set the password."""
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        """Check if the raw password matches the hashed password."""
        return check_password(raw_password, self.password_hash)
    
    # In User model
    def validate_password(self, password):
        if len(password) < 8:
            raise ValidationError("Password must be ≥8 characters")

    def get_full_name(self):
        return self.first_name + " " + self.last_name

class Session(models.Model):
    """Model to handle user sessions."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='session_info')
    token = models.UUIDField(default=uuid4, editable=False, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True, null=True)
    is_expired = models.BooleanField(default=False)

    @classmethod
    def create_session(cls, user, duration_hours=24):
        """Create a new session for the user."""
        expires_at = now() + timedelta(hours=duration_hours)
        return cls.objects.create(user=user, expires_at=expires_at)
    
    @classmethod
    def cleanup_expired(cls):
        cls.objects.filter(expires_at__lt=now()).update(is_expired=True)

    def expire(self):
        """Mark the session as expired."""
        self.is_expired = True
        self.save()

class EmailVerificationToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    @classmethod
    def create_token(cls, user, duration_hours=24):
        expires_at = now() + timedelta(hours=duration_hours)
        return cls.objects.create(user=user, expires_at=expires_at)

    def is_valid(self):
        return not self.user.is_verified and self.expires_at > now()


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    @classmethod
    def create_token(cls, user, duration_hours=1):  # Shorter duration for security
        expires_at = now() + timedelta(hours=duration_hours)
        return cls.objects.create(user=user, expires_at=expires_at)

    def is_valid(self):
        return self.expires_at > now()
