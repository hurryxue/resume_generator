class OutlookTokenException(Exception):
    """基础异常类"""
    pass


class ValidationException(OutlookTokenException):
    """参数验证异常"""
    pass


class AccountNotFoundException(OutlookTokenException):
    """账号不存在异常"""
    pass


class DuplicateEmailException(OutlookTokenException):
    """邮箱重复异常"""
    pass


class PortOccupiedException(OutlookTokenException):
    """端口被占用异常"""
    pass


class MicrosoftAPIException(OutlookTokenException):
    """微软 API 调用异常"""
    pass


class BackupException(OutlookTokenException):
    """备份异常"""
    pass


class RestoreException(OutlookTokenException):
    """恢复异常"""
    pass