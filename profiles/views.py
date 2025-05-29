from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from users.decorators import authenticate_token, strict_body_to_json, role_required
from users.models import User
from .models import StudentProfile, CompanyProfile, StudentCV, student_profile_to_dict, company_profile_to_dict
from .decorators import profile_access_required
import json

@csrf_exempt
@authenticate_token
@require_http_methods(["GET"])
def get_profile(request):
    user = request._user
    try:
        if user.role == 'student':
            data = student_profile_to_dict(user.student_profile)
        else:
            from internships.models import Application
            data = company_profile_to_dict(user.company_profile)
            data["stats"] = {
                "totalInternships": user.company_profile.internships.count(),
                "activeInternships": user.company_profile.internships.filter(status='published').count(),
                "applications": Application.objects.filter(
                    internship__company=user.company_profile
                ).count(),
                "hiredInterns": Application.objects.filter(
                    status='hired',
                    internship__company=user.company_profile
                ).count(),
            }
        
        return JsonResponse({
            "success": True,
            "profile": data
        })
    
    except (StudentProfile.DoesNotExist, CompanyProfile.DoesNotExist):
        return JsonResponse({
            "success": False,
            "message": "Profile not found",
            "errno": 0xA0
        }, status=404)

@csrf_exempt
@authenticate_token
@require_http_methods(["PATCH"])
def update_profile(request):
    user = request._user
    try:
        update_data = json.loads(request.body)        

        update_blacklist = ['user', 'created_at', 'updated_at', 'id', 'deleted_at', 'is_verified']
        
        profile = user.student_profile if user.role == 'student' else user.company_profile
        
        for field, value in update_data.items():
            if not field in update_blacklist:
                setattr(profile, field, value)
        
        profile.save()
        return JsonResponse({"success": True})
    
    except Exception as e:
        return JsonResponse({"success": False, "message": "Profile update failed", "error": str(e), "errno": 0x64}, status=400)

@csrf_exempt
@authenticate_token
@profile_access_required
def get_profile_by_id(request, user_id):
    try:
        target_user = get_object_or_404(User, id=user_id, deleted_at__isnull=True)
        
        # Admin gets full profile, others get basic info
        is_admin = request._user.role == 'admin'
        
        if target_user.role == 'student':
            profile = target_user.student_profile
            response_data = serialize_student_profile(profile, is_admin)
        else:
            profile = target_user.company_profile
            response_data = serialize_company_profile(profile, is_admin)
        
        return JsonResponse({
            "success": True,
            "profile": response_data,
            "is_own_profile": str(request._user.id) == str(user_id)
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e),
            "errno": 0xA2
        }, status=400)

def serialize_student_profile(profile, is_admin=False):
    data = student_profile_to_dict(profile)
    if not is_admin:
        # Remove sensitive fields for non-admins
        data.pop('gpa', None)
        data.pop('desired_salary', None)
    return data

def serialize_company_profile(profile, is_admin=False):
    data = company_profile_to_dict(profile)
    if not is_admin:
        # Remove sensitive fields for non-admins
        data['legal'].pop('tax_id', None)
        data['contact']['hr_contact']['email'] = ''
    return data



# CV

@authenticate_token
@role_required('student')
@csrf_exempt
@require_http_methods(["GET"])
def list_cvs(request):
    try:
        cvs = request._user.cvs.all().order_by('-is_default', '-updated_at')
        
        data = [{
            'id': cv.id,
            'title': cv.title,
            'is_default': cv.is_default,
            'education_count': len(cv.education),
            'experience_count': len(cv.experience),
            'skills_count': len(cv.skills),
            'updated_at': cv.updated_at.isoformat()
        } for cv in cvs]
        
        return JsonResponse({
            'success': True,
            'cvs': data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'CV_LIST_ERROR'
        }, status=500)



@authenticate_token
@role_required('student')
@csrf_exempt
@require_http_methods(["POST"])
@strict_body_to_json
def create_cv(request):
    try:
        data = request.parsed_data
        
        # Validate required fields
        if 'title' not in data:
            return JsonResponse({
                'success': False,
                'error': 'Title is required',
                'code': 'MISSING_TITLE'
            }, status=400)
        
        # Create CV
        cv = StudentCV.objects.create(
            user=request._user,
            title=data['title'],
            education=data.get('education', []),
            experience=data.get('experience', []),
            skills=data.get('skills', []),
            is_default=data.get('is_default', False)
        )
        
        # If set as default, unset others
        if cv.is_default:
            request._user.cvs.exclude(id=cv.id).update(is_default=False)
        
        return JsonResponse({
            'success': True,
            'cv_id': cv.id,
            'is_default': cv.is_default
        }, status=201)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'CV_CREATION_ERROR'
        }, status=400)
    
@authenticate_token
@role_required('student')
@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
@strict_body_to_json
def cv_detail(request, cv_id):
    try:
        cv = request._user.cvs.get(id=cv_id)
        
        if request.method == "GET":
            return JsonResponse({
                'success': True,
                'cv': {
                    'id': cv.id,
                    'title': cv.title,
                    'education': cv.education,
                    'experience': cv.experience,
                    'skills': cv.skills,
                    'is_default': cv.is_default,
                    'created_at': cv.created_at.isoformat(),
                    'updated_at': cv.updated_at.isoformat()
                }
            })
            
        elif request.method == "PUT":
            data = request.parsed_data
            
            # Update fields
            if 'title' in data:
                cv.title = data['title']
            if 'education' in data:
                cv.education = data['education']
            if 'experience' in data:
                cv.experience = data['experience']
            if 'skills' in data:
                cv.skills = data['skills']
            if 'is_default' in data:
                cv.is_default = data['is_default']
                if cv.is_default:
                    request._user.cvs.exclude(id=cv.id).update(is_default=False)
            
            cv.save()
            
            return JsonResponse({
                'success': True,
                'message': 'CV updated successfully'
            })
            
        elif request.method == "DELETE":
            if cv.is_default and request._user.cvs.count() > 1:
                # Set another CV as default before deletion
                new_default = request._user.cvs.exclude(id=cv.id).first()
                new_default.is_default = True
                new_default.save()
            
            cv.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'CV deleted successfully'
            })
            
    except StudentCV.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'CV not found',
            'code': 'CV_NOT_FOUND'
        }, status=404)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'CV_OPERATION_ERROR'
        }, status=400)

@authenticate_token
@role_required('student')
@csrf_exempt
@require_http_methods(["POST"])
def set_default_cv(request, cv_id):
    try:
        cv = request._user.cvs.get(id=cv_id)
        
        # Unset all other defaults
        request._user.cvs.exclude(id=cv.id).update(is_default=False)
        
        # Set this one as default
        cv.is_default = True
        cv.save()
        
        return JsonResponse({
            'success': True,
            'message': f'CV "{cv.title}" set as default'
        })
        
    except StudentCV.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'CV not found',
            'code': 'CV_NOT_FOUND'
        }, status=404)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'SET_DEFAULT_ERROR'
        }, status=400)

@authenticate_token
@csrf_exempt
@require_http_methods(["POST"])
@strict_body_to_json
def search_cvs(request):
    try:
        from internships.utils import generate_embedding
        from pgvector.django import CosineDistance
        
        query = request.parsed_data.get('query', '')
        query_embedding = generate_embedding(query)
        
        cvs = StudentCV.objects.annotate(
            similarity=1 - CosineDistance('embedding', query_embedding)
        ).order_by('-similarity')[:20]
        
        results = [{
            'id': cv.id,
            'student_name': cv.user.get_full_name(),
            'similarity': float(cv.similarity),
            'top_skills': cv.skills[:5]
        } for cv in cvs]
        
        return JsonResponse({'success': True, 'results': results})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)