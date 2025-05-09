from functools import wraps
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now
import json
from .models import Session  # Import your Session model

def authenticate_token(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            request._user = None  # Explicitly set user to None
            return JsonResponse({
                "success": False,
                "message": "Authentication token is missing or invalid.",
                "errno": 0x20
            }, status=401)

        token = auth_header.split(' ')[1]
        
        try:
            session = Session.objects.select_related('user').get(
                token=token, 
                is_expired=False
            )
            
            if session.expires_at < now():
                session.is_expired = True
                session.save()
                request._user = None  # Explicitly set user to None
                return JsonResponse({
                    "success": False,
                    "message": "Token has expired.",
                    "errno": 0x21
                }, status=401)

            # Ensure user is attached to request
            request._user = session.user
            if request._user is None:
                return JsonResponse({
                    "success": False,
                    "message": "User account not found.",
                    "errno": 0x22
                }, status=401)

            return view_func(request, *args, **kwargs)

        except ObjectDoesNotExist:
            request._user = None  # Explicitly set user to None
            return JsonResponse({
                "success": False,
                "message": "Invalid or expired token.",
                "errno": 0x21
            }, status=401)

    return _wrapped_view


def expect_json(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.content_type != 'application/json':
            return JsonResponse({
                "success": False,
                "message": "Content-Type must be application/json",
                "errno": 0x60
            }, status=415)
        
        try:
            if request.body:  # Only parse if there's a body
                request.parsed_data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                "success": False,
                "message": "Invalid JSON data",
                "errno": 0x61
            }, status=400)
            
        return view_func(request, *args, **kwargs)
    return wrapper


def strict_body_to_json(view_func):
    """Converts JSON/form-data/x-www-form-urlencoded requests to JSON."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Initialize unified data dict
        request.parsed_data = {}
        content_type = request.content_type.lower()

        # JSON (application/json)
        if content_type == 'application/json':
            if request.body:
                try:
                    request.parsed_data = json.loads(request.body)
                except json.JSONDecodeError:
                    return JsonResponse({
                        "success": False,
                        "message": "Invalid JSON data",
                        "errno": 0x61
                    }, status=400)

        # Form-Data (multipart/form-data)
        elif content_type.startswith('multipart/form-data'):
            request.parsed_data = request.POST.dict()
            if request.FILES:
                request.parsed_data['_files'] = {
                    name: file.name for name, file in request.FILES.items()
                }

        # URL-Encoded (application/x-www-form-urlencoded)
        elif content_type == 'application/x-www-form-urlencoded':
            request.parsed_data = request.POST.dict()

        # Reject all other content types
        else:
            return JsonResponse({
                "success": False,
                "message": "Unsupported Content-Type. Use JSON, form-data, or x-www-form-urlencoded",
                "errno": 0x62
            }, status=415)

        return view_func(request, *args, **kwargs)
    return wrapper

# Decorator to check if the user has a specific role
def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request._user.role != role:
                return JsonResponse({
                    "success": False,
                    "message": f"{role.capitalize()} access only",
                    "errno": 0x70
                }, status=403)
                
            profile = getattr(request._user, f'{role}_profile', None)
            
            if not profile:
                return JsonResponse({
                    "success": False,
                    "message": f"Complete your {role} profile first",
                    "errno": 0x80
                }, status=403)
                
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator