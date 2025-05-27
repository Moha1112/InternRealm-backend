from datetime import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from users.decorators import authenticate_token, strict_body_to_json, role_required
from .models import Internship, Application, Interview, Evaluation
from .serializers import EvaluationSerializer
from users.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_integer, DecimalValidator
from .pagination import CustomPagination


@authenticate_token
@csrf_exempt
@require_http_methods(["GET"])
def list_internships(request):
    try:
        from django.db.models import Q
        
        # Validate pagination parameters
        page_size = request.GET.get('page_size', 20)
        try:
            if page_size:
                validate_integer(page_size)
                page_size = int(page_size)
                if page_size < 1 or page_size > 100:
                    raise ValidationError("Page size must be between 1 and 100")
        except ValidationError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

        # Initialize base queryset
        queryset = Internship.objects.filter(status='published').select_related('company')
        
        # Initialize filter conditions
        filters = Q()
        
        # 1. Location Filter (supports exact, contains, and remote)
        location = request.GET.get('location')
        if location:
            if location.lower() == 'remote':
                filters &= Q(remote_option=True)
            elif location.startswith('"') and location.endswith('"'):
                # Exact match for quoted locations (e.g., "New York")
                filters &= Q(location__iexact=location.strip('"'))
            else:
                # Contains search for unquoted locations
                filters &= Q(location__icontains=location)
        
        # 2. Duration Filter (min and max)
        min_duration = request.GET.get('min_duration')
        max_duration = request.GET.get('max_duration')
        if min_duration or max_duration:
            try:
                if min_duration:
                    validate_integer(min_duration)
                    filters &= Q(duration_months__gte=int(min_duration))
                if max_duration:
                    validate_integer(max_duration)
                    filters &= Q(duration_months__lte=int(max_duration))
            except ValidationError:
                return JsonResponse({
                    'success': False,
                    'error': 'Duration must be a positive integer'
                }, status=400)
        
        # 3. Salary/Paid Status Filter
        is_paid = request.GET.get('is_paid')
        if is_paid and is_paid.lower() in ['true', 'false']:
            filters &= Q(is_paid=(is_paid.lower() == 'true'))
        
        min_salary = request.GET.get('min_salary')
        if min_salary:
            try:
                DecimalValidator(10, 2)(min_salary)
                filters &= Q(salary__gte=float(min_salary))
            except ValidationError:
                return JsonResponse({
                    'success': False,
                    'error': 'Minimum salary must be a valid number'
                }, status=400)
        
        # 4. Company Filter
        company_id = request.GET.get('company_id')
        if company_id:
            try:
                validate_integer(company_id)
                filters &= Q(company_id=int(company_id))
            except ValidationError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid company ID'
                }, status=400)
        
        # 5. Remote Filter (can be combined with location)
        remote_only = request.GET.get('remote_only')
        if remote_only and remote_only.lower() == 'true':
            filters &= Q(remote_option=True)
        
        # 6. Deadline Filter (upcoming or all)
        upcoming_only = request.GET.get('upcoming_only')
        if upcoming_only and upcoming_only.lower() == 'true':
            from django.utils import timezone
            filters &= Q(application_deadline__gte=timezone.now().date())
        
        # 7. Keyword Search (title/description)
        search_term = request.GET.get('search')
        if search_term:
            filters &= (
                Q(title__icontains=search_term) |
                Q(description__icontains=search_term) |
                Q(requirements__icontains=search_term)
            )
        
        # Apply all filters
        queryset = queryset.filter(filters)
        
        # 8. Sorting
        sort_by = request.GET.get('sort_by', '-created_at')
        valid_sort_options = {
            'recent': '-created_at',
            'deadline': 'application_deadline',
            'salary': '-salary',
            'duration': '-duration_months',
            'title': 'title'
        }
        sort_field = valid_sort_options.get(sort_by.lower(), '-created_at')
        queryset = queryset.order_by(sort_field)
        
        # Paginate results
        paginator = CustomPagination()
        result_page = paginator.paginate_queryset(queryset, request)
        
        # Prepare response data
        data = [{
            'id': i.id,
            'title': i.title,
            'company': {
                'id': i.company.id,
                'name': i.company.company_name,
                'logo': getattr(i.company, 'logo_url', None)
            },
            'location': {
                'address': i.location,
                'coordinates': i.coordinates,
                'is_remote': i.remote_option
            },
            'duration': i.duration_months,
            'is_paid': i.is_paid,
            'salary': float(i.salary) if i.salary else None,
            'deadline': i.application_deadline.isoformat(),
            'created_at': i.created_at.isoformat()
        } for i in result_page]
        
        # Return paginated response
        response_data = paginator.get_paginated_response(data)
        response_data['data']['filters'] = {
            'applied': {k: v for k, v in request.GET.items() if k != 'page_size'},
            'available': {
                'sort_options': list(valid_sort_options.keys()),
                'location_types': ['exact match (use quotes)', 'contains', 'remote']
            }
        }
        
        return JsonResponse(response_data)
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@authenticate_token
@role_required('company')
@csrf_exempt
@require_http_methods(["POST"])
@strict_body_to_json
def create_internship(request):
    try:
        from django.core.exceptions import ValidationError
        from .validations import validate_future_date, validate_salary

        company = request._user.company_profile
        data = request.parsed_data

        # Required fields validation
        required_fields = ['title', 'description', 'requirements', 
                         'duration_months', 'location', 'application_deadline']
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'success': False,
                    'error': f'Missing required field: {field}',
                    'code': 'MISSING_FIELD'
                }, status=400)

        # Date validation
        try:
            validate_future_date(data['application_deadline'])
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'code': 'INVALID_DATE'
            }, status=400)

        # Salary validation
        try:
            validate_salary({
                'is_paid': data.get('is_paid', False),
                'salary': data.get('salary')
            })
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'code': 'INVALID_SALARY'
            }, status=400)
        
        # Validate coordinates if provided
        if 'latitude' in data or 'longitude' in data:
            try:
                lat = float(data.get('latitude')) if data.get('latitude') else None
                lng = float(data.get('longitude')) if data.get('longitude') else None
                if ((lat and not (-90 <= lat <= 90)) or 
                    (lng and not (-180 <= lng <= 180))):
                    raise ValidationError("Invalid coordinates range")
                if bool(lat) != bool(lng):
                    raise ValidationError("Both latitude and longitude must be provided")
            except (ValueError, TypeError) as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e),
                    'code': 'INVALID_COORDINATES'
                }, status=400)

        # Create internship
        internship = Internship(
            company=company,
            title=data['title'],
            description=data['description'],
            requirements=data['requirements'],
            duration_months=int(data['duration_months']),
            is_paid=data.get('is_paid', False),
            salary=data.get('salary'),
            location=data['location'],
            remote_option=data.get('remote_option', False),
            application_deadline=data['application_deadline'],
            longitude=data.get('longitude'),
            latitude=data.get('latitude'),
        )

        # Full model validation
        internship.full_clean()
        internship.save()

        # Return success response with additional data
        return JsonResponse({
            'success': True,
            'internship': {
                'id': internship.id,
                'title': internship.title,
                'company_id': company.id,
                'created_at': internship.created_at.isoformat(),
                'location_data': {
                    'address': internship.location,
                    'coordinates': internship.coordinates
                }
            }
        }, status=201)

    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'VALIDATION_ERROR',
            'details': e.message_dict if hasattr(e, 'message_dict') else None
        }, status=400)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred',
            'code': 'SERVER_ERROR'
        }, status=500)

@authenticate_token
@role_required('company')
@csrf_exempt
@require_http_methods(["PUT"])
@strict_body_to_json
def edit_internship(request, internship_id):
    try:
        from django.core.exceptions import ValidationError, ObjectDoesNotExist
        from .validations import validate_future_date, validate_salary

        company = request._user.company_profile
        data = request.parsed_data

        # Get existing internship
        try:
            internship = Internship.objects.get(id=internship_id, company=company)
        except ObjectDoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Internship not found or not owned by your company',
                'code': 'NOT_FOUND'
            }, status=404)

        # Date validation if provided
        if 'application_deadline' in data:
            try:
                validate_future_date(data['application_deadline'])
                internship.application_deadline = data['application_deadline']
            except ValidationError as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e),
                    'code': 'INVALID_DATE'
                }, status=400)

        # Salary validation if provided
        if 'is_paid' in data or 'salary' in data:
            try:
                validate_salary({
                    'is_paid': data.get('is_paid', internship.is_paid),
                    'salary': data.get('salary', internship.salary)
                })
                if 'is_paid' in data:
                    internship.is_paid = data['is_paid']
                if 'salary' in data:
                    internship.salary = data['salary']
            except ValidationError as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e),
                    'code': 'INVALID_SALARY'
                }, status=400)

        # Validate coordinates if provided
        if 'latitude' in data or 'longitude' in data:
            try:
                lat = float(data.get('latitude')) if data.get('latitude') else None
                lng = float(data.get('longitude')) if data.get('longitude') else None
                if ((lat and not (-90 <= lat <= 90)) or
                    (lng and not (-180 <= lng <= 180))):
                    raise ValidationError("Invalid coordinates range")
                if bool(lat) != bool(lng):
                    raise ValidationError("Both latitude and longitude must be provided")
                internship.latitude = lat
                internship.longitude = lng
            except (ValueError, TypeError) as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e),
                    'code': 'INVALID_COORDINATES'
                }, status=400)

        # Update standard fields
        updatable_fields = [
            'title', 'description', 'requirements',
            'duration_months', 'location', 'remote_option'
        ]
        for field in updatable_fields:
            if field in data:
                setattr(internship, field, data[field])

        # Full model validation
        internship.full_clean()
        internship.save()

        # Return success response
        return JsonResponse({
            'success': True,
            'internship': {
                'id': internship.id,
                'title': internship.title,
                'company_id': company.id,
                'updated_at': internship.updated_at.isoformat(),
                'location_data': {
                    'address': internship.location,
                    'coordinates': internship.coordinates
                }
            }
        })

    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'VALIDATION_ERROR',
            'details': e.message_dict if hasattr(e, 'message_dict') else None
        }, status=400)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred',
            'code': 'SERVER_ERROR'
        }, status=500)

@authenticate_token
@role_required('student')
@csrf_exempt
@require_http_methods(["POST"])
@strict_body_to_json
def apply_for_internship(request):
    try:
        student = request._user
        data = request.parsed_data
        
        # Get or create default CV
        cv = student.cvs.filter(is_default=True).first()
        if not cv:
            return JsonResponse({
                'success': False,
                'error': 'No CV available. Please create one first.',
                'code': 'NO_CV'
            }, status=400)

        application = Application.objects.create(
            internship_id=data['internship_id'],
            student=student,
            cv=cv,
            cover_letter=data['cover_letter']
        )
        
        return JsonResponse({
            'success': True,
            'application_id': application.id
        }, status=201)
    
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e),
            'code': 'APPLICATION_ERROR'
        }, status=400)

@authenticate_token
@csrf_exempt
@require_http_methods(["GET"])
def internship_detail(request, internship_id):
    try:
        internship = Internship.objects.select_related('company').get(
            id=internship_id,
            status='published'  # Only show published internships
        )
        
        response_data = {
            'id': internship.id,
            'title': internship.title,
            'company': {
                'id': internship.company.user.id,
                'name': internship.company.company_name,
                'logo': internship.company.logo_url
            },
            'description': internship.description,
            'requirements': internship.requirements,
            'duration_months': internship.duration_months,
            'is_paid': internship.is_paid,
            'salary': float(internship.salary) if internship.salary else None,
            'location': internship.location,
            'remote_option': internship.remote_option,
            'deadline': internship.application_deadline.isoformat(),
            'created_at': internship.created_at.isoformat(),
            'coordinates': internship.coordinates,
        }
        
        # Add application status if user is student
        if request._user.role == 'student':
            try:
                application = Application.objects.get(
                    internship=internship,
                    student=request._user
                )
                response_data['application_status'] = application.status
            except Application.DoesNotExist:
                response_data['application_status'] = 'not_applied'
        
        return JsonResponse({
            'success': True,
            'internship': response_data
        })
        
    except Internship.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Internship not found',
            'errno': 0x80  # Not found error code
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e),
            'errno': 0x81  # General error code
        }, status=500)


@authenticate_token
@role_required('company')
@csrf_exempt
@require_http_methods(["PUT"])
@strict_body_to_json
def edit_internship(request, internship_id):
    try:
        from django.core.exceptions import ValidationError, ObjectDoesNotExist
        from .validations import validate_future_date

        company = request._user.company_profile
        data = request.parsed_data

        # Get existing internship
        try:
            internship = Internship.objects.get(id=internship_id, company=company)
        except ObjectDoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Internship not found or not owned by your company',
                'code': 'NOT_FOUND'
            }, status=404)

        # Update standard fields
        updatable_fields = [
            'title', 'description', 'requirements',
            'duration_months', 'location', 'remote_option',
            'status', 'application_deadline'
        ]

        for field in updatable_fields:
            if field in data:
                setattr(internship, field, data[field])

        # Handle salary fields
        if 'is_paid' in data:
            internship.is_paid = data['is_paid']
        if 'salary' in data:
            internship.salary = data['salary'] if data['salary'] is not None else None

        # Validate and update coordinates
        if 'latitude' in data or 'longitude' in data:
            try:
                lat = float(data['latitude']) if 'latitude' in data and data['latitude'] is not None else None
                lng = float(data['longitude']) if 'longitude' in data and data['longitude'] is not None else None

                if (lat is not None and not (-90 <= lat <= 90)) or (lng is not None and not (-180 <= lng <= 180)):
                    raise ValidationError("Invalid coordinates range")
                if (lat is None) != (lng is None):
                    raise ValidationError("Both latitude and longitude must be provided")

                internship.latitude = lat
                internship.longitude = lng
            except (ValueError, TypeError) as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e),
                    'code': 'INVALID_COORDINATES'
                }, status=400)

        # Validate status
        if 'status' in data and data['status'] not in dict(Internship.STATUS_CHOICES):
            return JsonResponse({
                'success': False,
                'error': 'Invalid status value',
                'code': 'INVALID_STATUS'
            }, status=400)

        # Validate future date if deadline is being updated
        if 'application_deadline' in data:
            try:
                validate_future_date(data['application_deadline'])
            except ValidationError as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e),
                    'code': 'INVALID_DATE'
                }, status=400)

        # Full model validation
        try:
            internship.full_clean()
            internship.save()
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
                'code': 'VALIDATION_ERROR',
                'details': e.message_dict if hasattr(e, 'message_dict') else None
            }, status=400)

        # Return success response
        return JsonResponse({
            'success': True,
            'internship': {
                'id': internship.id,
                'title': internship.title,
                'status': internship.status,
                'company_id': company.id,
                'created_at': internship.created_at.isoformat(),
                'updated_at': internship.updated_at.isoformat(),
                'location_data': {
                    'address': internship.location,
                    'coordinates': internship.coordinates,
                    'is_remote': internship.remote_option
                },
                'compensation': {
                    'is_paid': internship.is_paid,
                    'salary': float(internship.salary) if internship.salary else None
                },
                'duration_months': internship.duration_months,
                'application_deadline': internship.application_deadline.isoformat()
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred',
            'code': 'SERVER_ERROR'
        }, status=500)

@authenticate_token
@csrf_exempt
@require_http_methods(["GET"])
def list_applications(request):
    try:
        if request._user.role == 'student':
            # Student sees their own applications
            applications = Application.objects.filter(
                student=request._user
            ).select_related('internship', 'internship__company')
            
            data = [{
                'id': app.id,
                'internship': {
                    'id': app.internship.id,
                    'title': app.internship.title,
                    'company': app.internship.company.company_name
                },
                'status': app.status,
                'applied_at': app.applied_at.isoformat(),
                'last_updated': app.updated_at.isoformat()
            } for app in applications]
            
        elif request._user.role == 'company':
            # Company sees applications to their internships
            applications = Application.objects.filter(
                internship__company=request._user.company_profile
            ).select_related('student', 'student__student_profile', 'internship')
            
            data = [{
                'id': app.id,
                'internship': {
                    'id': app.internship.id,
                    'title': app.internship.title
                },
                'student': {
                    'id': app.student.id,
                    'name': f"{app.student.first_name} {app.student.last_name}",
                    'university': app.student.student_profile.university if hasattr(app.student, 'student_profile') else None
                },
                'status': app.status,
                'applied_at': app.applied_at.isoformat(),
                'cover_letter': app.cover_letter,
                'resume_url': app.resume_url
            } for app in applications]
            
        else:
            return JsonResponse({
                'success': False,
                'message': 'Unauthorized access',
                'errno': 0x70  # Access denied error code
            }, status=403)
            
        return JsonResponse({
            'success': True,
            'applications': data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e),
            'errno': 0x81  # General error code
        }, status=500)

@authenticate_token
@role_required('company')
@csrf_exempt
@require_http_methods(["PATCH"])
@strict_body_to_json
def update_application_status(request, application_id):
    try:
        application = Application.objects.get(
            id=application_id,
            internship__company=request._user.company_profile
        )
        
        new_status = request.parsed_data.get('status')
        if new_status not in dict(Application.STATUS_CHOICES):
            return JsonResponse({
                'success': False,
                'message': 'Invalid status',
                'errno': 0x82
            }, status=400)
            
        application.status = new_status
        application.save()
        
        return JsonResponse({
            'success': True,
            'new_status': new_status
        })
        
    except Application.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Application not found',
            'errno': 0x80
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e),
            'errno': 0x81
        }, status=500)

# In views.py
from pgvector.django import (
    MaxInnerProduct,  # For cosine similarity when vectors normalized
    CosineDistance,  # For cosine distance
)

import numpy as np

@authenticate_token
@csrf_exempt
@require_http_methods(["POST"])
@strict_body_to_json
def semantic_search(request):
    try:
        from .utils import generate_embedding  # Local import
        
        query = request.parsed_data.get('query', '')
        query_embedding = generate_embedding(query)
        
        results = Internship.objects.filter(
            status='published'
        ).annotate(
            similarity=1 - MaxInnerProduct('embedding', query_embedding)
        ).order_by('similarity')[:20]
    
        serialized = [{
            'id': i.id,
            'title': i.title,
            'company': i.company.company_name,
            'description': i.description[:200] + '...' if i.description else '',
            'score': float(1 / (1 + np.exp(i.distance)))  # Convert distance to 0-1 score
        } for i in results]
        
        return JsonResponse({
            'success': True,
            'results': serialized,
            'count': len(serialized)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
# Combine semantic and keyword search
@authenticate_token
@csrf_exempt
@require_http_methods(["POST"])
@strict_body_to_json
def hybrid_search(request):
    from django.db.models import Q
    from .utils import generate_embedding  # Local import

    query = request.parsed_data.get('query', '')
    
    # Keyword filters
    filters = Q(status='published')
    if request.parsed_data.get('location'):
        filters &= Q(location__icontains=request.parsed_data['location'])
    
    # Semantic part
    query_embedding = generate_embedding(query)
    
    results = Internship.objects.filter(filters).annotate(
        similarity=1 - MaxInnerProduct('embedding', query_embedding)
    ).order_by('similarity')[:20]
    
    serialized = [{
        'id': i.id,
        'title': i.title,
        'company': i.company.company_name,
        'description': i.description[:200] + '...' if i.description else '',
        'score': float(1 / (1 + np.exp(i.distance)))  # Convert distance to 0-1 score
    } for i in results]
    
    return JsonResponse({
        'success': True,
        'results': serialized,
        'count': len(serialized)
    })


@csrf_exempt
@require_http_methods(["POST"])
@strict_body_to_json
def get_embedding(request):
    from django.db.models import Q
    from .utils import generate_embedding  # Local import

    
    query = request.parsed_data.get('q', '')

    # Semantic part
    query_embedding = generate_embedding(query)

    return JsonResponse({
        'success': True,
        'embedding': query_embedding.tolist(),
        'length': len(query_embedding)
    })


# Interview Scheduling
@authenticate_token
@role_required('company')
@csrf_exempt
@require_http_methods(["POST"])
@strict_body_to_json
def schedule_interview(request, application_id):
    try:
        application = Application.objects.get(
            id=application_id,
            internship__company=request._user.company_profile
        )
        
        data = request.parsed_data
        
        # Validate required fields
        required_fields = ['interview_type', 'start_time', 'end_time']
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'success': False,
                    'error': f'Missing required field: {field}',
                    'code': 'MISSING_FIELD'
                }, status=400)
        
        # Type-specific validation
        if data['interview_type'] == 'onsite' and 'location' not in data:
            return JsonResponse({
                'success': False,
                'error': 'Location required for on-site interviews',
                'code': 'MISSING_LOCATION'
            }, status=400)
            
        if data['interview_type'] == 'video' and 'meeting_url' not in data:
            return JsonResponse({
                'success': False,
                'error': 'Meeting URL required for video interviews',
                'code': 'MISSING_URL'
            }, status=400)
        
        # Create interview
        interview = Interview(
            application=application,
            interview_type=data['interview_type'],
            start_time=data['start_time'],
            end_time=data['end_time'],
            location=data.get('location'),
            meeting_url=data.get('meeting_url'),
            notes=data.get('notes', '')
        )
        
        interview.full_clean()
        interview.save()
        
        # Add interviewers if specified
        if 'interviewers' in data:
            interviewers = User.objects.filter(
                id__in=data['interviewers'],
                company_profile=request._user.company_profile
            )
            interview.interviewers.set(interviewers)
        
        # Update application status
        if not application.interviews.exists():
            application.status = 'interviewing'
            application.save()
        
        return JsonResponse({
            'success': True,
            'interview': {
                'id': interview.id,
                'type': interview.interview_type,
                'status': interview.status,
                'start_time': interview.start_time.isoformat(),
                'end_time': interview.end_time.isoformat(),
                'duration_minutes': int((interview.end_time - interview.start_time).total_seconds() / 60),
                'location': interview.location,
                'meeting_url': interview.meeting_url,
                'interviewers': [
                    {'id': u.id, 'name': u.get_full_name()}
                    for u in interview.interviewers.all()
                ]
            }
        }, status=201)
    
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'VALIDATION_ERROR'
        }, status=400)
    except Application.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Application not found',
            'code': 'NOT_FOUND'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'SCHEDULING_ERROR'
        }, status=500)

@authenticate_token
@require_http_methods(["GET"])
@csrf_exempt
@strict_body_to_json
def list_application_interviews(request, application_id):
    try:
        # Verify application access
        if request._user.role == 'company':
            application = Application.objects.get(
                id=application_id,
                internship__company=request._user.company_profile
            )
        else:  # student
            application = Application.objects.get(
                id=application_id,
                student=request._user
            )

        # Get query parameters
        status_filter = request.GET.get('status')
        interview_type = request.GET.get('type')
        
        # Build queryset
        interviews = Interview.objects.filter(
            application=application
        ).select_related(
            'application__internship',
            'application__student'
        ).order_by('-start_time')

        # Apply filters
        if status_filter:
            interviews = interviews.filter(status=status_filter)
        if interview_type:
            interviews = interviews.filter(interview_type=interview_type)

        # Prepare response
        data = []
        for interview in interviews:
            interview_data = {
                'id': interview.id,
                'type': interview.get_interview_type_display(),
                'type_code': interview.interview_type,
                'status': interview.get_status_display(),
                'status_code': interview.status,
                'start_time': interview.start_time.isoformat(),
                'end_time': interview.end_time.isoformat(),
                'duration_minutes': interview.duration_minutes,
                'location': interview.location,
                'meeting_url': interview.meeting_url,
                'notes': interview.notes,
                'created_at': interview.created_at.isoformat(),
                'interviewers': [
                    {
                        'id': user.id,
                        'name': user.get_full_name(),
                        'email': user.email
                    }
                    for user in interview.interviewers.all()
                ],
                'application_info': {
                    'student_name': interview.application.student.get_full_name(),
                    'internship_title': interview.application.internship.title
                }
            }
            data.append(interview_data)

        return JsonResponse({
            'success': True,
            'count': len(data),
            'filters': {
                'applied': {
                    'status': status_filter,
                    'type': interview_type
                },
                'available': {
                    'statuses': dict(Interview.STATUS_CHOICES),
                    'types': dict(Interview.INTERVIEW_TYPES)
                }
            },
            'interviews': data
        })

    except Application.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Application not found or access denied',
            'code': 'NOT_FOUND'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'LIST_ERROR'
        }, status=500)

@authenticate_token
@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
@strict_body_to_json
def manage_interview(request, interview_id):
    try:
        # Get interview with proper permissions
        if request._user.role == 'company':
            interview = Interview.objects.select_related(
                'application__internship__company',
                'application__student'
            ).get(
                id=interview_id,
                application__internship__company=request._user.company_profile
            )
        else:  # student
            interview = Interview.objects.select_related(
                'application__student'
            ).get(
                id=interview_id,
                application__student=request._user
            )

        # Handle different methods
        if request.method == "GET":
            return JsonResponse({
                'success': True,
                'interview': {
                    'id': interview.id,
                    'type': interview.get_interview_type_display(),
                    'type_code': interview.interview_type,
                    'status': interview.get_status_display(),
                    'status_code': interview.status,
                    'start_time': interview.start_time.isoformat(),
                    'end_time': interview.end_time.isoformat(),
                    'duration_minutes': interview.duration_minutes,
                    'location': interview.location,
                    'meeting_url': interview.meeting_url,
                    'notes': interview.notes,
                    'interviewers': [
                        {
                            'id': user.id,
                            'name': user.get_full_name(),
                            'email': user.email
                        }
                        for user in interview.interviewers.all()
                    ],
                    'application': {
                        'id': interview.application.id,
                        'internship_title': interview.application.internship.title,
                        'student_name': interview.application.student.get_full_name()
                    }
                }
            })

        elif request.method == "PUT":
            data = request.parsed_data
            update_fields = []

            # Validate and update fields
            if 'status' in data:
                interview.status = data['status']
                update_fields.append('status')

            if 'notes' in data:
                interview.notes = data['notes']
                update_fields.append('notes')

            if 'start_time' in data or 'end_time' in data:
                new_start = data.get('start_time', interview.start_time)
                new_end = data.get('end_time', interview.end_time)
                if new_end <= new_start:
                    raise ValidationError("End time must be after start time")
                interview.start_time = new_start
                interview.end_time = new_end
                update_fields.extend(['start_time', 'end_time'])

            if 'interviewers' in data and request._user.role == 'company':
                interviewers = User.objects.filter(
                    id__in=data['interviewers'],
                    company_profile=request._user.company_profile
                )
                interview.interviewers.set(interviewers)

            interview.save(update_fields=update_fields)

            return JsonResponse({
                'success': True,
                'updated_fields': update_fields,
                'interview': {
                    'status': interview.status,
                    'start_time': interview.start_time.isoformat(),
                    'end_time': interview.end_time.isoformat()
                }
            })

        elif request.method == "DELETE":
            # Prevent deleting completed interviews
            if interview.status == 'completed':
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot delete completed interviews',
                    'code': 'DELETE_COMPLETED'
                }, status=400)

            interview_id = interview.id
            interview.delete()

            return JsonResponse({
                'success': True,
                'message': f'Interview {interview_id} deleted',
                'deleted_at': timezone.now().isoformat()
            })

    except Interview.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Interview not found or access denied',
            'code': 'NOT_FOUND'
        }, status=404)
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'VALIDATION_ERROR'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'MANAGEMENT_ERROR'
        }, status=500)


@authenticate_token
@csrf_exempt
@role_required('company')
@require_http_methods(["POST"])
@strict_body_to_json
def submit_evaluation(request, interview_id):
    try:
        interview = Interview.objects.get(
            id=interview_id,
            interviewers=request._user,
            status='completed'
        )
        
        # Check if evaluation already exists
        if Evaluation.objects.filter(interview=interview, evaluator=request._user).exists():
            return JsonResponse({
                'success': False,
                'error': 'Evaluation already submitted',
                'code': 'EVALUATION_EXISTS'
            }, status=400)
        
        serializer = EvaluationSerializer(
            data=request.parsed_data,
            context={'evaluator': request._user}
        )
        serializer.is_valid(raise_exception=True)
        evaluation = serializer.save(
            interview=interview,
            evaluator=request._user
        )
        
        return JsonResponse({
            'success': True,
            'evaluation_id': evaluation.id,
            'overall_score': evaluation.overall_score
        }, status=201)
    
    except Interview.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Interview not found or not completed',
            'code': 'INVALID_INTERVIEW'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'SUBMISSION_ERROR'
        }, status=500)

@authenticate_token
@csrf_exempt
@require_http_methods(["GET"])
def get_evaluations(request, interview_id):
    try:
        # Company can see all, student can see their own
        if request._user.role == 'company':
            interview = Interview.objects.get(
                id=interview_id,
                application__internship__company=request._user.company_profile
            )
        else:
            interview = Interview.objects.get(
                id=interview_id,
                application__student=request._user
            )
        
        evaluations = Evaluation.objects.filter(
            interview=interview
        ).select_related('evaluator')
        
        serializer = EvaluationSerializer(evaluations, many=True)
        return JsonResponse({
            'success': True,
            'evaluations': serializer.data,
            'average_score': interview.get_average_score()
        })
    
    except Interview.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Interview not found',
            'code': 'NOT_FOUND'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'FETCH_ERROR'
        }, status=500)