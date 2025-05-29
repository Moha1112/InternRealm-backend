from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta
from django.utils.timezone import now
import json
from .models import User, Session, EmailVerificationToken, PasswordResetToken
from .decorators import authenticate_token, strict_body_to_json
from profiles.models import StudentProfile, CompanyProfile

@csrf_exempt
@require_POST
@strict_body_to_json
def login(request):
    try:
        email = request.parsed_data.get('email')
        password = request.parsed_data.get('password')

        if not email or not password:
            return JsonResponse({
                "success": False,
                "message": "Email and password are required.",
                "errno": 0x10
            }, status=400)

        try:
            user = User.objects.get(email=email, deleted_at__isnull=True)
        except User.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "Invalid credentials.",
                "errno": 0x11
            }, status=401)

        if not user.check_password(password):
            return JsonResponse({
                "success": False,
                "message": "Invalid credentials.",
                "errno": 0x11
            }, status=401)

        # Create a session
        session = Session.create_session(user, 732)
        user.last_login = now()
        user.save()

        return JsonResponse({
            "success": True,
            "message": "Login successful.",
            "token": str(session.token),
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role
            }
        }, status=200)

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": "An unexpected error occurred.",
            "error": str(e)
        }, status=500)


@csrf_exempt
@require_POST
@authenticate_token
def logout(request):
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(' ')[1]

    try:
        session = Session.objects.get(token=token)
        session.expire()  # Mark the session as expired
    except Session.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Invalid token.",
            "errno": 0x21
        }, status=401)

    return JsonResponse({
        "success": True,
        "message": "Logged out successfully."
    }, status=200)


@csrf_exempt
@authenticate_token
def me(request):
    user = request._user
    return JsonResponse({
        "success": True,
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_number": user.phone_number,
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "is_verified": user.is_verified
        }
    }, status=200)


@csrf_exempt
@require_POST
def refresh_token(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return JsonResponse({
            "success": False,
            "message": "Authentication token is missing or invalid.",
            "errno": 0x20
        }, status=401)

    token = auth_header.split(' ')[1]
    try:
        session = Session.objects.get(token=token, is_expired=False)
        
        # Check if the token is still valid
        if session.expires_at > now():
            # Extend the token's validity
            session.expires_at = now() + timedelta(hours=24)
            session.save()
            return JsonResponse({
                "success": True,
                "message": "Token refreshed successfully.",
                "token": str(session.token)
            }, status=200)
        else:
            # Token has expired
            session.is_expired = True
            session.save()
            return JsonResponse({
                "success": False,
                "message": "Token has expired.",
                "errno": 0x21
            }, status=401)

    except Session.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Invalid or expired token.",
            "errno": 0x21
        }, status=401)


@csrf_exempt
@require_POST
@strict_body_to_json
def register(request):
    try:        
        # Validate required fields
        required_fields = ['email', 'password', 'first_name', 'last_name', 'role']
        if not all(field in request.parsed_data for field in required_fields):
            return JsonResponse({
                "success": False,
                "message": "All fields are required.",
                "errno": 0x30
            }, status=400)
        
        # Validate role
        if request.parsed_data['role'] not in [choice[0] for choice in User.USER_TYPE_CHOICES]:
            return JsonResponse({
                "success": False,
                "message": "Invalid user role.",
                "errno": 0x31
            }, status=400)
        
        # Check if email exists
        if User.objects.filter(email=request.parsed_data['email']).exists():
            return JsonResponse({
                "success": False,
                "message": "Email already exists.",
                "errno": 0x32
            }, status=400)

        with transaction.atomic():
            # Create user
            user = User.objects.create(
                email=request.parsed_data['email'],
                username=request.parsed_data.get('username', request.parsed_data['email'].split('@')[0]),
                first_name=request.parsed_data['first_name'],
                last_name=request.parsed_data['last_name'],
                role=request.parsed_data['role'],
                last_login=now()
            )
            user.set_password(request.parsed_data['password'])
            user.save()

            # Create profile based on role
            if request.parsed_data['role'] == 'student':
                StudentProfile.objects.create(user=user)
            elif request.parsed_data['role'] == 'company':
                CompanyProfile.objects.create(
                    user=user,
                    company_name=request.parsed_data.get('company_name', '')
                )

        return JsonResponse({
            "success": True,
            "message": "Registration successful.",
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role
            }
        }, status=201)

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": "Registration failed.",
            "error": str(e)
        }, status=500)


@csrf_exempt
@require_POST
@strict_body_to_json
def send_verification_email(request):
    try:
        email = request.parsed_data.get('email')
        
        if not email:
            return JsonResponse({
                "success": False,
                "message": "Email is required.",
                "errno": 0x40
            }, status=400)

        try:
            user = User.objects.get(email=email, deleted_at__isnull=True)
        except User.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "User not found.",
                "errno": 0x41
            }, status=404)

        if user.is_verified:
            return JsonResponse({
                "success": False,
                "message": "Email already verified.",
                "errno": 0x42
            }, status=400)

        # Create and send verification token
        token = EmailVerificationToken.create_token(user)
        
        # In a real app, you would send an email here
        # send_verification_email_task.delay(user.email, str(token.token))
        from notifications.utils import create_notification, send_html_email
        create_notification(user, "system", "A verification email has been sent.", "A verification token has been sent to your email address.")
        # send_html_email("Your email verification token", f"The token: {token.token}", user.email)
        
        return JsonResponse({
            "success": True,
            "message": "Verification email sent."
        }, status=200)

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": "Failed to send verification email.",
            "error": str(e)
        }, status=500)


@csrf_exempt
@require_POST
@strict_body_to_json
def verify_email(request):
    try:
        token = request.parsed_data.get('token')
        
        if not token:
            return JsonResponse({
                "success": False,
                "message": "Token is required.",
                "errno": 0x43
            }, status=400)

        try:
            verification_token = EmailVerificationToken.objects.get(token=token)
        except EmailVerificationToken.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "Invalid verification token.",
                "errno": 0x44
            }, status=400)

        if not verification_token.is_valid():
            return JsonResponse({
                "success": False,
                "message": "Token expired or already used.",
                "errno": 0x45
            }, status=400)

        # Mark user as verified
        user = verification_token.user
        user.is_verified = True
        user.save()
        
        # Delete the token
        verification_token.delete()

        return JsonResponse({
            "success": True,
            "message": "Email verified successfully."
        }, status=200)

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": "Email verification failed.",
            "error": str(e)
        }, status=500)


@csrf_exempt
@require_POST
@strict_body_to_json
def request_password_reset(request):
    try:
        email = request.parsed_data.get('email')
        
        if not email:
            return JsonResponse({
                "success": False,
                "message": "Email is required.",
                "errno": 0x50
            }, status=400)

        try:
            user = User.objects.get(email=email, deleted_at__isnull=True)
        except User.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "If this email exists, we've sent a reset link.",
                "errno": 0x51
            }, status=200)  # Don't reveal if user exists

        # Create and send reset token
        token = PasswordResetToken.create_token(user)
        
        # In a real app, you would send an email here
        # send_password_reset_email_task.delay(user.email, str(token.token))
        
        return JsonResponse({
            "success": True,
            "message": "If this email exists, we've sent a reset link."
        }, status=200)

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": "Failed to process password reset request.",
            "error": str(e)
        }, status=500)


@csrf_exempt
@require_POST
@strict_body_to_json
def reset_password(request):
    try:
        token = request.parsed_data.get('token')
        new_password = request.parsed_data.get('new_password')
        
        if not token or not new_password:
            return JsonResponse({
                "success": False,
                "message": "Token and new password are required.",
                "errno": 0x52
            }, status=400)

        try:
            reset_token = PasswordResetToken.objects.get(token=token)
        except PasswordResetToken.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "Invalid password reset token.",
                "errno": 0x53
            }, status=400)

        if not reset_token.is_valid():
            reset_token.delete()
            return JsonResponse({
                "success": False,
                "message": "Token expired.",
                "errno": 0x54
            }, status=400)

        # Update user password
        user = reset_token.user
        user.set_password(new_password)
        user.save()
        
        # Delete the token
        reset_token.delete()

        return JsonResponse({
            "success": True,
            "message": "Password reset successfully."
        }, status=200)

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": "Password reset failed.",
            "error": str(e)
        }, status=500)
