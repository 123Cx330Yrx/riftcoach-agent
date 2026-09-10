import json
import subprocess
import sys
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_diagnostic as m


def event(**kwargs):
    return NS(reasoning_delta=kwargs.get("reasoning"), content_delta=kwargs.get("content"),
              finish_reason=kwargs.get("finish"), usage=kwargs.get("usage"))


class Session:
    close_failed = False
    def __init__(self, events):
        self.events = events
        self.closed = False
    def __iter__(self):
        return iter(self.events)
    def close(self):
        self.closed = True


def run(tmp_path, events, **kwargs):
    session = Session(events)
    value = m.observe(lambda *a: session, directory=tmp_path, started=0, deadline=90,
                      clock=lambda: 1, **kwargs)
    assert session.closed
    return value


@pytest.mark.parametrize("events,state", [
    ([event(reasoning="secret-reasoning")], "incomplete"),
    ([event(content="secret-body")], "incomplete"),
    ([event(content="secret-body", finish="stop")], "incomplete"),
    ([event(content="secret-body", finish="length", usage=NS(input_tokens=12, output_tokens=8))], "incomplete"),
    ([event(reasoning="secret-reasoning"), event(content="secret-body", finish="stop"),
      event(usage=NS(input_tokens=12, output_tokens=8))], "complete"),
])
def test_terminal_and_usage_required_and_no_body(tmp_path, events, state):
    value = run(tmp_path, events)
    assert value.state == state
    assert "secret" not in (tmp_path / "progress.json").read_text()


@pytest.mark.parametrize("events,error", [
    ([event(content="x" * (m.MAX_CHARS + 1))], "character_limit"),
    ([event()] * (m.MAX_EVENTS + 1), "event_limit"),
    ([event(usage=NS(input_tokens=64001, output_tokens=1))], "usage_limit"),
])
def test_caps(tmp_path, events, error):
    assert run(tmp_path, events).error == error


def test_open_failure_and_expired_budget(tmp_path):
    calls = []
    def opener(*args):
        calls.append(1)
        raise RuntimeError("secret-key")
    assert m.observe(opener, directory=tmp_path, started=0, deadline=1, clock=lambda: 2).error == "deadline"
    assert not calls
    assert m.observe(opener, directory=tmp_path, started=0, deadline=90, clock=lambda: 2).error == "provider_error"
    assert "secret" not in (tmp_path / "progress.json").read_text()


def test_swallowed_close_failure_and_safe_http_hook(tmp_path):
    session = Session([event(content="body", finish="stop", usage=NS(input_tokens=1, output_tokens=1))])
    session.close_failed = True
    def opener(hook, remaining):
        request = NS(extensions={})
        hook(request)
        request.extensions["trace"]("http11.receive_response_headers.started", {"secret": "key"})
        request.extensions["trace"]("secret-event", {"secret": "key"})
        return session
    value = m.observe(opener, directory=tmp_path, started=0, deadline=90, clock=lambda: 1)
    assert value.error == "close_failed" and value.http_requests == 1
    assert "secret" not in (tmp_path / "progress.json").read_text()


@pytest.mark.parametrize("phase", ["opening", "reading", "closing"])
def test_real_child_hard_deadline_and_immutable_receipt(tmp_path, phase):
    # Child publishes a valid milestone then blocks; parent must terminate it.
    path = tmp_path / "progress.json"
    code = "import pathlib,threading; pathlib.Path(" + repr(str(path)) + ").write_text(" + repr(m.Observation(state=phase).model_dump_json()) + "); threading.Event().wait(30)"
    result = m.supervise([sys.executable, "-c", code], directory=tmp_path, timeout_s=1)
    assert result["process_outcome"] == "parent_deadline"
    assert result["elapsed_ms"] < 10000
    assert result["observation"]["state"] == phase
    assert not result["quality_evaluated"]
    with pytest.raises(FileExistsError):
        m.write_new_json(tmp_path / "result.json", {})


def test_child_crash_and_invalid_projection(tmp_path):
    (tmp_path / "progress.json").write_text('{"body":"secret"}')
    result = m.supervise([sys.executable, "-c", "raise SystemExit(1)"], directory=tmp_path)
    assert result["process_outcome"] == "invalid_progress" and result["observation"] is None
    assert "secret" not in (tmp_path / "result.json").read_text()


def test_unreaped_child_still_leaves_receipt(tmp_path, monkeypatch):
    def timeout(*a, **kw):
        raise subprocess.TimeoutExpired("child", 1)
    monkeypatch.setattr(m.subprocess, "Popen", lambda *a, **kw: NS(wait=timeout, poll=lambda: None, kill=lambda: None))
    result = m.supervise(["child"], directory=tmp_path)
    assert result["process_outcome"] == "child_unreaped"
    assert (tmp_path / "result.json").is_file()


def test_bad_input_identity_zero_io(tmp_path):
    with pytest.raises(ValueError, match="run_invalid"):
        m.prepare_request(tmp_path, saved_run_id="../escape", summary_sha="a" * 64,
                          manifest_sha="b" * 64, riot_id="Offline#TEST", region="asia")


def test_actual_adapter_high_payload_usage_tail_and_close(tmp_path):
    from tests.test_zhipu_stream_adapter import FakeClient, ClosableStream, chunk, usage
    from app.providers.zhipu import ZhipuProvider
    from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
    from app.providers.models import ChatRequest, ChatMessage, MessageRole
    raw = ClosableStream([chunk(reasoning="secret"), chunk(content="secret", finish_reason="stop"), chunk(raw_usage=usage())])
    client = FakeClient(raw)
    provider = ZhipuProvider.from_candidate_profile(client=client, model="glm-5.3-flash",
        profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE)
    request = ChatRequest(messages=(ChatMessage(MessageRole.USER, "fixture"),), max_tokens=8192, timeout_s=90)
    value = m.observe(lambda *a: provider.stream_adapter().stream_session(request, include_usage_tail=True),
                      directory=tmp_path, started=0, deadline=90, clock=lambda: 1)
    assert value.state == "complete" and raw.closed
    assert len(client.completions.calls) == 1
    payload = client.completions.calls[0]
    assert payload["max_tokens"] == 8192 and payload["stream"] is True
    assert payload["extra_body"]["reasoning_effort"] == "high"
    assert not provider.capabilities.streaming


@pytest.mark.parametrize("tamper", ["manifest", "content", "path", "duplicate"])
def test_pinned_manifest_and_artifact_tamper(tmp_path, monkeypatch, tamper):
    import hashlib
    run_id = "fixture_saved_run"
    root = tmp_path / run_id
    (root / "inputs").mkdir(parents=True)
    content = b"fixture"
    (root / "inputs/deterministic_report.md").write_bytes(content)
    row = dict(run_id=run_id, kind="deterministic_report", path="inputs/deterministic_report.md",
               sha256=hashlib.sha256(content).hexdigest())
    rows = [row]
    if tamper == "path":
        row["path"] = "../escape"
    if tamper == "duplicate":
        rows.append(dict(row))
    raw = json.dumps(dict(run_id=run_id, artifacts=rows)).encode()
    (root / "manifest.json").write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    if tamper == "manifest":
        sha = "a" * 64
    if tamper == "content":
        (root / "inputs/deterministic_report.md").write_bytes(b"tampered")
    monkeypatch.setattr(m, "load_saved_summary", lambda *a, **k: ({}, None))
    with pytest.raises((ValueError, RuntimeError)):
        m.prepare_request(tmp_path, saved_run_id=run_id, summary_sha="a" * 64,
                          manifest_sha=sha, riot_id="Offline#TEST", region="asia")
