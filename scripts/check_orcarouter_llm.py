"""One bounded real OrcaRouter gateway call through the provider adapter."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.providers.config import (
    load_orcarouter_settings,
    create_orcarouter_provider,
)
from app.providers.models import ChatMessage, ChatRequest, MessageRole


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    settings = load_orcarouter_settings(os.environ)
    provider = create_orcarouter_provider(settings)
    request = ChatRequest(
        messages=(
            ChatMessage(MessageRole.USER, "Reply with exactly: RIFTCOACH_ORCAROUTER_OK"),
        ),
        temperature=0.0,
        max_tokens=512,
    )
    response = provider.chat(request)
    print(f"provider={response.provider}")
    print(f"requested_model={settings.model}")
    print(f"resolved_model={response.model}")
    print(f"finish_reason={response.finish_reason}")
    print(f"content={response.content!r}")
    if not response.content or "RIFTCOACH_ORCAROUTER_OK" not in response.content:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
