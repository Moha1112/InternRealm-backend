# recommendations/utils.py
from django.db.models import F
from pgvector.django import CosineDistance
from internships.models import Internship, Application

def get_student_recommendations(student, limit=5):
    """
    Get personalized internship recommendations for a student
    """
    cv = student.cvs.filter(is_default=True).first()
    if not cv or not cv.embedding:
        return Internship.objects.none()
    
    return Internship.objects.filter(
        status='published'
    ).annotate(
        match_score=1 - CosineDistance('embedding', cv.embedding)
    ).order_by(
        '-match_score',
        '-created_at'
    )[:limit]

def get_candidate_recommendations(internship, limit=5):
    """
    Get top candidates for an internship
    """
    if not internship.embedding:
        return Application.objects.none()
    
    return Application.objects.filter(
        internship=internship
    ).annotate(
        match_score=1 - CosineDistance('cv__embedding', internship.embedding)
    ).select_related(
        'student', 'cv'
    ).order_by(
        '-match_score'
    )[:limit]