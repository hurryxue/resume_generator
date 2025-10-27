"""
Outlook 邮件拉取脚本（IMAP 协议版本）
------------------------------------
功能：
  - 使用 IMAP 协议访问 Outlook 邮箱
  - 支持 OAuth2 认证（使用 Access Token）
  - 拉取多个邮箱中的邮件
  - 结构化解析邮件信息
  - 支持标记邮件为已读

依赖：
  pip install requests
  Python 标准库：imaplib, email
"""

import os
import time
import json
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import requests


# ==============================================================
# 1️⃣ 基础配置函数
# ==============================================================

def get_config():
    """获取全局配置"""
    config = {
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "default_folder": "INBOX",
        "max_mails": 200,      # 最大总邮件数
        "request_timeout": 30,  # 请求超时时间（秒）
        "save_path": "emails.json",
        "token_api_url": "http://localhost:8000/api/batch-access-tokens/"  # Token API 地址
    }
    return config


# ==============================================================
# 2️⃣ Token 管理函数
# ==============================================================

def get_access_token(emails):
    """
    从指定 API 批量获取 access token。

    参数：
        emails: 邮箱地址列表

    返回：
        dict: {email: access_token} 的字典，失败的邮箱 token 为 None
    """
    config = get_config()
    api_url = config["token_api_url"]

    try:
        # 调用批量获取 token 接口
        response = requests.post(
            api_url,
            json={"emails": emails},
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            data = result.get("data", {})
            results = data.get("results", [])

            # 构造返回字典
            token_dict = {}
            for item in results:
                email_addr = item.get("email")
                success = item.get("success", False)
                access_token = item.get("access_token", "")
                message = item.get("message", "")

                if success and access_token:
                    token_dict[email_addr] = access_token
                    print(f"✅ {email_addr}: Token 获取成功")
                else:
                    token_dict[email_addr] = None
                    print(f"❌ {email_addr}: {message}")

            print(f"\n📊 Token 获取统计：成功 {data.get('success_count', 0)} 个，失败 {data.get('failed_count', 0)} 个\n")
            return token_dict
        else:
            print(f"[错误] API 请求失败 ({response.status_code}): {response.text}")
            return {email_addr: None for email_addr in emails}

    except requests.RequestException as e:
        print(f"[错误] 网络请求异常：{e}")
        return {email_addr: None for email_addr in emails}
    except Exception as e:
        print(f"[错误] 获取 Token 失败：{e}")
        return {email_addr: None for email_addr in emails}


# ==============================================================
# 3️⃣ IMAP 连接函数
# ==============================================================

def connect_imap(email_addr, access_token):
    """
    使用 OAuth2 连接到 IMAP 服务器。

    参数：
        email_addr: 邮箱地址
        access_token: Access Token

    返回：
        IMAP4_SSL 连接对象，失败返回 None
    """
    config = get_config()

    try:
        # 创建 IMAP 连接
        mail = imaplib.IMAP4_SSL(config["imap_server"], config["imap_port"])

        # 构造 OAuth2 认证字符串
        auth_string = f'user={email_addr}\x01auth=Bearer {access_token}\x01\x01'

        # 使用 OAuth2 认证
        mail.authenticate('XOAUTH2', lambda x: auth_string.encode())

        print(f"✅ IMAP 连接成功：{email_addr}")
        return mail

    except imaplib.IMAP4.error as e:
        print(f"❌ IMAP 认证失败：{email_addr} - {e}")
        return None
    except Exception as e:
        print(f"❌ IMAP 连接异常：{email_addr} - {e}")
        return None


def disconnect_imap(mail):
    """安全关闭 IMAP 连接"""
    try:
        if mail:
            mail.close()
            mail.logout()
    except Exception as e:
        print(f"[警告] 关闭连接时出错：{e}")


# ==============================================================
# 4️⃣ 邮件拉取函数
# ==============================================================

def fetch_mails(email_addr, access_token, folder="INBOX", limit=100):
    """
    拉取指定文件夹的未读邮件。

    参数：
        email_addr: 邮箱地址
        access_token: Access Token
        folder: 邮件文件夹名称
        limit: 最大拉取数量

    返回：
        解析后的邮件列表
    """
    mail = connect_imap(email_addr, access_token)
    if not mail:
        return []

    all_mails = []

    try:
        # 选择文件夹
        status, messages = mail.select(folder)
        if status != 'OK':
            print(f"[错误] 无法打开文件夹：{folder}")
            return []

        # 搜索未读邮件
        status, message_ids = mail.search(None, 'UNSEEN')
        if status != 'OK':
            print(f"[错误] 搜索邮件失败")
            return []

        # 获取邮件 ID 列表
        mail_ids = message_ids[0].split()

        if not mail_ids:
            print(f"📭 没有未读邮件")
            return []

        # 倒序处理（最新的在前）
        mail_ids = list(reversed(mail_ids))

        # 限制拉取数量
        mail_ids = mail_ids[:limit]

        print(f"📥 开始拉取邮件（文件夹：{folder}，未读邮件：{len(mail_ids)} 封）...")

        # 逐个获取邮件
        for i, mail_id in enumerate(mail_ids, 1):
            try:
                # 获取邮件内容
                status, msg_data = mail.fetch(mail_id, '(RFC822)')
                if status != 'OK':
                    print(f"[警告] 无法获取邮件 {mail_id}")
                    continue

                # 解析邮件
                raw_email = msg_data[0][1]
                parsed_mail = parse_mail(raw_email, mail_id.decode())

                hasKeyValue = checkKeyValue(parsed_mail)

                if parsed_mail and hasKeyValue:
                    all_mails.append(parsed_mail)

                    # 标记为已读
                    mark_mail_as_read(mail, mail_id)

                print(f"  已拉取 {i}/{len(mail_ids)} 封邮件...")

            except Exception as e:
                print(f"[错误] 处理邮件 {mail_id} 失败：{e}")
                print(f"[错误] 处理邮件 {mail_id} 失败：{e}")
                continue

        print(f"✅ 拉取完成，共获取 {len(all_mails)} 封邮件\n")

    except Exception as e:
        print(f"[错误] 拉取邮件异常：{e}")
    finally:
        disconnect_imap(mail)

    return all_mails


def mark_mail_as_read(mail, mail_id):
    """
    将指定邮件标记为已读。

    参数：
        mail: IMAP 连接对象
        mail_id: 邮件 ID

    返回：
        是否成功
    """
    try:
        mail.store(mail_id, '+FLAGS', '\\Seen')
        return True
    except Exception as e:
        print(f"[警告] 标记邮件失败：{e}")
        return False


# ==============================================================
# 5️⃣ 邮件解析函数
# ==============================================================

def decode_mime_header(header_value):
    """解码 MIME 编码的邮件头"""
    if not header_value:
        return ""

    decoded_parts = decode_header(header_value)
    result = []

    for content, encoding in decoded_parts:
        if isinstance(content, bytes):
            try:
                if encoding:
                    result.append(content.decode(encoding))
                else:
                    result.append(content.decode('utf-8', errors='ignore'))
            except:
                result.append(content.decode('utf-8', errors='ignore'))
        else:
            result.append(str(content))

    return ''.join(result)


def checkKeyValue(mail):
    # todo Implement this function to check if the email has the keywords
    return True


def parse_mail(raw_email, mail_id):
    """
    解析单封邮件的主要字段。

    参数：
        raw_email: 原始邮件字节流
        mail_id: 邮件 ID

    返回：
        标准化字典
    """
    try:
        # 解析邮件
        msg = email.message_from_bytes(raw_email)

        # 提取主题
        subject = decode_mime_header(msg.get('Subject', '(无主题)'))

        # 提取发件人
        from_header = msg.get('From', '')
        from_addr = email.utils.parseaddr(from_header)[1] if from_header else "未知"

        # 提取收件人
        to_header = msg.get('To', '')
        to_addrs = []
        if to_header:
            to_list = email.utils.getaddresses([to_header])
            to_addrs = [addr for name, addr in to_list if addr]

        # 提取接收时间
        date_header = msg.get('Date', '')
        received_time = None
        if date_header:
            try:
                received_time = parsedate_to_datetime(date_header).isoformat()
            except:
                received_time = date_header

        # 提取邮件正文预览
        body_preview = extract_body_preview(msg)

        mail_info = {
            "id": mail_id,
            "subject": subject,
            "from": from_addr,
            "to": to_addrs,
            "received_time": received_time,
            "is_read": False,  # 拉取时标记为未读，后续会标记为已读
            "body_preview": body_preview[:200]  # 限制预览长度
        }

        return mail_info

    except Exception as e:
        print(f"[解析错误] {e}")
        return None


def extract_body_preview(msg):
    """提取邮件正文预览"""
    body = ""

    try:
        # 优先获取纯文本内容
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='ignore')
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='ignore')

        # 清理空白字符
        body = ' '.join(body.split())

    except Exception as e:
        print(f"[警告] 提取邮件正文失败：{e}")

    return body


# ==============================================================
# 6️⃣ 结果保存函数
# ==============================================================

def save_mails(mails_by_account, path="emails.json"):
    """
    保存所有账号的邮件结果到 JSON 文件。

    参数：
        mails_by_account: {email: [mails]} 的字典
        path: 保存路径
    """
    try:
        # 统计信息
        total_mails = sum(len(mails) for mails in mails_by_account.values())

        # 构造保存数据
        save_data = {
            "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_accounts": len(mails_by_account),
            "total_mails": total_mails,
            "accounts": mails_by_account
        }

        # 保存到文件
        with open(path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        print(f"💾 邮件数据已保存到：{path}")
        print(f"📊 统计：{len(mails_by_account)} 个账号，共 {total_mails} 封邮件")

        # 打印每个账号的统计
        for email_addr, mails in mails_by_account.items():
            print(f"  - {email_addr}: {len(mails)} 封")

    except Exception as e:
        print(f"[错误] 保存失败：{e}")


# ==============================================================
# 7️⃣ 主函数
# ==============================================================

def main():
    """主程序入口"""
    config = get_config()

    # 定义要拉取的邮箱列表
    emails = [
        "MichelleChen8421@outlook.com"
    ]

    print("=" * 60)
    print("🚀 Outlook 邮件批量拉取程序（IMAP 协议）")
    print("=" * 60)
    print(f"📧 待处理邮箱数量：{len(emails)}")
    print(f"📁 目标文件夹：{config['default_folder']}")
    print(f"📊 每账号最多拉取：{config['max_mails']} 封\n")

    # 1. 批量获取所有邮箱的 access token
    print("🔑 步骤 1/3：获取 Access Token")
    print("-" * 60)
    tokens = get_access_token(emails)

    # 2. 拉取每个邮箱的邮件
    print("\n📬 步骤 2/3：拉取邮件内容")
    print("-" * 60)
    mails_by_account = {}

    for email_addr in emails:
        token = tokens.get(email_addr)

        if token:
            print(f"\n📮 正在处理账号：{email_addr}")
            mails = fetch_mails(
                email_addr,
                token,
                folder=config["default_folder"],
                limit=config["max_mails"]
            )
            mails_by_account[email_addr] = mails
        else:
            print(f"\n⏭️  跳过账号：{email_addr}（Token 获取失败）")
            mails_by_account[email_addr] = []

    # 3. 保存结果
    print("\n💾 步骤 3/3：保存结果")
    print("-" * 60)
    save_mails(mails_by_account, config["save_path"])

    print("\n" + "=" * 60)
    print("✅ 所有任务完成！")
    print("=" * 60)


# ==============================================================
# 程序入口
# ==============================================================

if __name__ == "__main__":
    main()