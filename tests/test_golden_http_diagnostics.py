import json
from types import SimpleNamespace

import httpcore
import httpx
import pytest
from httpcore._backends.mock import MockBackend, MockStream
from openai import DefaultHttpxClient, OpenAI

from app.evaluation.golden_http_diagnostics import GoldenHttpDiagnostics
from app.evaluation.golden_journal import GoldenCallJournal, JournaledProvider
from app.providers.errors import ProviderTimeoutError
from app.providers.models import ChatMessage, ChatRequest, MessageRole
from app.providers.zhipu import ZhipuProvider
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE


@pytest.mark.parametrize("failure,expected", [
    (None, "http11.receive_response_body.complete"),
    ("connect", "connection.connect_tcp.failed"),
    ("headers", "http11.receive_response_headers.failed"),
    ("body", "http11.receive_response_body.failed"),
])
def test_real_sdk_and_httpcore_phases_without_network(tmp_path, failure, expected):
    body = json.dumps({"id": "private-response-id", "model": "glm-5.3-flash",
                       "choices": [{"finish_reason": "stop", "message": {
                           "role": "assistant", "content": "private-response-body"}}],
                       "usage": {"prompt_tokens": 12, "completion_tokens": 8}}).encode()
    headers = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n"
    writes = []
    class Stream(MockStream):
        def read(self, *args, **kwargs):
            if failure == "headers" or (failure == "body" and len(self._buffer) == 1):
                raise httpcore.ReadTimeout("private-error-body")
            return super().read(*args, **kwargs)

        def write(self, buffer, timeout=None):
            writes.append(buffer)

    class Backend(MockBackend):
        calls = 0
        def connect_tcp(self, *args, **kwargs):
            self.calls += 1
            if failure == "connect":
                raise httpcore.ConnectTimeout("private-error-body")
            return Stream([headers, body])

    backend = Backend([])
    transport = httpx.HTTPTransport(retries=0)
    # Test-only fake socket backend exercises real httpcore trace emission.
    transport._pool = httpcore.ConnectionPool(network_backend=backend, retries=0)
    journal = GoldenCallJournal(tmp_path / "run", identity={}, limits={"provider": 1})
    diagnostics = GoldenHttpDiagnostics(journal)
    with DefaultHttpxClient(transport=transport, trust_env=False,
                            event_hooks={"request": [diagnostics.on_request]}) as http_client:
        with OpenAI(api_key="private-api-key", base_url="https://example.invalid/v4",
                    max_retries=0, http_client=http_client) as client:
            provider = ZhipuProvider.from_candidate_profile(
                client=client, model="glm-5.3-flash", profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE)
            wrapped = JournaledProvider(provider, journal, diagnostics=diagnostics)
            request = ChatRequest(messages=(ChatMessage(MessageRole.USER, "private-prompt"),), timeout_s=90)
            if failure:
                with pytest.raises(ProviderTimeoutError):
                    wrapped.chat(request)
            else:
                assert wrapped.chat(request).content == "private-response-body"
    record = json.loads((journal.directory / "http-001.json").read_text())
    assert record["outcome"] == ("failed" if failure else "response")
    assert record["http_requests"] == backend.calls == journal.counts["provider"] == 1
    assert expected in [event["event"] for event in record["events"]]
    assert "private" not in (journal.directory / "http-001.json").read_text()
    if failure != "connect":
        payload = json.loads(b"".join(writes).split(b"\r\n\r\n", 1)[1])
        assert payload["stream"] is False
        assert payload["messages"][0]["content"] == "private-prompt"


def test_allowlist_cap_and_attempt_separation(tmp_path):
    journal = GoldenCallJournal(tmp_path / "run", identity={}, limits={"provider": 2})
    now = [0.0]
    diagnostics = GoldenHttpDiagnostics(journal, clock=lambda: now[0])
    class Secret:
        def __str__(self):
            raise AssertionError("must not inspect trace data")
    def chat(request):
        diagnostics.on_request(SimpleNamespace(extensions={}))
        diagnostics.on_trace("private-untrusted-event", Secret())
        for _ in range(70):
            now[0] += .001
            diagnostics.on_trace("http11.receive_response_headers.started", Secret())
        return request
    wrapped = JournaledProvider(SimpleNamespace(chat=chat), journal, diagnostics=diagnostics)
    assert wrapped.chat("one") == "one"
    assert wrapped.chat("two") == "two"
    for ordinal in (1, 2):
        row = json.loads((journal.directory / f"http-{ordinal:03d}.json").read_text())
        assert row["provider_ordinal"] == ordinal
        assert len(row["events"]) == 64 and row["dropped_events"] == 6
        assert row["elapsed_ms"] == 70 and row["http_requests"] == 1


def test_interruption_is_preserved_and_not_retried(tmp_path):
    journal = GoldenCallJournal(tmp_path / "run", identity={}, limits={"provider": 1})
    diagnostics = GoldenHttpDiagnostics(journal)
    def interrupt(request):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        JournaledProvider(SimpleNamespace(chat=interrupt), journal, diagnostics=diagnostics).chat(None)
    row = json.loads((journal.directory / "http-001.json").read_text())
    assert row["outcome"] == "interrupted" and row["http_requests"] == 0
    assert row["events"] == []


def test_proxy_connect_tls_phase_uses_actual_httpcore_event_name(tmp_path):
    journal = GoldenCallJournal(tmp_path / "run", identity={}, limits={"provider": 1})
    diagnostics = GoldenHttpDiagnostics(journal)
    transport = httpx.HTTPTransport()
    transport._pool = httpcore.HTTPProxy(
        proxy_url="http://proxy.invalid", network_backend=MockBackend([
            b"HTTP/1.1 200 Connection Established\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok",
        ]), retries=0)
    with DefaultHttpxClient(transport=transport, trust_env=False,
                            event_hooks={"request": [diagnostics.on_request]}) as client:
        wrapped = JournaledProvider(SimpleNamespace(chat=lambda _: client.get("https://example.invalid")),
                                    journal, diagnostics=diagnostics)
        assert wrapped.chat(None).text == "ok"
    row = json.loads((journal.directory / "http-001.json").read_text())
    events = [event["event"] for event in row["events"]]
    assert "proxy.start_tls.started" in events and "proxy.start_tls.complete" in events
    assert row["http_requests"] == 1
