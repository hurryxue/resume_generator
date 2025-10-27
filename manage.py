#!/usr/bin/env python
import os
import sys


def main():
    """运行管理命令"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "无法导入 Django。请确保已安装 Django 并且环境变量 DJANGO_SETTINGS_MODULE 已正确设置。"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

