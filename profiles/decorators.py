from functools import wraps
from django.http import JsonResponse

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request._user or request._user.role != 'admin':
            return JsonResponse({
                "success": False,
                "error": "Admin privileges required"
            }, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper

def profile_access_required(view_func):
    @wraps(view_func)
    def wrapper(request, user_id, *args, **kwargs):
        # Admin can access any profile
        if request._user.role == 'admin':
            return view_func(request, user_id, *args, **kwargs)
            
        # Users can only access their own profile
        if str(request._user.id) != str(user_id):
            return JsonResponse({
                "success": False,
                "message": "You don't have permission to access this profile",
                "errno": 0x73  # Insufficient permissions
            }, status=403)
            
        return view_func(request, user_id, *args, **kwargs)
    return wrapper