# notifications/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from users.decorators import authenticate_token
from .models import Notification

@authenticate_token
@require_http_methods(["GET"])
def list_notifications(request):
    try:
        status = request.GET.get('status', 'unread')  # 'all', 'read', 'unread'
        
        notifications = request._user.notifications.all()
        
        if status == 'unread':
            notifications = notifications.filter(is_read=False)
        elif status == 'read':
            notifications = notifications.filter(is_read=True)
        
        data = [{
            'id': n.id,
            'type': n.notification_type,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
            'related_entities': {
                'interview_id': n.related_interview.id if n.related_interview else None,
                'application_id': n.related_application.id if n.related_application else None
            }
        } for n in notifications[:50]]  # Limit to 50 most recent
        
        return JsonResponse({
            'success': True,
            'count': len(data),
            'unread_count': request._user.notifications.filter(is_read=False).count(),
            'notifications': data
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@authenticate_token
@csrf_exempt
@require_http_methods(["POST"])
def mark_as_read(request, notification_id):
    try:
        notification = request._user.notifications.get(id=notification_id)
        notification.mark_as_read()
        
        return JsonResponse({
            'success': True,
            'unread_count': request._user.notifications.filter(is_read=False).count()
        })
    
    except Notification.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Notification not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)