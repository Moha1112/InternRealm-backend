from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_profile, name='get_profile'),
    path('update/', views.update_profile, name='update_profile'),
    path('<int:user_id>/', views.get_profile_by_id, name='profile_by_id'),

    path('cvs/', views.list_cvs, name='list-cvs'),
    path('cvs/create/', views.create_cv, name='create-cv'),
    path('cvs/<int:cv_id>/', views.cv_detail, name='cv-detail'),
    path('cvs/<int:cv_id>/set-default/', views.set_default_cv, name='set-default-cv'),
]