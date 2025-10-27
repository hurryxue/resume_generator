# 文件: core/urls.py

from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
    # 前端页面
    path('', views.index, name='index'),
    path('accounts/', views.accounts_page, name='accounts_page'),
    path('config/', views.config_page, name='config_page'),
    path('logs/', views.logs_page, name='logs_page'),
    
    # 账号管理 API
    path('api/accounts/', views.AccountListView.as_view(), name='account_list'),
    path('api/accounts/refresh-status/', views.refresh_account_status, name='refresh_status'),
    path('api/accounts/<uuid:pk>/', views.AccountDetailView.as_view(), name='account_detail'),
    path('api/accounts/<uuid:pk>/update-token/', views.update_single_token, name='update_token'),
    path('api/accounts/refresh_all_tokens/', views.refresh_all_tokens, name='refresh_all_tokens'),
    
    # Token 获取 API
    path('api/access-token/', views.get_access_token, name='access_token'),
    path('api/batch-access-tokens/', views.batch_get_access_tokens, name='batch_get_access_tokens'),
    
    # 配置管理 API
    path('api/config/', views.ConfigView.as_view(), name='config'),
    path('api/config/reset/', views.reset_config, name='reset_config'),
    
    # 手动更新 API
    path('api/update/single/', views.update_single, name='update_single'),
    path('api/update/all/', views.update_all, name='update_all'),
    
    # 日志管理 API
    path('api/logs/', views.LogListView.as_view(), name='log_list'),
    path('api/logs/export/', views.export_logs, name='export_logs'),
    

    # # 系统信息 API
    # path('api/status/', views.get_status, name='status'),
    # path('api/health/', views.health_check, name='health'),
]