from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_internships, name='list-internships'),
    path('create/', views.create_internship, name='create-internship'),
    path('apply/', views.apply_for_internship, name='apply-internship'),
    path('<int:interview_id>/evaluations/', views.get_evaluations, name='get-evaluations'),
    path('<int:interview_id>/evaluate/', views.submit_evaluation, name='submit-evaluation'),
    path('<int:internship_id>/', views.internship_detail, name='internship-detail'),
    path('<int:internship_id>/edit', views.edit_internship, name='internship-detail'),

    path('applications/', views.list_applications, name='list-applications'),
    
    # Add these for company actions
    path('applications/<int:application_id>/status/', 
         views.update_application_status, 
         name='update-application-status'),
    path('search/', views.semantic_search, name='semantic-search'),
    path('get_embedding/', views.get_embedding, name='get-embedding')
]