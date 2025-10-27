"""
邮件汇总表格生成与发送模块
------------------------------------
功能：
  - 解析邮件数据，生成详细的邮件列表表格
  - 支持统计汇总信息
  - 生成 HTML 格式的邮件列表
  - 通过 SMTP 发送汇总邮件
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from collections import Counter


# ==============================================================
# 1️⃣ 邮件列表统计函数
# ==============================================================

def summarize_mails(mails_by_account):
    """
    统计邮件信息并生成汇总数据。

    参数：
        mails_by_account: {email: [mails]} 的字典

    返回：
        dict: 包含邮件列表和统计信息的字典
    """
    summary = {
        "total_mails": 0,
        "total_accounts": len(mails_by_account),
        "mail_list": [],  # 所有邮件的扁平列表
        "by_account": {},  # 按账号分组的邮件
        "stats": {
            "by_sender": Counter(),
            "by_account": {},
            "total_unread": 0
        }
    }

    # 遍历所有账号
    for account, mails in mails_by_account.items():
        account_info = {
            "count": len(mails),
            "mails": mails
        }
        summary["by_account"][account] = account_info
        summary["stats"]["by_account"][account] = len(mails)

        # 添加到总列表
        for mail in mails:
            # 添加账号信息到每封邮件
            mail_with_account = mail.copy()
            mail_with_account["account"] = account
            summary["mail_list"].append(mail_with_account)

            # 统计发件人
            sender = mail.get("from", "未知")
            summary["stats"]["by_sender"][sender] += 1

            # 统计未读
            if not mail.get("is_read", True):
                summary["stats"]["total_unread"] += 1

    summary["total_mails"] = len(summary["mail_list"])

    # 按时间排序（最新的在前）
    summary["mail_list"].sort(
        key=lambda x: x.get("received_time", ""),
        reverse=True
    )

    return summary


# ==============================================================
# 2️⃣ 生成 HTML 邮件列表表格
# ==============================================================

def generate_mail_table_html(summary, title="邮件汇总列表"):
    """
    生成包含邮件列表表格的 HTML。

    参数：
        summary: 邮件汇总数据
        title: 报告标题

    返回：
        str: HTML 内容
    """
    mail_list = summary.get("mail_list", [])
    stats = summary.get("stats", {})

    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f8f9fa;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 25px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .header h1 {{
                margin: 0 0 10px 0;
                font-size: 28px;
            }}
            .header .meta {{
                opacity: 0.9;
                font-size: 14px;
            }}
            .stats-bar {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }}
            .stat-item {{
                text-align: center;
                padding: 15px;
                border-radius: 6px;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            }}
            .stat-label {{
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
                margin-bottom: 5px;
            }}
            .stat-value {{
                font-size: 24px;
                font-weight: bold;
                color: #667eea;
            }}
            .table-container {{
                background: white;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                overflow-x: auto;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 14px;
            }}
            thead {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }}
            th {{
                padding: 12px 10px;
                text-align: left;
                font-weight: 600;
                white-space: nowrap;
            }}
            td {{
                padding: 12px 10px;
                border-bottom: 1px solid #e9ecef;
                vertical-align: top;
            }}
            tbody tr:hover {{
                background-color: #f8f9fa;
            }}
            tbody tr:last-child td {{
                border-bottom: none;
            }}
            .account-badge {{
                display: inline-block;
                padding: 4px 10px;
                border-radius: 12px;
                background-color: #e3f2fd;
                color: #1976d2;
                font-size: 11px;
                font-weight: 500;
            }}
            .subject-cell {{
                max-width: 300px;
                font-weight: 500;
                color: #2c3e50;
            }}
            .sender-cell {{
                color: #555;
                font-size: 13px;
            }}
            .time-cell {{
                color: #999;
                font-size: 12px;
                white-space: nowrap;
            }}
            .preview-cell {{
                max-width: 350px;
                color: #777;
                font-size: 13px;
                line-height: 1.4;
                overflow: hidden;
                text-overflow: ellipsis;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
            }}
            .index-cell {{
                color: #999;
                font-weight: 500;
                text-align: center;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding: 20px;
                color: #999;
                font-size: 12px;
            }}
            @media (max-width: 768px) {{
                .stats-bar {{
                    grid-template-columns: 1fr 1fr;
                }}
                table {{
                    font-size: 12px;
                }}
                th, td {{
                    padding: 8px 5px;
                }}
                .subject-cell {{
                    max-width: 200px;
                }}
                .preview-cell {{
                    max-width: 250px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📬 {title}</h1>
            <div class="meta">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>

        <div class="stats-bar">
            <div class="stat-item">
                <div class="stat-label">📧 总邮件数</div>
                <div class="stat-value">{summary.get('total_mails', 0)}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">👥 邮箱账号</div>
                <div class="stat-value">{summary.get('total_accounts', 0)}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">📮 独立发件人</div>
                <div class="stat-value">{len(stats.get('by_sender', {}))}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">🔔 未读邮件</div>
                <div class="stat-value">{stats.get('total_unread', 0)}</div>
            </div>
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th style="width: 40px;">#</th>
                        <th style="width: 150px;">账号</th>
                        <th style="width: 250px;">主题</th>
                        <th style="width: 200px;">发件人</th>
                        <th style="width: 140px;">接收时间</th>
                        <th>正文预览</th>
                    </tr>
                </thead>
                <tbody>
    """

    # 生成邮件列表行
    for idx, mail in enumerate(mail_list, 1):
        # 处理时间显示
        received_time = mail.get("received_time", "")
        try:
            if received_time:
                dt = datetime.fromisoformat(received_time.replace('Z', '+00:00'))
                time_display = dt.strftime('%m-%d %H:%M')
            else:
                time_display = "未知"
        except:
            time_display = received_time[:16] if received_time else "未知"

        # 处理主题
        subject = mail.get("subject", "(无主题)")
        if len(subject) > 50:
            subject = subject[:50] + "..."

        # 处理发件人
        sender = mail.get("from", "未知")
        if len(sender) > 35:
            sender = sender[:35] + "..."

        # 处理正文预览
        body_preview = mail.get("body_preview", "")
        if len(body_preview) > 100:
            body_preview = body_preview[:100] + "..."

        # 账号显示
        account = mail.get("account", "未知")
        account_display = account.split('@')[0] if '@' in account else account

        html += f"""
                    <tr>
                        <td class="index-cell">{idx}</td>
                        <td><span class="account-badge">{account_display}</span></td>
                        <td class="subject-cell" title="{mail.get('subject', '(无主题)')}">{subject}</td>
                        <td class="sender-cell" title="{mail.get('from', '未知')}">{sender}</td>
                        <td class="time-cell">{time_display}</td>
                        <td class="preview-cell">{body_preview}</td>
                    </tr>
        """

    html += """
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>📊 本汇总由邮件拉取系统自动生成</p>
        </div>
    </body>
    </html>
    """

    return html


# ==============================================================
# 3️⃣ 生成纯文本邮件列表
# ==============================================================

def generate_mail_table_text(summary):
    """
    生成纯文本格式的邮件列表。

    参数：
        summary: 邮件汇总数据

    返回：
        str: 纯文本内容
    """
    mail_list = summary.get("mail_list", [])
    stats = summary.get("stats", {})

    text = f"""
邮件汇总列表
{'=' * 80}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

【统计信息】
- 总邮件数: {summary.get('total_mails', 0)} 封
- 邮箱账号: {summary.get('total_accounts', 0)} 个
- 独立发件人: {len(stats.get('by_sender', {}))} 人
- 未读邮件: {stats.get('total_unread', 0)} 封

【各账号统计】
"""

    for account, count in stats.get('by_account', {}).items():
        text += f"  {account}: {count} 封\n"

    text += f"\n{'=' * 80}\n【邮件列表】\n{'=' * 80}\n\n"

    # 生成邮件列表
    for idx, mail in enumerate(mail_list, 1):
        # 处理时间
        received_time = mail.get("received_time", "")
        try:
            if received_time:
                dt = datetime.fromisoformat(received_time.replace('Z', '+00:00'))
                time_display = dt.strftime('%Y-%m-%d %H:%M')
            else:
                time_display = "未知"
        except:
            time_display = received_time[:19] if received_time else "未知"

        text += f"""[{idx}] {mail.get('subject', '(无主题)')}
    账号: {mail.get('account', '未知')}
    发件人: {mail.get('from', '未知')}
    时间: {time_display}
    预览: {mail.get('body_preview', '')[:100]}{'...' if len(mail.get('body_preview', '')) > 100 else ''}

"""

    text += f"{'=' * 80}\n共 {len(mail_list)} 封邮件\n"

    return text


# ==============================================================
# 4️⃣ 发送邮件汇总
# ==============================================================

def send_mail_summary(from_email, to_email, password, mails_by_account, subject=None):
    """
    发送邮件汇总列表。

    参数：
        from_email: 发件人邮箱
        to_email: 收件人邮箱（字符串或列表）
        access_token: OAuth2 Access Token
        mails_by_account: {email: [mails]} 的字典
        subject: 邮件主题（可选）

    返回：
        bool: 是否发送成功
    """
    smtp_server = "smtp.office365.com"
    smtp_port = 587

    try:
        # 统计汇总
        print("📊 正在生成邮件汇总...")
        summary = summarize_mails(mails_by_account)

        # 创建邮件对象
        msg = MIMEMultipart('alternative')
        msg['From'] = from_email

        # 处理收件人
        if isinstance(to_email, list):
            msg['To'] = ', '.join(to_email)
            recipients = to_email
        else:
            msg['To'] = to_email
            recipients = [to_email]

        # 设置主题
        if subject is None:
            today = datetime.now().strftime('%Y-%m-%d')
            subject = f"📬 邮件汇总列表 - {today} ({summary['total_mails']}封)"
        msg['Subject'] = subject

        # 生成纯文本版本
        text_content = generate_mail_table_text(summary)
        part1 = MIMEText(text_content, 'plain', 'utf-8')

        # 生成 HTML 版本
        html_content = generate_mail_table_html(summary)
        part2 = MIMEText(html_content, 'html', 'utf-8')

        # 添加邮件内容
        msg.attach(part1)
        msg.attach(part2)

        # 连接 SMTP 服务器
        print(f"📤 正在连接 SMTP 服务器...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.starttls()
        server.ehlo()

        #  认证
        server.login(from_email, password)


        # 发送邮件
        print(f"📧 正在发送邮件汇总到: {msg['To']}")
        server.send_message(msg)
        server.quit()

        print(f"✅ 邮件汇总发送成功！")
        print(f"   总计: {summary['total_mails']} 封邮件")
        return True

    except Exception as e:
        print(f"❌ 发送邮件汇总失败：{e}")
        return False


# ==============================================================
# 5️⃣ 保存 HTML 汇总到本地
# ==============================================================

def save_mail_summary_html(mails_by_account, output_path=None):
    """
    保存邮件汇总 HTML 到本地文件。

    参数：
        mails_by_account: {email: [mails]} 的字典
        output_path: 输出文件路径（可选）

    返回：
        str: 保存的文件路径
    """
    try:
        # 生成汇总
        summary = summarize_mails(mails_by_account)

        # 生成 HTML
        html_content = generate_mail_table_html(summary)

        # 确定保存路径
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"mail_summary_{timestamp}.html"

        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"💾 邮件汇总已保存到: {output_path}")
        return output_path

    except Exception as e:
        print(f"❌ 保存邮件汇总失败：{e}")
        return None


# ==============================================================
# 6️⃣ 完整流程：拉取、汇总、发送
# ==============================================================

def main_with_summary():
    """
    主程序：拉取邮件 -> 生成汇总 -> 发送汇总邮件
    """

    # 配置
    emails = ["MichelleChen8421@outlook.com"]
    summary_recipients = ["admin@example.com"]  # 汇总接收人


    tokens = ""


    mails_by_account = {}

    # 保存 HTML 汇总
    html_path = save_mail_summary_html(mails_by_account)

    # 步骤4: 发送邮件汇总
    print("\n📧 步骤 4/4：发送邮件汇总")
    print("-" * 60)

    # 使用第一个有效账号发送

    sender_email = ""
    sender_pwd = ""

    if not sender_pwd or not sender_email :
        print("please enter the sender email address and passward")


    if sender_email and sender_pwd:
        # 检查是否有邮件需要发送
        total_mails = sum(len(mails) for mails in mails_by_account.values())
        if total_mails > 0:
            send_mail_summary(
                sender_email,
                summary_recipients,
                sender_pwd,
                mails_by_account
            )
        else:
            print("ℹ️  没有邮件需要发送汇总")


    print("\n" + "=" * 60)
    print("✅ 所有任务完成！")
    print("=" * 60)


# ==============================================================
# 7️⃣ 独立使用示例
# ==============================================================

def example_usage():
    """
    示例：为已有的邮件数据生成并发送汇总
    """
    # 假设已经有了拉取的邮件数据
    mails_by_account = {
        "test@outlook.com": [
            {
                "id": "1",
                "subject": "重要通知：系统更新",
                "from": "admin@company.com",
                "to": ["test@outlook.com"],
                "received_time": "2025-10-20T10:30:00",
                "is_read": False,
                "body_preview": "系统将在今晚22:00进行例行维护更新，预计耗时2小时..."
            },
            {
                "id": "2",
                "subject": "会议提醒",
                "from": "calendar@company.com",
                "to": ["test@outlook.com"],
                "received_time": "2025-10-20T09:15:00",
                "is_read": False,
                "body_preview": "提醒您今天下午3点有团队周会..."
            }
        ]
    }

    # 方式1: 生成并保存 HTML 文件
    save_mail_summary_html(mails_by_account, "my_summary.html")

    # 方式2: 发送汇总邮件（需要 token）
    # send_mail_summary(
    #     "test@outlook.com",
    #     "admin@example.com",
    #     access_token,
    #     mails_by_account
    # )

    # 方式3: 只生成汇总数据
    summary = summarize_mails(mails_by_account)
    print(f"总邮件数: {summary['total_mails']}")
    print(f"独立发件人: {len(summary['stats']['by_sender'])}")


if __name__ == "__main__":
    # 运行完整流程
    main_with_summary()

    # 或使用示例
    # example_usage()