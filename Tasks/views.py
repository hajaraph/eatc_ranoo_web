from celery.result import AsyncResult
from django.http import JsonResponse


def check_task_status(request, task_id):
    result = AsyncResult(task_id)
    return JsonResponse({'task_id': task_id, 'status': result.status, 'result': result.result})
