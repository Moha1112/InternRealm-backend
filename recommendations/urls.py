from django.urls import path
from . import views

urlpatterns = [
    path('for-me/', 
         views.student_recommendations, 
         name='student-recommendations'),
    path('<int:internship_id>/recommended-candidates/', 
         views.candidate_recommendations, 
         name='candidate-recommendations'),
]