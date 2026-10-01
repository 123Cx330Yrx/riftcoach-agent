"""Regression coverage for real-call accounting and private response evidence."""
import json
from types import SimpleNamespace

import pytest

from scripts.run_golden_inference_development import Counted


def test_reservation_survives_failure_and_prevents_an_extra_call(tmp_path):
    state = dict(calls=0, input_tokens=0, output_tokens=0)
    attempts = []

    def fail(request):
        reservation = json.loads((tmp_path / "call-001.json").read_text())
        assert reservation["state"] == "reserved_before_io"
        attempts.append(request)
        raise RuntimeError("synthetic transport failure")

    provider = Counted(SimpleNamespace(chat=fail), state=state,
                       call_limit=1, directory=tmp_path)
    with pytest.raises(RuntimeError, match="synthetic"):
        provider.chat("request")
    assert state["calls"] == 1
    assert not (tmp_path / "response-001.json").exists()
    with pytest.raises(ValueError, match="development_call_limit"):
        provider.chat("second")
    assert attempts == ["request"]


def test_success_preserves_exact_response_for_semantic_review(tmp_path):
    state = dict(calls=0, input_tokens=0, output_tokens=0)
    response = SimpleNamespace(content='{"quote":"原始 **措辞**"}',
                               finish_reason="stop",
                               usage=SimpleNamespace(input_tokens=12, output_tokens=7))
    provider = Counted(SimpleNamespace(chat=lambda _: response), state=state,
                       call_limit=1, directory=tmp_path)
    assert provider.chat("request") is response
    saved = json.loads((tmp_path / "response-001.json").read_text(encoding="utf-8"))
    assert saved == dict(content=response.content, finish_reason="stop")
    assert state == dict(calls=1, input_tokens=12, output_tokens=7)
