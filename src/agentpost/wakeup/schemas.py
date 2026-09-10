from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class WakeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FeishuAilyWakeChannelCreate(WakeModel):
    webhook_url: SecretStr = Field(min_length=12, max_length=4000)
    bearer_token: SecretStr = Field(min_length=8, max_length=2000)

    @field_validator("webhook_url")
    @classmethod
    def clean_url(cls, value: SecretStr) -> SecretStr:
        return SecretStr(value.get_secret_value().strip())


class WakeChannelStatus(WakeModel):
    channel_type: Literal["feishu_aily_webhook", "feishu_notification_webhook"]
    status: Literal["configured", "active", "error", "disabled"]
    endpoint_host: str
    last_tested_at: datetime | None
    last_success_at: datetime | None
    last_error_code: str | None
    pending_deliveries: int = 0


class WakeChannelTestResult(WakeModel):
    status: Literal["active", "error"]
    delivered: bool
    error_code: str | None = None
