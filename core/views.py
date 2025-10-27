# 文件: core/views.py
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime, timedelta
import uuid
import requests
from .models import Account, Config, TokenLog
from .utils.response import success_response, error_response
from .utils.validator import validate_rfc3339_datetime, validate_email


# ============ 前端页面视图 ============

def index(request):
    """首页"""
    return render(request, 'index.html')


def accounts_page(request):
    """账号管理页面"""
    return render(request, 'accounts.html')


def config_page(request):
    """配置管理页面"""
    return render(request, 'config.html')


def logs_page(request):
    """日志页面"""
    return render(request, 'logs.html')


# ============ 账号管理 API ============

class AccountListView(View):
    """账号列表视图 - GET 获取列表，POST 添加账号"""

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """获取账号列表"""
        try:
            # 获取查询参数
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
            search = request.GET.get('search', '').strip()
            status = request.GET.get('status', 'all')

            # 参数验证
            if page < 1:
                page = 1
            if page_size not in [10, 20, 50, 100]:
                page_size = 20

            # 构建查询条件
            queryset = Account.objects.all()

            # 邮箱搜索（模糊匹配）
            if search:
                queryset = queryset.filter(email__icontains=search)

            # 状态筛选
            if status != 'all' and status in ['normal', 'expired', 'abnormal']:
                queryset = queryset.filter(status=status)

            # 排序（按创建时间倒序）
            queryset = queryset.order_by('-created_at')

            # 分页处理
            paginator = Paginator(queryset, page_size)

            try:
                accounts_page = paginator.page(page)
            except PageNotAnInteger:
                accounts_page = paginator.page(1)
            except EmptyPage:
                accounts_page = paginator.page(paginator.num_pages)

            # 构建返回数据
            items = []
            for account in accounts_page:
                items.append({
                    'id': str(account.id),
                    'email': account.email,
                    'status': account.status,
                    'last_updated': account.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
                    'remark': account.remark or ''
                })

            data = {
                'count': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': accounts_page.number,
                'page_size': page_size,
                'items': items
            }

            return success_response(data, '获取账号列表成功')

        except ValueError as e:
            return error_response('参数格式错误', code=400)
        except Exception as e:
            return error_response(f'获取账号列表失败: {str(e)}', code=500)

    def post(self, request):
        """添加账号"""
        try:
            # 解析请求体
            data = json.loads(request.body)

            # 提取字段
            email = data.get('email', '').strip()
            client_id = data.get('client_id', '').strip()
            refresh_token = data.get('refresh_token', '').strip()
            expires_at_str = data.get('expires_at', '').strip()
            remark = data.get('remark', '').strip()

            # ============ 参数验证 ============
            errors = {}

            # 验证邮箱
            if not email:
                errors['email'] = ['邮箱地址不能为空']
            elif not validate_email(email):
                errors['email'] = ['邮箱格式不正确']
            elif Account.objects.filter(email=email).exists():
                errors['email'] = ['邮箱已存在，请勿重复添加']

            # 验证 client_id
            if not client_id:
                errors['client_id'] = ['Client ID 不能为空']
            elif len(client_id) > 255:
                errors['client_id'] = ['Client ID 长度不能超过 255 字符']

            # 验证 refresh_token
            if not refresh_token:
                errors['refresh_token'] = ['Refresh Token 不能为空']
            elif len(refresh_token) > 1000:
                errors['refresh_token'] = ['Refresh Token 长度不能超过 1000 字符']

            # 验证备注
            if remark and len(remark) > 200:
                errors['remark'] = ['备注长度不能超过 200 字符']

            # 如果有验证错误，返回错误信息
            if errors:
                return JsonResponse({
                    'code': 400,
                    'message': '参数验证失败',
                    'data': errors,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }, status=400)

            # ============ 创建账号 ============


            account = Account.objects.create(
                email=email,
                client_id=client_id,
                refresh_token=refresh_token,
                expires_at=datetime(2099, 12, 31, 23, 59, 59),
                status='normal',
                remark=remark

            )

            # 构建返回数据
            response_data = {
                'id': str(account.id),
                'email': account.email,
                'status': account.status,
                'last_updated': account.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
                'remark': account.remark
            }

            # 记录日志（可选）
            try:
                log_id = f"log_{uuid.uuid4().hex[:12]}"
                TokenLog.objects.create(
                    id=log_id,
                    email=account.email,
                    operation_type='manual_update',
                    result='success',
                    result_detail=f'账号添加成功，Token 有效期至 {expires_at_str}'
                )
            except Exception as log_error:
                # 日志记录失败不影响主流程
                print(f"日志记录失败: {log_error}")

            return success_response(response_data, '账号添加成功', status_code=200)

        except json.JSONDecodeError:
            return error_response('请求体格式错误，请使用有效的 JSON 格式', code=400)
        except Exception as e:
            return error_response(f'添加账号失败: {str(e)}', code=500)


class AccountDetailView(View):
    """账号详情视图 - PUT 编辑，DELETE 删除"""

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, pk):
        """删除账号"""
        try:
            # TODO: 实现实际逻辑
            return success_response(None, '账号删除成功')
        except Exception as e:
            return error_response(str(e), code=500)


@csrf_exempt
@require_http_methods(['GET'])
def refresh_all_tokens(request):
    """批量刷新所有账号的 Access Token"""
    try:
        # 获取所有账号
        accounts = Account.objects.all()

        if not accounts.exists():
            return error_response('没有找到任何账号', code=404)

        # 统计信息
        total_count = accounts.count()
        success_count = 0
        failed_count = 0
        results = []

        # 微软 Token API 地址
        token_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'

        # 遍历所有账号
        for account in accounts:
            email = account.email
            result_item = {
                'email': email,
                'status': '',
                'message': ''
            }

            try:
                # 准备请求数据
                token_data = {
                    'client_id': account.client_id,
                    'refresh_token': account.refresh_token,
                    'grant_type': 'refresh_token',
                }

                # 发送请求
                response = requests.post(
                    token_url,
                    data=token_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=30
                )

                # 处理响应
                if response.status_code == 200:
                    token_response = response.json()

                    access_token = token_response.get('access_token')
                    new_refresh_token = token_response.get('refresh_token')

                    # 更新数据库
                    if new_refresh_token:
                        account.refresh_token = new_refresh_token
                    account.expires_at = datetime(2099, 12, 31, 12, 59, 59)
                    account.status = 'normal'
                    account.save()

                    # 记录成功日志
                    log_id = f"{email}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    TokenLog.objects.create(
                        id=log_id,
                        email=email,
                        operation_type='auto_update',
                        result='success',
                        result_detail=f'批量刷新成功，有效期至 {account.expires_at}'
                    )

                    success_count += 1
                    result_item['status'] = 'success'
                    result_item['message'] = 'Token 刷新成功'

                else:
                    # 处理失败情况
                    error_data = response.json()
                    error_code = error_data.get('error', 'unknown_error')
                    error_description = error_data.get('error_description', '未知错误')

                    # 记录失败日志
                    log_id = f"{email}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    TokenLog.objects.create(
                        id=log_id,
                        email=email,
                        operation_type='auto_update',
                        result='failed',
                        result_detail=f'批量刷新失败: {error_code} - {error_description}'
                    )

                    # 如果是 invalid_grant 错误，更新账号状态
                    if error_code == 'invalid_grant':
                        account.status = 'expired'
                        account.save()

                    failed_count += 1
                    result_item['status'] = 'failed'
                    result_item['message'] = f'{error_code}: {error_description}'

            except requests.RequestException as e:
                # 网络请求异常
                log_id = f"{email}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                TokenLog.objects.create(
                    id=log_id,
                    email=email,
                    operation_type='auto_update',
                    result='failed',
                    result_detail=f'网络请求失败: {str(e)}'
                )

                failed_count += 1
                result_item['status'] = 'failed'
                result_item['message'] = f'网络请求失败: {str(e)}'

            except Exception as e:
                # 其他异常
                failed_count += 1
                result_item['status'] = 'failed'
                result_item['message'] = f'未知错误: {str(e)}'

            results.append(result_item)

        # 构造响应数据
        response_data = {
            'summary': {
                'total': total_count,
                'success': success_count,
                'failed': failed_count
            },
            'details': results
        }

        # 根据结果返回相应的消息
        if failed_count == 0:
            message = f'所有账号 Token 刷新成功（共 {total_count} 个）'
        elif success_count == 0:
            message = f'所有账号 Token 刷新失败（共 {total_count} 个）'
        else:
            message = f'批量刷新完成：成功 {success_count} 个，失败 {failed_count} 个'

        return success_response(response_data, message)

    except Exception as e:
        # 其他未预期的错误
        return error_response(f'服务器内部错误：{str(e)}', code=500)




@csrf_exempt
@require_http_methods(['POST'])
def refresh_account_status(request):
    """刷新账号状态"""
    try:
        data = json.loads(request.body) if request.body else {}
        ids = data.get('ids', [])
        # TODO: 实现实际逻辑

        response_data = {
            'total': 100,
            'normal': 95,
            'expired': 3,
            'abnormal': 2,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        return success_response(response_data, '状态刷新成功')
    except Exception as e:
        return error_response(str(e), code=500)


@csrf_exempt
@require_http_methods(['POST'])
def update_single_token(request, pk):
    """单个账号手动更新 Token"""
    try:
        # TODO: 实现实际逻辑
        response_data = {
            'email': 'test@outlook.com',
            'status': 'normal',
            'expires_at': '2024-06-21 15:30:00',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        return success_response(response_data, 'Token 更新成功')
    except Exception as e:
        return error_response(str(e), code=500)


# ============ Token 获取 API ============
@csrf_exempt
@require_http_methods(['POST'])
def batch_get_access_tokens(request):
    """批量获取 Access Token"""
    try:
        # 解析请求体
        data = json.loads(request.body)
        emails = data.get('emails', [])

        # 参数验证
        if not emails:
            return error_response('邮箱列表不能为空', code=400)

        if not isinstance(emails, list):
            return error_response('emails 必须是数组', code=400)

        if len(emails) > 100:  # 限制批量数量
            return error_response('单次最多处理100个邮箱', code=400)

        # 去重并清理邮箱
        emails = list(set([email.strip() for email in emails if email]))

        if not emails:
            return error_response('没有有效的邮箱地址', code=400)

        # 结果列表
        results = []
        success_count = 0
        failed_count = 0

        # 微软 Token_API 地址
        token_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'

        # 遍历处理每个邮箱
        for email in emails:
            result = {
                'email': email,
                'access_token': '',
                'message': '',
                'success': False
            }

            try:
                # 验证邮箱格式
                try:
                    validate_email(email)
                except ValidationError:
                    result['message'] = '邮箱格式不正确'
                    results.append(result)
                    failed_count += 1
                    continue

                # 查询账号是否存在
                try:
                    account = Account.objects.get(email=email)
                except Account.DoesNotExist:
                    result['message'] = '账号不存在'
                    results.append(result)
                    failed_count += 1
                    continue

                # 准备请求数据
                token_data = {
                    'client_id': account.client_id,
                    'refresh_token': account.refresh_token,
                    'grant_type': 'refresh_token',
                }

                # 发送请求
                response = requests.post(
                    token_url,
                    data=token_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=30
                )

                # 处理响应
                if response.status_code == 200:
                    token_response = response.json()

                    access_token = token_response.get('access_token')
                    expires_in = token_response.get('expires_in', 3600)
                    new_refresh_token = token_response.get('refresh_token')

                    # 更新数据库中的 refresh_token 和过期时间
                    if new_refresh_token:
                        account.refresh_token = new_refresh_token
                    account.expires_at = datetime(2099, 12, 31, 12, 59, 59)
                    account.status = 'normal'
                    account.save()

                    # 记录成功日志
                    log_id = f"{email}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    TokenLog.objects.create(
                        id=log_id,
                        email=email,
                        operation_type='manual_update',
                        result='success',
                        result_detail=f'批量获取 access token 成功，有效期至 {account.expires_at}'
                    )

                    # 构造成功响应
                    result['access_token'] = access_token
                    result['message'] = 'access token 获取成功'
                    result['success'] = True
                    success_count += 1

                else:
                    # 处理失败情况
                    error_data = response.json()
                    error_code = error_data.get('error', 'unknown_error')
                    error_description = error_data.get('error_description', '未知错误')

                    # 记录失败日志
                    log_id = f"{email}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    TokenLog.objects.create(
                        id=log_id,
                        email=email,
                        operation_type='manual_update',
                        result='failed',
                        result_detail=f'批量获取 access token 失败: {error_code} - {error_description}'
                    )

                    # 如果是 invalid_grant 错误，更新账号状态
                    if error_code == 'invalid_grant':
                        account.status = 'expired'
                        account.save()
                        result['message'] = f'token 已失效 (error: {error_code})，建议重新获取并录入 refresh token'
                    else:
                        result['message'] = f'{error_description} (error: {error_code})'

                    failed_count += 1

            except requests.RequestException as e:
                # 网络请求异常
                log_id = f"{email}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                TokenLog.objects.create(
                    id=log_id,
                    email=email,
                    operation_type='manual_update',
                    result='failed',
                    result_detail=f'批量获取 - 网络请求失败: {str(e)}'
                )
                result['message'] = f'网络请求失败：{str(e)}'
                failed_count += 1

            except Exception as e:
                # 其他未预期的错误
                result['message'] = f'处理失败：{str(e)}'
                failed_count += 1

            results.append(result)

        # 构造返回数据
        response_data = {
            'total': len(emails),
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results
        }

        # 根据成功失败情况决定返回状态
        if success_count > 0:
            message = f'批量处理完成：成功 {success_count} 个，失败 {failed_count} 个'
            return success_response(response_data, message, status_code=200)
        else:
            message = f'批量处理全部失败：共 {failed_count} 个'
            return error_response(message, code=500, data=response_data)

    except json.JSONDecodeError:
        return error_response('请求体格式错误', code=400)

    except Exception as e:
        # 其他未预期的错误
        return error_response(f'服务器内部错误：{str(e)}', code=500)


@csrf_exempt
@require_http_methods(['POST'])
def get_access_token(request):
    """获取 Access Token"""
    try:
        # 解析请求体
        data = json.loads(request.body)
        email = data.get('email', '').strip()

        # 参数验证
        if not email:
            return error_response('邮箱不能为空', code=400)


        # 验证邮箱格式
        try:
            validate_email(email)
        except ValidationError:
            return error_response('邮箱格式不正确', code=400)


        # 查询账号是否存在
        try:
            account = Account.objects.get(email=email)
        except Account.DoesNotExist:

            return  error_response('账号不存在', code=404)


        # 调用微软 API 获取 access token
        token_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'

        token_data = {
            'client_id': account.client_id,
            'refresh_token': account.refresh_token,
            'grant_type': 'refresh_token',
        }

        # 发送请求
        response = requests.post(
            token_url,
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30
        )

        # 处理响应
        if response.status_code == 200:
            token_response = response.json()
            print("Response JSON:", token_response)

            access_token = token_response.get('access_token')
            expires_in = token_response.get('expires_in', 3600)
            new_refresh_token = token_response.get('refresh_token')

            # 更新数据库中的 refresh_token 和过期时间
            if new_refresh_token:
                account.refresh_token = new_refresh_token
            account.expires_at = datetime(2099,12,31,12,59,59)
            account.status = 'normal'
            account.save()

            # 记录日志
            log_id = f"{email}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            TokenLog.objects.create(
                id=log_id,
                email=email,
                operation_type='manual_update',
                result='success',
                result_detail=f'成功获取 access token，有效期至 {account.expires_at}'
            )

            # 构造响应数据
            response_data = {
                'email': email,
                'access_token': access_token,
                'expires_in': expires_in,
                'expires_at': account.expires_at,
                'new_refresh_token': new_refresh_token if new_refresh_token else account.refresh_token,
                'last_updated': account.last_updated.strftime('%Y-%m-%d %H:%M:%S')
            }

            return success_response(response_data, 'access token 获取成功')


        else:
            # 处理失败情况
            error_data = response.json()
            error_code = error_data.get('error', 'unknown_error')
            error_description = error_data.get('error_description', '未知错误')

            # 记录失败日志
            log_id = f"{email}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            TokenLog.objects.create(
                id=log_id,
                email=email,
                operation_type='manual_update',
                result='failed',
                result_detail=f'获取 access token 失败: {error_code} - {error_description}'
            )

            # 如果是 invalid_grant 错误，更新账号状态
            if error_code == 'invalid_grant':
                account.status = 'expired'
                account.save()
                error_message = f'access token 获取失败：token 已失效 (error: {error_code})，建议重新获取并录入 refresh token'
            else:
                error_message = f'access token 获取失败：{error_description} (error: {error_code})'

            return error_response(error_message, code=500)


    except json.JSONDecodeError:
        return error_response('请求体格式错误', code=400)


    except requests.RequestException as e:
        # 网络请求异常
        log_id = f"{email}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        TokenLog.objects.create(
            id=log_id,
            email=email,
            operation_type='manual_update',
            result='failed',
            result_detail=f'网络请求失败: {str(e)}'
        )

        return error_response(f'网络请求失败：{str(e)}', code=500)


    except Exception as e:
        # 其他未预期的错误
        return error_response(f'服务器内部错误：{str(e)}', code=500)



# ============ 配置管理 API ============

class ConfigView(View):
    """配置视图 - GET 获取，PUT 更新"""

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """获取配置"""
        # TODO: 实现实际逻辑
        data = {
            'update_interval_days': 3,
            'update_time': '02:00',
            'advance_update_hours': 24,
            'max_retry_count': 3,
            'local_port': 8000,
            'created_at': '2024-01-01 00:00:00',
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        return success_response(data, '获取配置成功')

    def put(self, request):
        """更新配置"""
        try:
            data = json.loads(request.body)
            # TODO: 参数验证
            # TODO: 实现实际逻辑

            response_data = {
                'update_interval_days': data.get('update_interval_days', 3),
                'update_time': data.get('update_time', '02:00'),
                'advance_update_hours': data.get('advance_update_hours', 24),
                'max_retry_count': data.get('max_retry_count', 3),
                'local_port': data.get('local_port', 8000),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            return success_response(response_data, '配置保存成功，实时生效')
        except Exception as e:
            return error_response(str(e), code=500)


@csrf_exempt
@require_http_methods(['POST'])
def reset_config(request):
    """重置为默认配置"""
    try:
        # TODO: 实现实际逻辑
        response_data = {
            'update_interval_days': 3,
            'update_time': '02:00',
            'advance_update_hours': 24,
            'max_retry_count': 3,
            'local_port': 8000
        }

        return success_response(response_data, '配置已重置为默认值')
    except Exception as e:
        return error_response(str(e), code=500)


# ============ 手动更新 API ============

@csrf_exempt
@require_http_methods(['POST'])
def update_single(request):
    """单个账号更新"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '')
        # TODO: 参数验证
        # TODO: 实现实际逻辑

        response_data = {
            'email': email,
            'status': 'success',
            'expires_at': '2024-06-21 15:30:00',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        return success_response(response_data, 'Token 更新成功')
    except Exception as e:
        return error_response(str(e), code=500)


@csrf_exempt
@require_http_methods(['POST'])
def update_all(request):
    """全部账号更新"""
    try:
        # TODO: 实现实际逻辑
        response_data = {
            'total': 100,
            'success': 95,
            'failed': 5,
            'details': [
                {
                    'email': 'test1@outlook.com',
                    'status': 'success',
                    'expires_at': '2024-06-21 15:30:00'
                },
                {
                    'email': 'test2@outlook.com',
                    'status': 'failed',
                    'error': 'token 已失效'
                }
            ]
        }

        return success_response(response_data, '全部账号更新完成')
    except Exception as e:
        return error_response(str(e), code=500)


# ============ 日志管理 API ============

class LogListView(View):
    """日志列表视图"""

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """获取更新日志"""
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        time_range = request.GET.get('time_range', '7days')
        email = request.GET.get('email', '')
        result = request.GET.get('result', 'all')

        # TODO: 实现实际逻辑

        data = {
            'count': 150,
            'total_pages': 8,
            'current_page': page,
            'page_size': page_size,
            'items': [
                {
                    'id': 'log_550e8400',
                    'operation_time': '2024-05-21 15:30:00',
                    'email': 'test@outlook.com',
                    'operation_type': 'manual_update',
                    'result': 'success',
                    'result_detail': '新 token 有效期至 2024-06-21 15:30:00'
                },
                {
                    'id': 'log_550e8401',
                    'operation_time': '2024-05-21 14:00:00',
                    'email': 'test2@outlook.com',
                    'operation_type': 'auto_update',
                    'result': 'failed',
                    'result_detail': 'error: invalid_grant，token 已失效'
                }
            ]
        }

        return success_response(data, '获取日志成功')


@csrf_exempt
@require_http_methods(['POST'])
def export_logs(request):
    """导出日志为 CSV"""
    try:
        data = json.loads(request.body)
        # TODO: 参数验证
        # TODO: 生成 CSV 文件

        response_data = {
            'file_path': 'D:\\Logs\\outlook_token_update_20240521.csv',
            'file_name': 'outlook_token_update_20240521.csv',
            'row_count': 150
        }

        return success_response(response_data, '日志导出成功')
    except Exception as e:
        return error_response(str(e), code=500)

