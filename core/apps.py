from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Outlook Token 管理核心'

    def ready(self):
        """应用启动时执行"""
        # TODO: 启动定时任务
        # TODO: 初始化配置
        pass
