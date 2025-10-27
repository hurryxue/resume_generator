
from django.http import JsonResponse
from datetime import datetime


def success_response(data, message='操作成功', status_code=200):
    """统一成功响应格式"""
    return JsonResponse({
        'code': status_code,
        'message': message,
        'data': data,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, status=status_code)


def error_response(message, code=500, data=None):
    """统一错误响应格式"""
    return JsonResponse({
        'code': code,
        'message': message,
        'data': data,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, status=code)
