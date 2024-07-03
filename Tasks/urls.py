from django.urls import path

from Tasks.views import check_task_status

urlpatterns = [
    path('check_task_status/<str:task_id>/', check_task_status, name='check_task_status'),
]
