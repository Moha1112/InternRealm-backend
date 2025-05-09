from django.contrib import admin
from .models import StudentProfile, CompanyProfile

class EducationInline(admin.StackedInline):
    model = StudentProfile
    fields = ('education_level', 'university', 'major', 'graduation_year', 'gpa')
    extra = 0
    max_num = 1
    can_delete = False

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'education_summary', 'availability', 'search_status')
    list_filter = ('education_level', 'availability', 'search_status', 'work_authorization')
    search_fields = ('user__email', 'university', 'major')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user',)
    
    fieldsets = (
        ('Personal Info', {'fields': ('user', 'bio')}),
        ('Education', {'fields': ('education_level', 'university', 'major', 'graduation_year', 'gpa')}),
        ('Professional', {'fields': ('availability', 'work_authorization')}),
        ('Job Preferences', {'fields': ('search_status', 'preferred_locations', 'desired_salary')}),
        ('Social', {'fields': ('linkedin_url', 'github_url', 'website_url')}),
        ('Dates', {'fields': ('created_at', 'updated_at')}),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    
    def education_summary(self, obj):
        return f"{obj.get_education_level_display()} at {obj.university or 'Unknown'}"
    education_summary.short_description = 'Education'

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'industry_display', 'is_verified', 'company_size', 'headquarters_location')
    list_filter = ('industry', 'is_verified')
    search_fields = ('company_name', 'user__email', 'headquarters_location')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user',)
    
    fieldsets = (
        ('Company Info', {'fields': ('user', 'company_name', 'description', 'industry', 'founded_year', 'company_size')}),
        ('Contact', {'fields': ('website_url', 'logo_url', 'headquarters_location')}),
        ('HR Contact', {'fields': ('hr_contact_name', 'hr_contact_email', 'hr_contact_phone')}),
        ('Verification', {'fields': ('is_verified', 'tax_id')}),
        ('Dates', {'fields': ('created_at', 'updated_at')}),
    )
    
    def industry_display(self, obj):
        return obj.get_industry_display()
    industry_display.short_description = 'Industry'