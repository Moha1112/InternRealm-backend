from django.contrib import admin
from .models import Internship, Application

@admin.register(Internship)
class InternshipAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'status', 'application_deadline')
    list_filter = ('status', 'is_paid', 'remote_option')
    search_fields = ('title', 'company__company_name')

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('internship', 'student', 'status', 'applied_at')
    list_filter = ('status', 'internship__company')
    search_fields = ('student__email', 'internship__title')