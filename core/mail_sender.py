"""
邮件发送模块
支持多服务器（第三方 + 自建），支持同时发送/主备切换
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional
from datetime import datetime


class MailSender:
    """多服务器邮件发送器"""

    def __init__(self, config_manager):
        """
        Args:
            config_manager: ConfigManager 实例
        """
        self._config = config_manager

    def send_notification(
        self,
        subject: str,
        body: str,
        body_type: str = "html",
        attachment: str = None,
    ) -> dict:
        """
        发送通知邮件

        Args:
            subject: 邮件主题
            body: 邮件正文
            body_type: 'html' 或 'plain'
            attachment: 附件路径

        Returns:
            {
                'success': [str, ...],   # 成功的服务器名
                'failed': [(str, str)],  # (服务器名, 错误信息)
            }
        """
        import logging
        logger = logging.getLogger("FolderArchiveTool")
        result = {"success": [], "failed": []}

        if not self._config.get("mail.enabled", False):
            logger.info("[邮件] 邮件通知已禁用，跳过发送")
            return result

        servers = self._config.get("mail.servers", [])
        recipients = self._config.get("mail.recipients", [])
        send_mode = self._config.get("mail.send_mode", "all")

        if not servers or not recipients:
            logger.warning("[邮件] 服务器或收件人为空，跳过发送")
            return result

        logger.info(f"[邮件] 准备发送邮件，收件人: {recipients}，模式: {send_mode}")

        # 构建邮件消息
        msg = self._build_message(subject, body, body_type, attachment, recipients)

        if send_mode == "all":
            # 所有启用的服务器都发送
            for server in servers:
                if server.get("enabled", True):
                    ok = self._send_via_server(server, msg, recipients)
                    if ok:
                        result["success"].append(server.get("name", "unknown"))
                    else:
                        result["failed"].append(
                            (server.get("name", "unknown"), "发送失败，请查看日志")
                        )
        else:
            # 主备模式：主服务器失败则切换备用
            primary = [s for s in servers if s.get("is_primary", False) and s.get("enabled", True)]
            backup = [s for s in servers if not s.get("is_primary", False) and s.get("enabled", True)]

            sent = False
            for server in primary + backup:
                ok = self._send_via_server(server, msg, recipients)
                if ok:
                    result["success"].append(server.get("name", "unknown"))
                    sent = True
                    break
                else:
                    result["failed"].append(
                        (server.get("name", "unknown"), "发送失败，请查看日志")
                    )

        return result

    def test_connection(self, server_config: dict) -> dict:
        """测试邮件服务器连接"""
        result = {"success": False, "error": ""}
        try:
            context = ssl.create_default_context() if server_config.get("use_ssl") else None

            if server_config.get("use_ssl"):
                server = smtplib.SMTP_SSL(
                    server_config["smtp_host"],
                    server_config["smtp_port"],
                    context=context,
                    timeout=10,
                )
            else:
                server = smtplib.SMTP(
                    server_config["smtp_host"],
                    server_config["smtp_port"],
                    timeout=10,
                )
                if server_config.get("use_tls"):
                    server.starttls(context=context)

            server.login(server_config["username"], server_config.get("password", ""))
            server.quit()
            result["success"] = True
        except Exception as e:
            result["error"] = str(e)
        return result

    def build_archive_report(
        self,
        archive_result: dict,
        clean_result: dict,
        validator_result: dict,
    ) -> str:
        """构建归档报告 HTML 邮件正文"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "成功" if archive_result.get("success") else "失败"
        status_color = "#4CAF50" if archive_result.get("success") else "#F44336"

        html = f"""
        <html>
        <body style="font-family: 'Microsoft YaHei', Arial, sans-serif; color: #333;">
            <h2 style="color: #1976D2;">📦 归档任务报告</h2>
            <p><strong>执行时间：</strong>{now}</p>
            <p><strong>执行状态：</strong><span style="color: {status_color}; font-size: 18px;">{status}</span></p>

            <h3 style="color: #424242;">📊 压缩信息</h3>
            <table style="border-collapse: collapse; width: 100%;">
                <tr style="background: #f5f5f5;">
                    <td style="padding: 8px; border: 1px solid #ddd;">压缩包</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{archive_result.get('archive_path', '-')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">文件数量</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{archive_result.get('file_count', 0)}</td>
                </tr>
                <tr style="background: #f5f5f5;">
                    <td style="padding: 8px; border: 1px solid #ddd;">原始大小</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{archive_result.get('total_size', 0) / 1024 / 1024:.1f} MB</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">压缩后大小</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{archive_result.get('archive_size', 0) / 1024 / 1024:.1f} MB</td>
                </tr>
                <tr style="background: #f5f5f5;">
                    <td style="padding: 8px; border: 1px solid #ddd;">耗时</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{archive_result.get('duration_seconds', 0)} 秒</td>
                </tr>
            </table>

            <h3 style="color: #424242;">✅ 校验结果</h3>
            <p>校验状态：<strong>{'通过' if validator_result.get('valid') else '未通过'}</strong></p>
            <p>CRC 匹配数：{validator_result.get('details', {}).get('crc_match_count', 0)}</p>

            <h3 style="color: #424242;">🗑 清理结果</h3>
            <p>已删除：{len(clean_result.get('deleted', []))} 个文件</p>
            <p>删除失败：{len(clean_result.get('failed', []))} 个文件</p>
            <p>跳过：{len(clean_result.get('skipped', []))} 个文件</p>

            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">此邮件由 FolderArchiveTool 自动发送</p>
        </body>
        </html>
        """
        return html

    # ── 内部方法 ──────────────────────────────────────────

    def _build_message(
        self,
        subject: str,
        body: str,
        body_type: str,
        attachment: str,
        recipients: list,
    ) -> MIMEMultipart:
        """构建邮件消息"""
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["To"] = ", ".join(recipients)

        # 正文
        msg.attach(MIMEText(body, body_type, "utf-8"))

        # 附件
        if attachment:
            try:
                with open(attachment, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={attachment.split('/')[-1]}",
                )
                msg.attach(part)
            except Exception:
                pass

        return msg

    def _send_via_server(
        self,
        server_config: dict,
        msg: MIMEMultipart,
        recipients: list,
    ) -> bool:
        """通过指定服务器发送邮件"""
        import logging
        logger = logging.getLogger("FolderArchiveTool")
        server_name = server_config.get("name", "unknown")

        try:
            # 设置发件人，优先使用自定义发件人名称
            from_addr = server_config.get("from_addr", server_config["username"])
            sender_name = server_config.get("sender_name", "")
            if sender_name:
                from email.header import Header
                msg["From"] = f"{Header(sender_name, 'utf-8').encode()} <{from_addr}>"
            else:
                msg["From"] = from_addr
            logger.info(f"[邮件] 正在通过 {server_name} ({server_config['smtp_host']}:{server_config['smtp_port']}) 发送，发件人: {msg['From']}")

            context = None
            if server_config.get("use_ssl"):
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(
                    server_config["smtp_host"],
                    server_config["smtp_port"],
                    context=context,
                    timeout=15,
                )
            else:
                server = smtplib.SMTP(
                    server_config["smtp_host"],
                    server_config["smtp_port"],
                    timeout=15,
                )
                if server_config.get("use_tls"):
                    if context is None:
                        context = ssl.create_default_context()
                    server.starttls(context=context)

            logger.info(f"[邮件] {server_name} 连接成功，正在登录...")
            server.login(server_config["username"], server_config.get("password", ""))
            logger.info(f"[邮件] {server_name} 登录成功，正在发送...")
            server.sendmail(msg["From"], recipients, msg.as_string())
            server.quit()
            logger.info(f"[邮件] {server_name} 发送成功!")
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"[邮件] {server_name} 认证失败: 用户名或密码错误 (SMTP: {e.smtp_code})")
            return False
        except smtplib.SMTPConnectError as e:
            logger.error(f"[邮件] {server_name} 连接失败: 无法连接到服务器 (SMTP: {e.smtp_code})")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"[邮件] {server_name} 收件人被拒绝: {e.recipients}")
            return False
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"[邮件] {server_name} 服务器断开连接")
            return False
        except TimeoutError:
            logger.error(f"[邮件] {server_name} 连接超时 (15秒)")
            return False
        except ConnectionRefusedError:
            logger.error(f"[邮件] {server_name} 连接被拒绝: 请检查地址和端口")
            return False
        except ssl.SSLError as e:
            logger.error(f"[邮件] {server_name} SSL 错误: {e}")
            return False
        except Exception as e:
            logger.error(f"[邮件] {server_name} 发送失败: {type(e).__name__}: {e}")
            return False
