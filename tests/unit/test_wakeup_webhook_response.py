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
