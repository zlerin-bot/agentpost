from __future__ import annotations

from email.message import EmailMessage

import pytest

from agentpost.accounts import mailer
from agentpost.config import Settings


class FakeSmtp:
    def __init__(self) -> None:
        self.started_tls = False
        self.login_args: tuple[str, str] | None = None
        self.sent: EmailMessage | None = None

    def __enter__(self):
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def starttls(self, *, context) -> None:
        assert context is not None
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.login_args = (username, password)

    def send_message(self, message: EmailMessage) -> None:
        self.sent = message


def test_starttls_smtp_uses_encrypted_upgrade_and_authentication(monkeypatch) -> None:
    client = FakeSmtp()

    def connect(host: str, port: int, *, timeout: int):
        assert (host, port, timeout) == ("smtp.example.com", 80, 10)
        return client

    monkeypatch.setattr(mailer.smtplib, "SMTP", connect)
    settings = Settings(
        email_delivery_mode="smtp",
        smtp_host="smtp.example.com",
        smtp_port=80,
        smtp_username="mailer",
        smtp_password="secret-password",
        smtp_from_address="no-reply@agentpost.me",
        smtp_starttls=True,
    )

    mailer.deliver_verification_code(
        settings,
        email="tester@example.com",
        code="12345678",
        purpose="register",
    )

    assert client.started_tls is True
    assert client.login_args == ("mailer", "secret-password")
    assert client.sent is not None
    assert client.sent["To"] == "tester@example.com"
    assert "12345678" in client.sent.get_content()


def test_implicit_tls_smtp_does_not_issue_starttls(monkeypatch) -> None:
    client = FakeSmtp()

    def connect(host: str, port: int, *, timeout: int, context):
        assert (host, port, timeout) == ("smtpdm.aliyun.com", 465, 10)
        assert context is not None
        return client

    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", connect)
    settings = Settings(
        email_delivery_mode="smtp",
        smtp_host="smtpdm.aliyun.com",
        smtp_port=465,
        smtp_username="mailer@agentpost.me",
        smtp_password="secret-password",
        smtp_from_address="mailer@agentpost.me",
        smtp_starttls=False,
        smtp_ssl=True,
    )

    mailer.deliver_task_membership_notification(
        settings,
        email="colleague@example.com",
        inviter_name="负责人",
        task_title="Pilot",
        task_id="00000000-0000-0000-0000-000000000001",
        agent_name="codex",
    )

    assert client.started_tls is False
    assert client.login_args == ("mailer@agentpost.me", "secret-password")
    assert client.sent is not None
    assert client.sent["To"] == "colleague@example.com"


def test_smtp_errors_are_sanitized(monkeypatch) -> None:
    def connect(*_args, **_kwargs):
        raise OSError("provider detail must not escape")

    monkeypatch.setattr(mailer.smtplib, "SMTP", connect)
    settings = Settings(
        email_delivery_mode="smtp",
        smtp_host="smtp.example.com",
        smtp_from_address="no-reply@agentpost.me",
    )

    with pytest.raises(mailer.EmailDeliveryError, match="Email could not be delivered") as exc:
        mailer.deliver_verification_code(
            settings,
            email="tester@example.com",
            code="12345678",
            purpose="recover",
        )
    assert "provider detail" not in str(exc.value)


def test_task_membership_email_contains_identifier_but_not_task_body(monkeypatch) -> None:
    client = FakeSmtp()

    def connect(host: str, port: int, *, timeout: int):
        assert (host, port, timeout) == ("smtp.example.com", 587, 10)
        return client

    monkeypatch.setattr(mailer.smtplib, "SMTP", connect)
    settings = Settings(
        email_delivery_mode="smtp",
        smtp_host="smtp.example.com",
        smtp_from_address="no-reply@agentpost.me",
        public_base_url="https://agentpost.me",
    )

    mailer.deliver_task_membership_notification(
        settings,
        email="member@example.com",
        inviter_name="Mars",
        task_title="联合研究",
        task_id="00000000-0000-0000-0000-000000000123",
        agent_name="codex",
    )

    assert client.sent is not None
    content = client.sent.get_content()
    assert client.sent["To"] == "member@example.com"
    assert "00000000-0000-0000-0000-000000000123" in content
    assert "https://agentpost.me/orbit?task=00000000-0000-0000-0000-000000000123" in content
    assert "邮件不包含任务正文或附件" in content
