from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_notifications, name='list-notifications'),
    path('<int:notification_id>/read/', views.mark_as_read, name='mark-read'),
]