# recommendations/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from users.decorators import authenticate_token, role_required

@authenticate_token
@role_required('student')
@require_http_methods(["GET"])
def student_recommendations(request):
    try:
        from .utils import get_student_recommendations
        
        internships = get_student_recommendations(request._user, 10)
        
        data = [{
            'id': i.id,
            'title': i.title,
            'company': i.company.company_name,
            'match_score': float(i.match_score),
            'deadline': i.application_deadline.isoformat()
        } for i in internships]
        
        return JsonResponse({
            'success': True,
            'recommendations': data,
            'last_updated': request._user.last_login.isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@authenticate_token
@role_required('company')
@require_http_methods(["GET"])
def candidate_recommendations(request, internship_id):
    try:
        from .utils import get_candidate_recommendations
        from profiles.models import StudentCV
        
        internship = request._user.company_profile.internships.get(id=internship_id)
        applications = get_candidate_recommendations(internship, 10)
        
        data = [{
            'application_id': app.id,
            'student': {
                'id': app.student.id,
                'name': app.student.get_full_name(),
                'email': app.student.email
            },
            'match_score': float(app.match_score),
            'cv_highlights': {
                'skills': app.cv.skills[:5],
                'experience': app.cv.experience[:2]
            }
        } for app in applications]
        
        return JsonResponse({
            'success': True,
            'internship_title': internship.title,
            'candidates': data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)