from django.contrib import admin
from .models import User, Session, EmailVerificationToken, PasswordResetToken

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    # Remove references to groups/user_permissions/is_active
    filter_horizontal = ()
    
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_verified', 'last_login')
    list_filter = ('role', 'is_verified')  # Removed is_active
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'last_login')
    
    fieldsets = (
        (None, {'fields': ('email', 'password_hash')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'username', 'profile_picture_url', 'phone_number', 'timezone')}),
        ('Permissions', {'fields': ('role', 'is_verified')}),  # Removed is_active
        ('Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password_hash'),
        }),
    )

    # Remove these methods if they were inherited
    def get_fieldsets(self, request, obj=None):
        return self.fieldsets

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return form

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'token_truncated', 'is_expired', 'created_at', 'expires_at')
    list_filter = ('is_expired',)
    search_fields = ('user__email',)
    readonly_fields = ('token', 'created_at')
    raw_id_fields = ('user',)
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    
    def token_truncated(self, obj):
        return str(obj.token)[:8] + '...'
    token_truncated.short_description = 'Token'

@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'is_valid', 'created_at', 'expires_at')
    search_fields = ('user__email',)
    readonly_fields = ('token', 'created_at')
    raw_id_fields = ('user',)
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    
    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'is_valid', 'created_at', 'expires_at')
    search_fields = ('user__email',)
    readonly_fields = ('token', 'created_at')
    raw_id_fields = ('user',)
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    
    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True