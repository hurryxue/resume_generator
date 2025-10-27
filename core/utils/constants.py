# 账号状态
ACCOUNT_STATUS_NORMAL = 'normal'
ACCOUNT_STATUS_EXPIRED = 'expired'
ACCOUNT_STATUS_ABNORMAL = 'abnormal'

ACCOUNT_STATUS_CHOICES = [
    (ACCOUNT_STATUS_NORMAL, '正常'),
    (ACCOUNT_STATUS_EXPIRED, '过期'),
    (ACCOUNT_STATUS_ABNORMAL, '异常'),
]

# 操作类型
OPERATION_TYPE_AUTO = 'auto_update'
OPERATION_TYPE_MANUAL = 'manual_update'

OPERATION_TYPE_CHOICES = [
    (OPERATION_TYPE_AUTO, '自动更新'),
    (OPERATION_TYPE_MANUAL, '手动更新'),
]

# 操作结果
RESULT_SUCCESS = 'success'
RESULT_FAILED = 'failed'

RESULT_CHOICES = [
    (RESULT_SUCCESS, '成功'),
    (RESULT_FAILED, '失败'),
]

# 默认配置
DEFAULT_CONFIG = {
    'update_interval_days': 3,
    'update_time': '02:00',
    'advance_update_hours': 24,
    'max_retry_count': 3,
    'local_port': 8000,
}

# 时间范围
TIME_RANGE_1DAY = '1day'
TIME_RANGE_7DAYS = '7days'
TIME_RANGE_CUSTOM = 'custom'

TIME_RANGE_CHOICES = [
    (TIME_RANGE_1DAY, '近 1 天'),
    (TIME_RANGE_7DAYS, '近 7 天'),
    (TIME_RANGE_CUSTOM, '自定义'),
]

