from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
import re


def validate_email(email):
    """验证邮箱格式"""
    validator = EmailValidator()
    try:
        validator(email)
        return True
    except ValidationError:
        return False


def validate_rfc3339_datetime(dt_string):
    """验证 RFC 3339 时间格式"""
    try:
        datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
        return True
    except ValueError:
        return False


def validate_password(password):
    """
    验证密码强度：
    - 8 位及以上
    - 包含大小写字母、数字、特殊字符中的三种
    """
    if len(password) < 8:
        return False, '密码长度至少为 8 位'

    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password))

    count = sum([has_upper, has_lower, has_digit, has_special])

    if count < 3:
        return False, '密码必须包含大小写字母、数字、特殊字符中的三种'

    return True, ''


def validate_port(port):
    """验证端口号"""
    if not isinstance(port, int):
        return False, '端口号必须是整数'

    if port < 1024 or port > 65535:
        return False, '端口号范围为 1024-65535'

    return True, ''


def validate_update_interval(days):
    """验证更新周期"""
    if not isinstance(days, int):
        return False, '更新周期必须是整数'

    if days < 1 or days > 30:
        return False, '更新周期范围为 1-30 天'

    return True, ''


def validate_advance_hours(hours):
    """验证提前更新小时数"""
    if not isinstance(hours, int):
        return False, '提前更新小时数必须是整数'

    if hours < 1 or hours > 72:
        return False, '提前更新小时数范围为 1-72'

    return True, ''


def validate_retry_count(count):
    """验证重试次数"""
    if not isinstance(count, int):
        return False, '重试次数必须是整数'

    if count < 1 or count > 5:
        return False, '重试次数范围为 1-5'

    return True, ''
