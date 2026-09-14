import json

from app.evaluation.golden_stream_bridge import SAFE_PROVIDER_FAILURE_CODES
from app.providers.errors import ProviderResponseError


def test_failure_diagnostics_allow_only_bounded_provider_codes():
    assert "stream_child_failed" in SAFE_PROVIDER_FAILURE_CODES
    assert "incomplete_chat_response" not in SAFE_PROVIDER_FAILURE_CODES
    error = ProviderResponseError(provider="zhipu", code="stream_child_failed")
    assert error.code in SAFE_PROVIDER_FAILURE_CODES


def test_failure_diagnostics_never_need_raw_error_text():
    payload = {"category": "worker_failed", "assembly_code": None, "provider_code": "stream_child_failed"}
    assert set(payload) == {"category", "assembly_code", "provider_code"}
    assert "secret" not in json.dumps(payload)
