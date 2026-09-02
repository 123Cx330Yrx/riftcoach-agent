from __future__ import annotations

import json
import threading
import time
from io import BytesIO
from pathlib import Path

import pytest

from app.evaluation.candidate_provider_close_wakeup_observation import (
    CANDIDATE_CLOSE_WAKE_SCHEMA_VERSION,
    CandidateCloseWakeReceipt,
    CandidateCloseWakeObservation,
    CandidateCloseWakeObservationError,
    CloseWakeState,
    observe_candidate_session,
    run_parent_close_wakeup_observation,
    summarize_provider_event,
    child_observation_line,
    write_candidate_close_wakeup_receipt,
)
from app.providers.stream_adapter_contract import ProviderStreamEvent


SHA = "a" * 40
PLAN_SHA = "b" * 40


def _report(**overrides):
    values = {
        "observation_state": "not_pending",
        "call_count": 1,
        "session_opened": True,
        "pending_reader_observed": False,
        "cancel_status": "not_attempted",
        "cancel_returned": False,
        "reader_woke": False,
        "event_categories": (),
        "initial_read_elapsed_ms": 1,
        "cancel_elapsed_ms": None,
        "reader_grace_ms": 100,
        "reader_wake_elapsed_ms": None,
        "close_report": {
            "iterator_state": "closed",
            "sdk_stream_state": "closed",
            "composite_state": "closed",
            "shared_resource": False,
        },
        "error_code": None,
        "child_exit_code": 0,
        "child_terminated": False,
    }
    values.update(overrides)
    return CandidateCloseWakeObservation(**values)


def _receipt(observation=None):
    return CandidateCloseWakeReceipt(
        implementation_sha=SHA,
        diagnostic_code_sha=SHA,
        input_plan_sha=PLAN_SHA,
        observation=observation or _report(),
    )


def test_contract_accepts_the_four_core_projection_states():
    assert _report().as_dict()["schema_version"] == CANDIDATE_CLOSE_WAKE_SCHEMA_VERSION
    assert _report().observation_state == CloseWakeState.NOT_PENDING
    assert _report(
        observation_state="pending_cancel_returned",
        pending_reader_observed=True,
        cancel_status="returned",
        cancel_returned=True,
        reader_woke=True,
        cancel_elapsed_ms=4,
        reader_wake_elapsed_ms=7,
    ).observation_state == "pending_cancel_returned"
    assert _report(
        observation_state="pending_cancel_timeout",
        pending_reader_observed=True,
        cancel_status="timeout",
        reader_grace_ms=100,
        error_code="cancel_timeout",
    ).observation_state == "pending_cancel_timeout"
    assert _report(
        observation_state="child_timeout",
        call_count=0,
        session_opened=False,
        pending_reader_observed=False,
        cancel_status="not_attempted",
        child_exit_code=None,
        child_terminated=True,
        error_code="child_timeout",
    ).observation_state == "child_timeout"


@pytest.mark.parametrize(
    "field,value",
    [
        ("error_code", "provider body leaked"),
        ("event_categories", ("content",)),
        ("initial_read_elapsed_ms", -1),
        ("observation_state", "provider_body"),
        ("child_exit_code", 10**10),
    ],
)
def test_contract_rejects_unsafe_or_invalid_values(field, value):
    with pytest.raises(CandidateCloseWakeObservationError):
        _report(**{field: value})


def test_from_dict_rejects_body_headers_request_ids_and_extra_keys():
    payload = _report().as_dict()
    for key, value in (
        ("body", "secret"),
        ("headers", {"authorization": "secret"}),
        ("request_id", "secret"),
        ("extra", True),
    ):
        with pytest.raises(CandidateCloseWakeObservationError):
            CandidateCloseWakeObservation.from_dict({**payload, key: value})


def test_repr_and_json_projection_are_body_free_and_writer_is_immutable(tmp_path: Path):
    receipt = _receipt()
    rendered = repr(receipt)
    assert "secret response body" not in rendered
    output = tmp_path / "receipt.json"
    written = write_candidate_close_wakeup_receipt(output, receipt)
    assert written == output
    parsed = json.loads(output.read_text(encoding="utf-8"))
    assert parsed["schema_version"] == CANDIDATE_CLOSE_WAKE_SCHEMA_VERSION
    with pytest.raises(FileExistsError, match="immutable"):
        write_candidate_close_wakeup_receipt(output, receipt)


def test_event_summary_only_contains_allowlisted_categories():
    event = ProviderStreamEvent(
        content_delta="secret answer",
        reasoning_delta="secret reasoning",
        finish_reason="stop",
        usage=None,
        model="glm-5.3-flash",
        request_id_sha256="c" * 64,
    )
    categories = summarize_provider_event(event)
    assert categories == ("reasoning_seen", "content_seen", "terminal_seen")
    assert all("secret" not in category for category in categories)


class _FakeSession:
    def __init__(self, actions, *, cancel_action=None, report=None):
        self._actions = list(actions)
        self._cancel_action = cancel_action
        self._report = report or {
            "iterator_state": "closed",
            "sdk_stream_state": "closed",
            "composite_state": "closed",
            "shared_resource": False,
        }
        self.cancel_calls = 0
        self.close_calls = 0

    def __next__(self):
        if not self._actions:
            raise StopIteration
        action = self._actions.pop(0)
        if isinstance(action, BaseException):
            raise action
        if callable(action):
            return action()
        return action

    def cancel(self, _code="candidate_close_wakeup"):
        self.cancel_calls += 1
        if self._cancel_action is not None:
            return self._cancel_action()

    def close(self):
        self.close_calls += 1

    @property
    def close_report(self):
        return self._report


def test_fake_session_opens_once_and_nonpending_does_not_retry():
    session = _FakeSession(
        [
            ProviderStreamEvent(content_delta="secret", finish_reason="stop"),
            StopIteration(),
        ]
    )
    calls = []

    def factory(request=None, *, include_usage_tail=False):
        calls.append((request, include_usage_tail))
        return session

    result = observe_candidate_session(
        factory,
        request=object(),
        initial_read_timeout_s=0.1,
        cancel_timeout_s=0.1,
        reader_grace_s=0.05,
    )
    assert calls == [(calls[0][0], True)]
    assert result.observation_state == "not_pending"
    assert result.call_count == 1
    assert session.cancel_calls == 0
    assert "secret" not in json.dumps(result.as_dict(), ensure_ascii=False)


def test_pending_reader_cancel_return_and_wake_are_distinguished():
    release = threading.Event()

    def blocked():
        release.wait(1)
        raise StopIteration

    session = _FakeSession([blocked], cancel_action=release.set)
    result = observe_candidate_session(
        lambda *, include_usage_tail: session,
        initial_read_timeout_s=0.01,
        cancel_timeout_s=0.1,
        reader_grace_s=0.1,
    )
    assert result.observation_state == "pending_cancel_returned"
    assert result.pending_reader_observed is True
    assert result.cancel_returned is True
    assert result.reader_woke is True


def test_pending_reader_cancel_timeout_is_bounded():
    never = threading.Event()
    session = _FakeSession(
        [lambda: (never.wait(1), None)[1]],
        cancel_action=lambda: never.wait(1),
    )
    result = observe_candidate_session(
        lambda *, include_usage_tail: session,
        initial_read_timeout_s=0.01,
        cancel_timeout_s=0.01,
        reader_grace_s=0.01,
    )
    assert result.observation_state == "pending_cancel_timeout"
    assert result.cancel_status == "timeout"
    assert result.reader_woke is False


def test_cancel_exception_is_safe_and_close_report_is_retained():
    session = _FakeSession(
        [lambda: time.sleep(1)],
        cancel_action=lambda: (_ for _ in ()).throw(RuntimeError("private body")),
    )
    result = observe_candidate_session(
        lambda *, include_usage_tail: session,
        initial_read_timeout_s=0.01,
        cancel_timeout_s=0.1,
        reader_grace_s=0.01,
    )
    assert result.observation_state == "pending_cancel_returned"
    assert result.cancel_status == "raised"
    assert result.error_code == "cancel_failed"
    assert "private body" not in repr(result)


class _FakeProcess:
    def __init__(self, output: bytes, *, returncode=0, hang=False):
        self.stdout = BytesIO(output)
        self.stderr = BytesIO(b"private provider error body")
        self.returncode = returncode
        self._hang = hang
        self.terminated = False
        self.killed = False

    def poll(self):
        return None if self._hang and not (self.terminated or self.killed) else self.returncode

    def wait(self, timeout=None):
        if self._hang and not (self.terminated or self.killed):
            raise TimeoutError
        return self.returncode

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


def test_parent_writes_safe_child_timeout_and_reaps(tmp_path: Path):
    output = tmp_path / "receipt.json"
    process = _FakeProcess(b'{"kind":"probe_started","call_count":1}\n', hang=True)
    result = run_parent_close_wakeup_observation(
        ["child"],
        output,
        implementation_sha=SHA,
        diagnostic_code_sha=SHA,
        input_plan_sha=PLAN_SHA,
        confirm_real_call=True,
        process_deadline_s=0.01,
        popen_factory=lambda *args, **kwargs: process,
    )
    assert result.observation.observation_state == "child_timeout"
    assert result.observation.child_terminated is True
    assert process.terminated or process.killed
    assert "private provider error body" not in output.read_text(encoding="utf-8")


def test_parent_accepts_only_the_safe_child_projection(tmp_path: Path):
    output = tmp_path / "receipt.json"
    child = _report(
        observation_state="pending_cancel_returned",
        pending_reader_observed=True,
        cancel_status="returned",
        cancel_returned=True,
        reader_woke=False,
        cancel_elapsed_ms=11,
    )
    process = _FakeProcess(
        ("probe_started\n" + child_observation_line(child) + "\n").encode("utf-8"),
        returncode=0,
    )
    result = run_parent_close_wakeup_observation(
        ["child"],
        output,
        implementation_sha=SHA,
        diagnostic_code_sha=SHA,
        input_plan_sha=PLAN_SHA,
        confirm_real_call=True,
        popen_factory=lambda *args, **kwargs: process,
    )
    assert result.observation.observation_state == "pending_cancel_returned"
    assert result.observation.child_exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["observation"]["reader_woke"] is False
    assert "probe_started" not in json.dumps(payload)


def test_parent_turns_malformed_child_output_into_safe_child_error(tmp_path: Path):
    output = tmp_path / "receipt.json"
    process = _FakeProcess(b'{"body":"private"}\n', returncode=2)
    result = run_parent_close_wakeup_observation(
        ["child"],
        output,
        implementation_sha=SHA,
        diagnostic_code_sha=SHA,
        input_plan_sha=PLAN_SHA,
        confirm_real_call=True,
        popen_factory=lambda *args, **kwargs: process,
    )
    assert result.observation.observation_state == "child_error"
    assert result.observation.error_code == "child_nonzero_exit"
    assert "private" not in output.read_text(encoding="utf-8")


def test_parent_confirmation_and_existing_output_are_checked_before_process(tmp_path: Path):
    output = tmp_path / "receipt.json"
    calls = []
    with pytest.raises(CandidateCloseWakeObservationError, match="confirmation"):
        run_parent_close_wakeup_observation(
            ["child"],
            output,
            implementation_sha=SHA,
            diagnostic_code_sha=SHA,
            input_plan_sha=PLAN_SHA,
            confirm_real_call=False,
            popen_factory=lambda *args, **kwargs: calls.append(True),
        )
    assert calls == []
    output.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError, match="immutable"):
        run_parent_close_wakeup_observation(
            ["child"],
            output,
            implementation_sha=SHA,
            diagnostic_code_sha=SHA,
            input_plan_sha=PLAN_SHA,
            confirm_real_call=True,
            popen_factory=lambda *args, **kwargs: calls.append(True),
        )
    assert calls == []


def test_child_confirmation_is_checked_before_context_or_client(monkeypatch, capsys):
    import importlib.util

    script_path = Path(__file__).parents[1] / "scripts" / "diagnose_glm53_flash_candidate_close_wakeup.py"
    spec = importlib.util.spec_from_file_location("candidate_close_cli", script_path)
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    touched = []
    monkeypatch.setattr(cli, "_load_environment", lambda _path: touched.append("env"))
    monkeypatch.setattr(cli, "_load_frozen_context", lambda _root: touched.append("context"))
    monkeypatch.setattr(cli, "OpenAI", lambda **_: touched.append("client"))
    args = cli._parser().parse_args(["--child"])
    assert cli._child_main(args) == 2
    assert touched == []
    assert "confirmation_required" in capsys.readouterr().out


def test_child_rejects_model_or_endpoint_before_client(monkeypatch, capsys):
    import importlib.util
    from types import SimpleNamespace

    script_path = Path(__file__).parents[1] / "scripts" / "diagnose_glm53_flash_candidate_close_wakeup.py"
    spec = importlib.util.spec_from_file_location("candidate_close_cli_mismatch", script_path)
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, "_load_frozen_context", lambda _root: SimpleNamespace(messages=()))
    monkeypatch.setattr(
        cli,
        "_load_environment",
        lambda _path: {
            "LLM_PROVIDER": "zhipu",
            "LLM_API_KEY": "secret",
            "LLM_BASE_URL": cli.BASE_URL,
            "LLM_MODEL": "wrong-model",
        },
    )
    touched = []
    monkeypatch.setattr(cli, "OpenAI", lambda **_: touched.append(True))
    args = cli._parser().parse_args(["--child", "--confirm-real-call"])
    assert cli._child_main(args) == 2
    assert touched == []
    output = capsys.readouterr().out
    assert "candidate_model_mismatch" in output
    assert "secret" not in output
