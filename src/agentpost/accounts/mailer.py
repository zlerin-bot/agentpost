from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from agentpost.config import Settings


class EmailDeliveryError(RuntimeError):
    pass


def _send_message(settings: Settings, message: EmailMessage) -> None:
    if settings.email_delivery_mode == "test":
        return
    if not settings.smtp_host or not settings.smtp_from_address:
        raise EmailDeliveryError("SMTP delivery is not configured")
    try:
        context = ssl.create_default_context()
        if settings.smtp_ssl:
            connection = smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=10,
                context=context,
            )
        else:
            connection = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
        with connection as client:
            if settings.smtp_starttls:
                client.starttls(context=context)
            if settings.smtp_username:
                password = (
                    settings.smtp_password.get_secret_value() if settings.smtp_password else ""
                )
                client.login(settings.smtp_username, password)
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("Email could not be delivered") from exc


def deliver_verification_code(
    settings: Settings,
    *,
    email: str,
    code: str,
    purpose: str,
) -> None:
    if not settings.smtp_host or not settings.smtp_from_address:
        if settings.email_delivery_mode == "test":
            return
        raise EmailDeliveryError("SMTP delivery is not configured")
    message = EmailMessage()
    message["Subject"] = "AgentPost 邮箱验证码"
    message["From"] = settings.smtp_from_address
    message["To"] = email
    action = "注册" if purpose == "register" else "账户恢复"
    message.set_content(
        f"你正在进行 AgentPost {action}。验证码：{code}\n\n"
        "验证码将在短时间后失效。若非本人操作，请忽略本邮件。"
    )
    _send_message(settings, message)


def deliver_task_membership_notification(
    settings: Settings,
    *,
    email: str,
    inviter_name: str,
    task_title: str,
    task_id: str,
    agent_name: str,
) -> None:
    if not settings.smtp_host or not settings.smtp_from_address:
        if settings.email_delivery_mode == "test":
            return
        raise EmailDeliveryError("SMTP delivery is not configured")
    message = EmailMessage()
    message["Subject"] = f"{inviter_name} 把你加入了 AgentPost 任务：{task_title}"
    message["From"] = settings.smtp_from_address
    message["To"] = email
    task_url = f"{settings.public_base_url.rstrip('/')}/orbit?task={task_id}"
    message.set_content(
        f"{inviter_name} 已把你加入 AgentPost 任务。\n\n"
        f"任务：{task_title}\n"
        f"任务 ID：{task_id}\n"
        f"参与 Agent：{agent_name}\n\n"
        f"登录后查看任务：{task_url}\n\n"
        "邮件不包含任务正文或附件。若不希望参与，可登录后退出任务。"
    )
    _send_message(settings, message)
