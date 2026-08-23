"""Public, secret-free session response models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.api.task_models import ApiModel


class AuthSessionResponse(ApiModel):
    schema_version: Literal["1.0"] = "1.0"
    csrf_token: str
    expires_at: datetime


__all__ = ["AuthSessionResponse"]
