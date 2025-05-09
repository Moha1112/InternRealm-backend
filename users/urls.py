from django.urls import path
from .views import login, logout, me, refresh_token, register, send_verification_email, verify_email,request_password_reset, reset_password

urlpatterns = [
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),
    path('me/', me, name='me'),
    path('refresh-token/', refresh_token, name='refresh_token'),
    path('register/', register, name='register'),
    path('send-verification-email/', send_verification_email, name='send_verification_email'),
    path('verify-email/', verify_email, name='verify_email'),
    path('request-password-reset/', request_password_reset, name='request_password_reset'),
    path('reset-password/', reset_password, name='reset_password'),
]

"""
Authentication Error Codes (0x00-0x5F)
--------------------------------------
0x10 - Missing email/password (login)
0x11 - Invalid credentials (login)
0x20 - Missing/invalid auth token
0x21 - Expired/invalid token
0x30 - Missing registration fields
0x31 - Invalid user role
0x32 - Email already exists
0x40 - Missing email (verification)
0x41 - User not found (verification)
0x42 - Email already verified
0x43 - Missing token (verification)
0x44 - Invalid verification token
0x45 - Expired verification token
0x50 - Missing email (password reset)
0x51 - Email not found (password reset)
0x52 - Missing token/password (password reset)
0x53 - Invalid reset token
0x54 - Expired reset token
0x61 - Invalid JSON data
0x62 - Unsupported Content-Type

Profile Error Codes (0x60-0x7F)
-------------------------------
0x60 - Student profile incomplete
0x61 - Company profile incomplete
0x62 - Missing required profile fields
0x63 - Invalid profile data format
0x64 - Profile update failed

Role Access Error Codes (0x70-0x7F)
-----------------------------------
0x70 - Student access only
0x71 - Company access only
0x72 - Admin access only
0x73 - Insufficient permissions

System Error Codes (0x80-0xFF)
------------------------------
0x80 - Database error
0x81 - External service failure
0xFE - Maintenance mode
0xFF - Unknown error
"""