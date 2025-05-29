from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from pgvector.django import VectorField
from users.models import User

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    
    # Personal Info
    bio = models.TextField(blank=True, max_length=500)
    education_level = models.CharField(max_length=50, blank=True, choices=[
        ('high_school', 'High School'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('phd', 'PhD')
    ])
    
    # Education
    university = models.CharField(max_length=100, blank=True)
    major = models.CharField(max_length=100, blank=True)
    graduation_year = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1900), MaxValueValidator(2100)]
    )
    gpa = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(4)]
    )
    
    # Professional
    availability = models.CharField(max_length=20, choices=[
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('contract', 'Contract')
    ], default='full_time')
    
    WORK_AUTHORIZATION_CHOICES = [
        ('us_citizen', 'US Citizen'),
        ('work_visa', 'Work Visa'),
        ('student_visa', 'Student Visa (OPT/CPT)'),
        ('no_sponsorship', 'Requires Sponsorship'),
        ('other', 'Other')
    ]
    work_authorization = models.CharField(
        max_length=20,
        choices=WORK_AUTHORIZATION_CHOICES,
        default='us_citizen'
    )
    
    # Social
    linkedin_url = models.URLField(max_length=255, blank=True)
    github_url = models.URLField(max_length=255, blank=True)
    website_url = models.URLField(max_length=255, blank=True)
    
    # Job Preferences
    search_status = models.CharField(max_length=50, default="active", choices=[
        ('active', 'Actively Searching'),
        ('passive', 'Open to Opportunities'),
        ('not_looking', 'Not Looking')
    ])
    preferred_locations = models.CharField(max_length=255, blank=True, default='')
    desired_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)]
    )

    saved_internships = models.ManyToManyField("internships.Internship", related_name='saved_internships', blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"
        ordering = ['-created_at']
    
    def get_education_info(self):
        return {
            'level': self.education_level,
            'institution': self.university,
            'field': self.major,
            'year': self.graduation_year
        }

    def __str__(self):
        return f"{self.user.email}'s Student Profile"

class IndustryChoices(models.TextChoices):
    TECHNOLOGY = 'tech', 'Technology'
    FINANCE = 'finance', 'Finance'
    HEALTHCARE = 'healthcare', 'Healthcare'
    EDUCATION = 'education', 'Education'
    RETAIL = 'retail', 'Retail'
    ENERGY = 'energy', 'Energy'
    MANUFACTURING = 'manufacturing', 'Manufacturing'
    ENTERTAINMENT = 'entertainment', 'Entertainment'
    GOVERNMENT = 'government', 'Government'

class CompanyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company_profile')
    
    # Company Info
    company_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    industry = models.CharField(max_length=50, choices=IndustryChoices.choices, blank=True, default='')
    founded_year = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1800), MaxValueValidator(2100)]
    )
    company_size = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1)]
    )
    
    # Contact
    website_url = models.URLField(max_length=255, blank=True)
    logo_url = models.URLField(max_length=255, blank=True)
    headquarters_location = models.CharField(max_length=100, blank=True)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    tax_id = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text="Format: XX-XXXXXXX"
    )
    
    # HR Contact
    hr_contact_name = models.CharField(max_length=100, null=True, blank=True)
    hr_contact_email = models.EmailField(max_length=255, null=True, blank=True)
    hr_contact_phone = models.CharField(
        max_length=20, 
        null=True, 
        blank=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company_name}'s Profile"


class StudentCV(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cvs')
    title = models.CharField(max_length=100)
    education = models.JSONField(default=list)  # [{degree, institution, year}]
    experience = models.JSONField(default=list) # [{role, company, duration}]
    skills = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_default = models.BooleanField(default=False)
    embedding = VectorField(dimensions=384, null=True, blank=True)  # For storing embeddings

    def update_embedding(self):
        """Generate embedding from CV content"""
        from internships.utils import generate_embedding
        text_parts = [
            self.title,
            ' '.join(self.skills),
            self.education_text(),
            self.experience_text()
        ]
        self.embedding = generate_embedding(' '.join(text_parts))
        self.save()
    
    def education_text(self):
        return ' '.join([
            f"{edu.get('degree','')} {edu.get('institution','')}" 
            for edu in self.education
        ])
    
    def experience_text(self):
        return ' '.join([
            f"{exp.get('role','')} {exp.get('company','')} {exp.get('description','')}" 
            for exp in self.experience
        ])

    def __str__(self):
        return f"{self.user.get_full_name()}'s CV ({self.title})"


def student_profile_to_dict(profile: StudentProfile) -> dict:
    """Convert StudentProfile to frontend-friendly dictionary"""
    return {
        'type': 'student',
        'id': profile.id,
        'basics': {
            'bio': profile.bio or '',
            'status': {
                'value': profile.search_status,
                'display': dict(StudentProfile._meta.get_field('search_status').choices).get(profile.search_status, '')
            },
            'availability': {
                'value': profile.availability,
                'display': dict(StudentProfile._meta.get_field('availability').choices).get(profile.availability, '')
            }
        },
        'education': {
            'level': {
                'value': profile.education_level,
                'display': dict(StudentProfile._meta.get_field('education_level').choices).get(profile.education_level, '')
            },
            'university': profile.university or '',
            'major': profile.major or '',
            'graduation_year': profile.graduation_year,
            'gpa': float(profile.gpa) if profile.gpa is not None else None
        },
        'work': {
            'authorization': {
                'value': profile.work_authorization,
                'display': dict(StudentProfile._meta.get_field('work_authorization').choices).get(profile.work_authorization, '')
            }
        },
        'social': {
            'linkedin': profile.linkedin_url or '',
            'github': profile.github_url or '',
            'website': profile.website_url or ''
        },
        'preferences': {
            'locations': profile.preferred_locations.split(',') if profile.preferred_locations else [],
            'salary': float(profile.desired_salary) if profile.desired_salary is not None else None,
            'currency': 'USD'
        },
        'dates': {
            'created': profile.created_at.isoformat(),
            'updated': profile.updated_at.isoformat()
        }
    }

def company_profile_to_dict(profile):
    """Convert CompanyProfile to frontend-friendly dictionary"""
    return {
        'type': 'company',
        'id': profile.id,
        'basics': {
            'company_name': profile.company_name,
            'description': profile.description or '',
            'verification_status': profile.is_verified
        },
        'details': {
            'industry': {
                'value': profile.industry,
                'display': dict(CompanyProfile._meta.get_field('industry').choices).get(profile.industry, '')
            },
            'founded_year': profile.founded_year,
            'size': profile.company_size,
            'headquarters': profile.headquarters_location or ''
        },
        'contact': {
            'website': profile.website_url or '',
            'logo': profile.logo_url or '',
            'hr_contact': {
                'name': profile.hr_contact_name or '',
                'email': profile.hr_contact_email or '',
                'phone': profile.hr_contact_phone or ''
            }
        },
        'legal': {
            'tax_id': profile.tax_id or ''
        },
        'dates': {
            'created': profile.created_at.isoformat(),
            'updated': profile.updated_at.isoformat()
        }
    }


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=StudentCV)
def update_cv_embedding(sender, instance, **kwargs):
    if any(field in kwargs.get('update_fields', []) 
           for field in ['title', 'skills', 'experience']):
        instance.update_embedding()