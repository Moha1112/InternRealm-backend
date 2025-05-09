from django.contrib import admin

from .models import User, StudentProfile, CompanyProfile

admin.site.register(User, StudentProfile, CompanyProfile)