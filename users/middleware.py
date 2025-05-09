from django.http import JsonResponse
from django.utils.timezone import now
from .models import Session
from django.core.exceptions import ObjectDoesNotExist

class TokenAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Initialize request._user as None by default
        request._user = None
        
        auth_header = request.headers.get('Authorization')
        
        # Only proceed with token check if Authorization header exists
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]  # Extract the token from the header
            
            try:
                session = Session.objects.get(token=token, is_expired=False)
                
                # Check if the session has expired
                if session.expires_at < now():
                    session.is_expired = True
                    session.save()
                else:
                    # Only attach user if token is valid and not expired
                    request._user = session.user
                    request._user.is_authenticated = True
                    
            except ObjectDoesNotExist:
                # Silently handle invalid tokens (request._user remains None)
                pass

        response = self.get_response(request)
        return response

class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for auth endpoints
        if request.path.startswith(('/auth/', '/admin/')):
            return self.get_response(request)
            
        if request._user:
            role = request._user.role
            if role == 'student':
                profile = getattr(request._user, 'student_profile', None)
                if not profile:
                    return JsonResponse({
                        "success": False,
                        "message": "Complete your student profile",
                        "errno": 0x60
                    }, status=403)
                    
            elif role == 'company':
                profile = getattr(request._user, 'company_profile', None)
                if not profile:
                    return JsonResponse({
                        "success": False,
                        "message": "Complete your company profile",
                        "errno": 0x61
                    }, status=403)
                    
        return self.get_response(request)