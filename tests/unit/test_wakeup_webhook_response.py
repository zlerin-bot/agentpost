from __future__ import annotations

import httpx
import pytest

from agentpost.wakeup import service
from agentpost.wakeup.service import WakeDeliveryError


def _send(monkeypatch: pytest.MonkeyPatch, response: httpx.Response) -> None:
    monkeypatch.setattr(service, "_assert_public_dns", lambda _hostname: None)
    monkeypatch.setattr(service.httpx, "post", lambda *_args, **_kwargs: response)
    service.send_webhook(
        "https://aily.example.test/hook",
        "secret",
        {"action": "verify_agentpost_wake_channel"},
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"status_code": "0", "data": {"code": "0", "data": "run-123"}},
        {"code": 0, "msg": "success"},
    ],
)
def test_send_webhook_requires_feishu_business_success(
    monkeypatch: pytest.MonkeyPatch, payload: dict[str, object]
) -> None:
    _send(monkeypatch, httpx.Response(200, json=payload))


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (httpx.Response(200, text="accepted"), "WAKE_INVALID_RESPONSE"),
        (
            httpx.Response(200, json={"status_code": "1", "data": {"message": "failed"}}),
            "WAKE_BUSINESS_REJECTED",
        ),
        (httpx.Response(200, json={"ok": True}), "WAKE_BUSINESS_REJECTED"),
    ],
)
def test_send_webhook_rejects_false_positive_2xx(
    monkeypatch: pytest.MonkeyPatch, response: httpx.Response, expected: str
) -> None:
    with pytest.raises(WakeDeliveryError, match=expected):
        _send(monkeypatch, response)


@pytest.mark.parametrize("code", [{}, [], True, "failed", 1])
def test_malformed_business_codes_never_raise_500(monkeypatch, code):
    with pytest.raises(WakeDeliveryError, match="WAKE_BUSINESS_REJECTED"):
        _send(monkeypatch, httpx.Response(200, json={"code": code}))


@pytest.mark.parametrize(
    "outcome",
    [
        {"dispatched": True},
        {"dispatched": False, "skipReason": "already_processed"},
    ],
)
def test_webhook_acceptance_and_dedup(monkeypatch, outcome):
    _send(monkeypatch, httpx.Response(200, json=outcome))


@pytest.mark.parametrize(
    "outcome",
    [
        {"dispatched": False, "errorCode": "WEBHOOK_HEADER_MISSING"},
        {"dispatched": "true"},
        {"dispatched": True, "errorCode": "failed"},
    ],
)
def test_webhook_business_failure_is_not_delivery(monkeypatch, outcome):
    with pytest.raises(WakeDeliveryError, match="WAKE_BUSINESS_REJECTED"):
        _send(monkeypatch, httpx.Response(200, json=outcome))


def test_hmac_signs_exact_sent_utf8_body_and_preserves_event_id(monkeypatch):
    import hashlib
    import hmac
    import json

    requests = []
    monkeypatch.setattr(service, "_assert_public_dns", lambda _host: None)

    def post(url, **kwargs):
        requests.append((url, kwargs))
        return httpx.Response(200, json={"dispatched": True})

    monkeypatch.setattr(service.httpx, "post", post)
    payload = {
        "_auth_scheme": "hmac_sha256",
        "event_id": "evt-fixed",
        "action": "verify_feishu_notification_channel",
        "data": "中文",
    }
    for _ in range(2):
        service.send_webhook("https://aily.example.test/hook?route=1", "test-secret", payload)
    for _url, request in requests:
        headers = request["headers"]
        body = request["content"]
        parsed = json.loads(body)
        assert parsed["event_id"] == headers["X-Webhook-Id"] == "evt-fixed"
        assert headers["X-Webhook-Event-Type"] == parsed["event_type"] == "agentpost.test"
        signing = "\n".join(
            [
                headers["X-Webhook-Timestamp"],
                headers["X-Webhook-Nonce"],
                "POST",
                "/hook",
                hashlib.sha256(body).hexdigest(),
            ]
        )
        expected = hmac.new(b"test-secret", signing.encode(), hashlib.sha256).hexdigest()
        assert headers["X-Webhook-Signature"] == f"v1,sha256={expected}"
        assert "Authorization" not in headers
        assert b"_auth_scheme" not in body
    assert (
        requests[0][1]["headers"]["X-Webhook-Nonce"] != requests[1][1]["headers"]["X-Webhook-Nonce"]
    )
