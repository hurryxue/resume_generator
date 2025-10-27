# 文件: core/models.py

from django.db import models
import uuid
from datetime import datetime


class Account(models.Model):
    """Outlook 账号模型"""

    STATUS_CHOICES = [
        ('normal', '正常'),
        ('expired', '过期'),
        ('abnormal', '异常'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255, verbose_name='邮箱地址')
    client_id = models.CharField(max_length=255, verbose_name='Client ID')
    refresh_token = models.TextField(verbose_name='刷新令牌（明文）')
    expires_at = models.DateTimeField(verbose_name='令牌过期时间')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='normal', verbose_name='状态')
    last_updated = models.DateTimeField(auto_now=True, verbose_name='上次更新时间')
    remark = models.CharField(max_length=200, blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'accounts'
        verbose_name = 'Outlook 账号'
        verbose_name_plural = 'Outlook 账号'
        ordering = ['-created_at']

    def __str__(self):
        return self.email


class Config(models.Model):
    """应用配置模型"""

    id = models.AutoField(primary_key=True)
    update_interval_days = models.IntegerField(default=3, verbose_name='更新周期（天）')
    update_time = models.TimeField(default='02:00', verbose_name='每日更新时间')
    advance_update_hours = models.IntegerField(default=24, verbose_name='提前更新小时数')
    max_retry_count = models.IntegerField(default=3, verbose_name='最大重试次数')
    local_port = models.IntegerField(default=8000, verbose_name='本地端口')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'config'
        verbose_name = '应用配置'
        verbose_name_plural = '应用配置'

    def __str__(self):
        return 'App Config'


class TokenLog(models.Model):
    """Token 更新日志模型"""

    OPERATION_TYPE_CHOICES = [
        ('auto_update', '自动更新'),
        ('manual_update', '手动更新'),
    ]

    RESULT_CHOICES = [
        ('success', '成功'),
        ('failed', '失败'),
    ]

    id = models.CharField(primary_key=True, max_length=50, editable=False)
    operation_time = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')
    email = models.EmailField(max_length=255, verbose_name='账号邮箱')
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPE_CHOICES, verbose_name='操作类型')
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, verbose_name='操作结果')
    result_detail = models.TextField(verbose_name='结果详情')

    class Meta:
        db_table = 'token_logs'
        verbose_name = 'Token 更新日志'
        verbose_name_plural = 'Token 更新日志'
        ordering = ['-operation_time']

    def __str__(self):
        return f'{self.email} - {self.operation_time}'
