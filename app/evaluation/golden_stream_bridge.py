"""Opt-in synchronous Coach port backed by one process-bounded stream per chat."""
from __future__ import annotations

from dataclasses import replace, fields, is_dataclass
from collections.abc import Mapping
import json
import hashlib
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from pydantic import TypeAdapter

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_http_diagnostics import _EVENTS
from app.evaluation.golden_stream_diagnostic import Observation, write_progress
from app.providers.errors import ProviderResponseError, ProviderTimeoutError
from app.providers.models import ChatRequest, ChatResponse
from app.providers.stream_adapter_contract import ProviderStreamAssembler
from app.providers.zhipu import ZhipuProvider
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE

TRANSPORT_ID = "golden-process-stream-v1"
REQUEST = TypeAdapter(ChatRequest)
RESPONSE = TypeAdapter(ChatResponse)
MAX_BYTES = 4_000_000
ROOT = Path(__file__).resolve().parents[2]


def _mapping(value):
    # StructuredResponseContract freezes schemas with mappingproxy recursively.
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return {field.name: getattr(value, field.name) for field in fields(value)}
    raise TypeError("stream_wire_type")


def validate_request(request):
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    if (not math.isfinite(request.timeout_s) or not 0 < request.timeout_s <= 90
            or request.max_tokens is None or request.max_tokens > 8192
            or estimate_runtime_request_input_ceiling(request) > 64000):
        raise ProviderResponseError(provider="zhipu", code="stream_request_budget")
    try:
        raw = json.dumps(request, default=_mapping, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError):
        raise ProviderResponseError(provider="zhipu", code="stream_request_encoding") from None
    if len(raw) > MAX_BYTES:
        raise ProviderResponseError(provider="zhipu", code="stream_request_size")
    return raw


def collect(request, opener, *, directory, started, deadline, clock=time.monotonic):
    """Only deliver after exhaustion and owned close; partial data remain private."""
    validate_request(request)
    value = Observation()
    assembler = ProviderStreamAssembler(provider_id="zhipu", requested_model="glm-5.3-flash",
        require_request_identity=True,
        max_output_tokens=request.max_tokens, max_events=16384, max_content_chars=262144,
        max_reasoning_chars=262144, max_tool_calls=8, max_tool_argument_chars=256000)
    session = None
    def stamp():
        return min(90000, max(0, round((clock() - started) * 1000)))
    def save():
        value.elapsed_ms = stamp()
        write_progress(directory, value)
    def check_time():
        if clock() >= deadline:
            raise ProviderTimeoutError(provider="zhipu", code="stream_deadline")
    def hook(request):
        value.http_requests += 1
        def trace(name, info):
            if name in _EVENTS:
                value.last_http_event = name
                save()
        request.extensions["trace"] = trace
    save()
    try:
        check_time()
        session = opener(replace(request, timeout_s=max(.001, deadline - clock())), hook)
        value.state = "reading"
        save()
        for event in session:
            check_time()
            assembler.accept(event)
            value.events += 1
            for field, present in (("first_event_ms", True),
                    ("first_reasoning_ms", bool(event.reasoning_delta and event.reasoning_delta.strip())),
                    ("first_visible_content_ms", bool(event.content_delta and event.content_delta.strip()))):
                if present and getattr(value, field) is None:
                    setattr(value, field, stamp())
                    save()
            value.content_chars += len(event.content_delta or "")
            value.reasoning_chars += len(event.reasoning_delta or "")
            if event.finish_reason:
                value.finish_reason, value.terminal_ms = event.finish_reason, stamp()
                save()
            if event.usage:
                value.input_tokens, value.output_tokens = event.usage.input_tokens, event.usage.output_tokens
                save()
            if value.events % 64 == 0:
                save()
        assembler.mark_exhausted()
        value.eof_ms = stamp()
    except BaseException:
        value.error = "provider_error"
        raise
    finally:
        value.state = "closing"
        save()
        if session is not None:
            try:
                session.close()
                if session.close_report.composite_state != "closed":
                    raise ProviderResponseError(provider="zhipu", code="stream_close_failed")
                value.close_state = "closed"
                value.close_ms = stamp()
            except BaseException:
                value.close_state, value.error = "failed", "close_failed"
                save()
                raise
        if value.error:
            value.state = "failed"
        save()
    try:
        check_time()
        result = assembler.finalize()
        if result.response.usage.input_tokens > 64000:
            raise ProviderResponseError(provider="zhipu", code="stream_input_usage_limit")
        value.state = "complete"
        save()
        return result.response
    except BaseException:
        value.state, value.error = "failed", "provider_error"
        save()
        raise


class GoldenProcessStreamProvider:
    provider_name = "zhipu"
    model_name = "glm-5.3-flash"
    capabilities = ZhipuProvider.capabilities
    thinking_profile_id = ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE.profile_id
    sdk_max_retries = 0
    runtime_profile = None

    def __init__(self, *, settings, directory):
        if settings.model != self.model_name or settings.base_url.rstrip("/") != "https://open.bigmodel.cn/api/paas/v4":
            raise ValueError("stream_provider_identity")
        self._settings, self._directory = settings, Path(directory)
        self._calls, self._failed = 0, False

    def chat(self, request):
        raw = validate_request(request)
        if self._failed or self._calls >= 9:
            raise ProviderResponseError(provider="zhipu", code="stream_bridge_exhausted")
        self._calls += 1
        directory = self._directory / f"stream-{self._calls:03d}"
        directory.mkdir(parents=True, exist_ok=False)
        write_new_json(directory / "reservation.json", {"transport_id": TRANSPORT_ID,
            "ordinal": self._calls, "request_sha256": hashlib.sha256(raw).hexdigest(),
            "state": "reserved_before_io"})
        environ = dict(os.environ)
        environ.update(LLM_API_KEY=self._settings.api_key, LLM_BASE_URL=self._settings.base_url,
                       LLM_MODEL=self.model_name, LLM_PROVIDER="zhipu")
        try:
            return run_child([sys.executable, "-B", "-m", "app.evaluation.golden_stream_bridge",
                "--worker", str(directory)], raw, directory=directory, timeout_s=request.timeout_s, environ=environ)
        except BaseException:
            self._failed = True
            raise


def run_child(command, raw, *, directory, timeout_s, environ=None):
    if not math.isfinite(timeout_s) or not 0 < timeout_s <= 90 or len(raw) > MAX_BYTES:
        raise ValueError("stream_ipc_budget")
    started = time.monotonic()
    deadline = started + timeout_s
    process = None
    state = "failed"
    try:
        process = subprocess.Popen([*command, "--started", str(started), "--deadline", str(deadline)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            cwd=ROOT, env=environ, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        output, _ = process.communicate(raw, timeout=max(.001, deadline - time.monotonic()))
        if process.returncode != 0 or len(output) > MAX_BYTES or time.monotonic() >= deadline:
            raise ValueError("stream_child_incomplete")
        response = RESPONSE.validate_json(output)
        if (response.model != "glm-5.3-flash" or response.provider != "zhipu"
                or response.finish_reason not in ("stop", "tool_calls")
                or response.usage.input_tokens > 64000 or response.usage.output_tokens > 8192):
            raise ValueError("stream_child_response")
        state = "complete"
        return response
    except subprocess.TimeoutExpired:
        state = "deadline"
        raise ProviderTimeoutError(provider="zhipu", code="stream_deadline") from None
    except KeyboardInterrupt:
        state = "interrupted"
        raise
    except Exception:
        raise ProviderResponseError(provider="zhipu", code="stream_child_failed") from None
    finally:
        if process is not None:
            try:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                state = "unreaped"
            if state != "unreaped":
                for pipe in (process.stdin, process.stdout):
                    if pipe is not None:
                        try:
                            pipe.close()
                        except (OSError, ValueError):
                            state = "cleanup_failed"
        write_new_json(directory / "result.json", {"transport_id": TRANSPORT_ID, "state": state,
            "elapsed_ms": round((time.monotonic() - started) * 1000), "body_free": True})
        if state in ("unreaped", "cleanup_failed"):
            raise ProviderResponseError(provider="zhipu", code="stream_cleanup_failed") from None


def worker(directory, started, deadline):
    from openai import OpenAI, DefaultHttpxClient
    from app.providers.config import load_zhipu_settings
    from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
    raw = sys.stdin.buffer.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("stream_ipc_size")
    request = REQUEST.validate_json(raw)
    validate_request(request)
    settings = load_zhipu_settings()
    if settings.model != "glm-5.3-flash" or settings.base_url.rstrip("/") != "https://open.bigmodel.cn/api/paas/v4":
        raise ValueError("stream_provider_identity")
    client = None
    class Owned:
        def __init__(self, session):
            self.session = session
        def __iter__(self):
            return iter(self.session)
        @property
        def close_report(self):
            return self.session.close_report
        def close(self):
            try:
                self.session.close()
            finally:
                client.close()
    def opener(request, hook):
        nonlocal client
        client = OpenAI(api_key=settings.api_key, base_url=settings.base_url, max_retries=0, timeout=request.timeout_s,
                       http_client=DefaultHttpxClient(event_hooks={"request": [hook]}))
        try:
            provider = ZhipuProvider.from_candidate_profile(client=client, model=settings.model,
                profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE)
            return Owned(provider.stream_adapter(tool_stream=bool(request.tools)).stream_session(request, include_usage_tail=True))
        except BaseException:
            client.close()
            raise
    response = collect(request, opener, directory=directory, started=started, deadline=deadline)
    output = RESPONSE.dump_json(response)
    if len(output) > MAX_BYTES:
        raise ValueError("stream_ipc_size")
    sys.stdout.buffer.write(output)
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", required=True, type=Path)
    parser.add_argument("--started", required=True, type=float)
    parser.add_argument("--deadline", required=True, type=float)
    args = parser.parse_args()
    try:
        worker(args.worker, args.started, args.deadline)
    except BaseException:
        raise SystemExit(1) from None
