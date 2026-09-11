from dataclasses import replace
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as m
from app.providers.errors import ProviderResponseError, ProviderTimeoutError
from app.providers.models import ChatMessage, ChatRequest, MessageRole, ToolCall, ToolChoiceMode, ToolSpec, StructuredResponseContract
from app.providers.zhipu import ZhipuProvider
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
from tests.test_zhipu_stream_adapter import FakeClient, ClosableStream, chunk, usage, tool_fragment


def request(**kwargs):
    return ChatRequest(messages=(ChatMessage(MessageRole.USER, "secret-prompt"),), max_tokens=8192, timeout_s=90, **kwargs)


def collect(tmp_path, chunks, req=None, close_error=None, allow_tool_content=False):
    raw = ClosableStream(chunks, close_error=close_error)
    client = FakeClient(raw)
    provider = ZhipuProvider.from_candidate_profile(client=client, model="glm-5.3-flash",
        profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE)
    req = req or request()
    result = m.collect(req, lambda r,hook: provider.stream_adapter(tool_stream=bool(r.tools)).stream_session(r, include_usage_tail=True),
                       directory=tmp_path, started=0, deadline=90, clock=lambda: 1,
                       allow_tool_content=allow_tool_content)
    assert raw.closed
    return result, client.completions.calls[0]


def test_complete_response_private_reasoning_and_payload(tmp_path):
    result, payload = collect(tmp_path, [chunk(reasoning="secret-reasoning"), chunk(content="secret-body", finish_reason="stop"), chunk(raw_usage=usage())])
    assert result.content == "secret-body" and result.reasoning_content == "secret-reasoning"
    assert m.RESPONSE.validate_json(m.RESPONSE.dump_json(result)) == result
    assert payload["stream_options"] == {"include_usage": True}
    assert payload["extra_body"]["reasoning_effort"] == "high" and payload["max_tokens"] == 8192
    assert "secret" not in (tmp_path / "progress.json").read_text()


def test_tool_fragments_then_tool_result_reasoning_roundtrip(tmp_path):
    req = request(tools=(ToolSpec("knowledge.search", "search fixture", {"type": "object"}),))
    result, payload = collect(tmp_path, [chunk(reasoning="private-thinking"),
        chunk(tool_calls=[tool_fragment(index=0, call_id="call_1", name="knowledge_search", arguments='{"query":')]),
        chunk(tool_calls=[tool_fragment(index=0, arguments='"fixture"}')], finish_reason="tool_calls"),
        chunk(raw_usage=usage())], req)
    assert payload["extra_body"]["tool_stream"] is True
    assert result.tool_calls[0].arguments == {"query": "fixture"}
    req2 = replace(req, messages=(*req.messages, ChatMessage(MessageRole.ASSISTANT, tool_calls=result.tool_calls,
        reasoning_content=result.reasoning_content), ChatMessage(MessageRole.TOOL, "fixture-result", tool_call_id="call_1")))
    assert m.REQUEST.validate_json(m.REQUEST.dump_json(req2)) == req2
    other = tmp_path / "next"; other.mkdir()
    _, sent = collect(other, [chunk(content="answer", finish_reason="stop"), chunk(raw_usage=usage())], req2)
    assert sent["messages"][1]["reasoning_content"] == "private-thinking"
    assert sent["messages"][2]["tool_call_id"] == "call_1"


@pytest.mark.parametrize("chunks", [
    [chunk(reasoning="secret")], [chunk(content="secret")],
    [chunk(content="secret", finish_reason="stop")],
    [chunk(content="secret", finish_reason="length"), chunk(raw_usage=usage())],
    [chunk(content="secret", finish_reason="stop"), chunk(raw_usage=usage(1,8193))],
    [chunk(content="secret", finish_reason="stop"), chunk(raw_usage=usage(64001,1))],
])
def test_incomplete_or_overbudget_never_delivers(tmp_path, chunks):
    with pytest.raises(Exception):
        collect(tmp_path, chunks)
    assert "secret" not in (tmp_path / "progress.json").read_text()


def test_close_failure_discards_complete_content(tmp_path):
    with pytest.raises(Exception):
        collect(tmp_path, [chunk(content="secret", finish_reason="stop"), chunk(raw_usage=usage())], close_error=RuntimeError("secret-close"))
    progress = json.loads((tmp_path / "progress.json").read_text())
    assert progress["close_state"] == "failed"
    assert "secret" not in json.dumps(progress)


def test_structured_request_survives_ipc(tmp_path):
    contract = StructuredResponseContract(name="fixture", version="1.0.0", json_schema={"type":"object","properties":{"ok":{"type":"boolean"}},"required":["ok"]})
    req = request(response_contract=contract)
    assert m.REQUEST.validate_json(m.validate_request(req)) == req
    result, payload = collect(tmp_path, [chunk(content='{"ok":true}', finish_reason="stop"), chunk(raw_usage=usage())], req)
    assert json.loads(result.content) == {"ok": True}
    assert payload["response_format"]["type"] == "json_object"


def test_parent_ipc_complete_child_and_no_payload_on_disk(tmp_path):
    code = '''import sys,json
from app.evaluation.golden_stream_bridge import REQUEST,RESPONSE
from app.providers.models import ChatResponse,TokenUsage
r=REQUEST.validate_json(sys.stdin.buffer.read())
assert r.messages[0].content=="secret-prompt"
sys.stdout.buffer.write(RESPONSE.dump_json(ChatResponse(content="secret-response", model="glm-5.3-flash",provider="zhipu",usage=TokenUsage(1,1),finish_reason="stop")))
'''
    response = m.run_child([sys.executable,"-B","-c",code], m.REQUEST.dump_json(request()), directory=tmp_path, timeout_s=15)
    assert response.content == "secret-response"
    assert "secret" not in (tmp_path / "result.json").read_text()


def test_actual_worker_fake_sdk_closes_before_private_delivery(tmp_path):
    code = '''import sys,openai
from pathlib import Path
from app.evaluation.golden_stream_bridge import worker
from tests.test_zhipu_stream_adapter import FakeClient,ClosableStream,chunk,usage
raw=ClosableStream([chunk(reasoning="secret-thinking"),chunk(content="secret-answer",finish_reason="stop"),chunk(raw_usage=usage())])
client=FakeClient(raw)
def close():
 assert raw.closed
client.close=close
openai.OpenAI=lambda **kwargs:client
worker(Path(DIRECTORY),float(sys.argv[-3]),float(sys.argv[-1]))
'''.replace("DIRECTORY", repr(str(tmp_path)))
    import os
    environ=dict(os.environ, LLM_PROVIDER="zhipu",LLM_MODEL="glm-5.3-flash",
                 LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4",LLM_API_KEY="fixture")
    response=m.run_child([sys.executable,"-B","-c",code],m.validate_request(request()),
                         directory=tmp_path,timeout_s=15,environ=environ)
    assert response.content=="secret-answer" and response.reasoning_content=="secret-thinking"
    assert all("secret" not in path.read_text() for path in tmp_path.iterdir())


@pytest.mark.parametrize("code", ["raise SystemExit(1)","print('secret-invalid-json')"])
def test_child_failure_never_leaks_output(tmp_path,code):
    with pytest.raises(ProviderResponseError) as caught:
        m.run_child([sys.executable,"-c",code],b"{}",directory=tmp_path,timeout_s=10)
    assert "secret" not in str(caught.value)
    assert json.loads((tmp_path/"result.json").read_text())["state"]=="failed"


@pytest.mark.parametrize("action", ["import threading;threading.Event().wait(30)",
    "import sys,threading;sys.stdout.write('partial-secret');sys.stdout.flush();threading.Event().wait(30)"])
def test_parent_stuck_or_partial_child_deadline(tmp_path, action):
    started = time.monotonic()
    with pytest.raises(ProviderTimeoutError):
        m.run_child([sys.executable,"-c",action], b"{}", directory=tmp_path, timeout_s=1)
    assert time.monotonic() - started < 8
    data = (tmp_path / "result.json").read_text()
    assert "partial-secret" not in data and json.loads(data)["state"] == "deadline"


def test_failure_poison_prevents_next_external_attempt(tmp_path, monkeypatch):
    calls=[]
    def fail(*a,**kw):
        calls.append(1)
        raise ProviderTimeoutError(provider="zhipu",code="fixture")
    monkeypatch.setattr(m,"run_child",fail)
    provider = m.GoldenProcessStreamProvider(settings=NS(model="glm-5.3-flash",base_url="https://open.bigmodel.cn/api/paas/v4",api_key="secret"),directory=tmp_path)
    with pytest.raises(ProviderTimeoutError): provider.chat(request())
    with pytest.raises(ProviderResponseError): provider.chat(request())
    assert len(calls)==1
    assert not (tmp_path/"stream-002").exists()


def test_transport_preflight_is_opt_in_and_budget_unchanged():
    from app.evaluation.coach_real_data_golden_slice import GoldenSliceConfig,preflight
    config = GoldenSliceConfig(riot_id="Fixture#TEST",routing_region="asia",run_id="fixture_stream",with_provider=True)
    old = preflight(config).model_dump(mode="json")
    new = preflight(replace(config,provider_transport=m.TRANSPORT_ID)).model_dump(mode="json")
    assert "provider_transport" not in old
    assert new.pop("provider_transport") == m.TRANSPORT_ID and new==old
    with pytest.raises(ValueError): preflight(replace(config,with_provider=False,provider_transport=m.TRANSPORT_ID))


def test_bridge_identity_satisfies_existing_coach_contract(tmp_path):
    from app.runtime.coach_contract import ADVICE_COACH_CONTRACT
    provider=m.GoldenProcessStreamProvider(settings=NS(model="glm-5.3-flash",base_url="https://open.bigmodel.cn/api/paas/v4",api_key="fixture"),directory=tmp_path)
    ADVICE_COACH_CONTRACT.require_provider(provider)
    assert not provider.capabilities.streaming


def test_full_nine_call_coach_replay_through_wire_and_assembler(tmp_path,monkeypatch):
    import scripts.check_coach_golden_replay as replay
    from app.providers.stream_adapter_contract import ProviderStreamEvent,StreamToolCallDelta
    from app.runtime.coach_contract import ADVICE_COACH_CONTRACT
    from tests.test_coach_application_composition import dependencies
    original=replay._ReplayProvider
    class StreamReplay(original):
        def chat(self,request):
            request=m.REQUEST.validate_json(m.validate_request(request))
            scripted=super().chat(request)
            if scripted.tool_calls:
                scripted=replace(scripted,content="fixture tool preamble, not final report")
            event=ProviderStreamEvent(content_delta=scripted.content,reasoning_delta=scripted.reasoning_content,
                finish_reason=scripted.finish_reason,usage=scripted.usage,model=scripted.model,
                request_id_sha256="a"*64,tool_call_deltas=tuple(StreamToolCallDelta(index=i,call_id=c.id,
                name=c.name,arguments_delta=json.dumps(dict(c.arguments))) for i,c in enumerate(scripted.tool_calls)))
            class Session:
                close_report=NS(composite_state="closed")
                def __iter__(self):return iter([event])
                def close(self):pass
            directory=tmp_path/str(len(self.requests));directory.mkdir()
            response=m.collect(request,lambda r,hook:Session(),directory=directory,started=0,deadline=90,clock=lambda:1,
                               allow_tool_content=True)
            return m.RESPONSE.validate_json(m.RESPONSE.dump_json(response))
    monkeypatch.setattr(replay,"_ReplayProvider",StreamReplay)
    result=replay.probe(dependencies()["summary_builder"].summary,contract=ADVICE_COACH_CONTRACT,training_positions=())
    assert result["scripted_provider_calls"]==9
    assert result["revision_count"]==1 and result["terminal_reason"]=="evaluation_failed"
    assert not result["report_available"]


@pytest.mark.parametrize("enabled",[False,True])
def test_mixed_tool_round_requires_new_explicit_policy(tmp_path,enabled):
    from app.providers.stream_adapter_contract import StreamAdapterError
    req=request(tools=(ToolSpec("knowledge.search","fixture",{"type":"object"}),))
    chunks=[chunk(content="secret-preamble",tool_calls=[tool_fragment(index=0,call_id="call_1",
        name="knowledge_search",arguments='{"query":"fixture"}')],finish_reason="tool_calls"),chunk(raw_usage=usage())]
    if not enabled:
        with pytest.raises(StreamAdapterError,match="tool_calls_with_content"):
            collect(tmp_path,chunks,req)
    else:
        result,_=collect(tmp_path,chunks,req,allow_tool_content=True)
        assert result.content=="secret-preamble" and result.requests_tools
        assert result.finish_reason=="tool_calls"
    assert "secret" not in (tmp_path/"progress.json").read_text()


@pytest.mark.parametrize("missing",["tool","usage","close"])
def test_mixed_policy_still_requires_all_completion_gates(tmp_path,missing):
    req=request(tools=(ToolSpec("knowledge.search","fixture",{"type":"object"}),))
    fragments=[] if missing=="tool" else [tool_fragment(index=0,call_id="call_1",name="knowledge_search",arguments='{}')]
    chunks=[chunk(content="private",tool_calls=fragments,finish_reason="tool_calls")]
    if missing!="usage":chunks.append(chunk(raw_usage=usage()))
    with pytest.raises(Exception):
        collect(tmp_path,chunks,req,allow_tool_content=True,
                close_error=RuntimeError("private") if missing=="close" else None)


def test_timing_distinguishes_advance_local_work_and_close(tmp_path, monkeypatch):
    from app.providers.stream_adapter_contract import ProviderStreamEvent
    from app.providers.models import TokenUsage
    now = [0.0]
    accept = m.ProviderStreamAssembler.accept
    write = m.write_progress
    def slow_accept(self, event):
        now[0] += .25
        return accept(self, event)
    def slow_write(directory, value):
        now[0] += .01
        write(directory, value)
    monkeypatch.setattr(m.ProviderStreamAssembler, "accept", slow_accept)
    monkeypatch.setattr(m, "write_progress", slow_write)
    class Session:
        close_report = NS(composite_state="closed")
        def __iter__(self):
            now[0] += 2
            yield ProviderStreamEvent(reasoning_delta="secret", model="glm-5.3-flash", request_id_sha256="a"*64)
            now[0] += 4
            yield ProviderStreamEvent(content_delta="secret", finish_reason="stop", usage=TokenUsage(1, 2),
                                      model="glm-5.3-flash", request_id_sha256="a"*64)
        def close(self): now[0] += .5
    def opener(r, hook):
        now[0] += 1
        return Session()
    m.collect(request(), opener, directory=tmp_path, started=0, deadline=90, clock=lambda: now[0])
    data = json.loads((tmp_path/"progress.json").read_text())
    assert data["schema_version"] == "1.1"
    assert data["open_duration_ms"] == 1000
    assert data["advance_duration_ms"] == 6000 and data["max_advance_duration_ms"] == 4000
    assert data["processing_duration_ms"] == 520 and data["close_duration_ms"] == 500
    assert data["max_inter_event_gap_ms"] == 4260
    assert data["last_content_ms"] > data["last_reasoning_ms"]
    assert data["progress_write_duration_ms"] == data["progress_writes"] * 10
    assert "secret" not in json.dumps(data)


def test_advance_exception_retains_gap_and_unclipped_elapsed(tmp_path):
    from app.providers.stream_adapter_contract import ProviderStreamEvent
    now = [0.0]
    class Session:
        close_report = NS(composite_state="closed")
        def __iter__(self):
            now[0] = 1
            yield ProviderStreamEvent(content_delta="secret", model="glm-5.3-flash", request_id_sha256="a"*64)
            now[0] = 91
            raise ProviderTimeoutError(provider="zhipu", code="fixture")
        def close(self): now[0] += .5
    with pytest.raises(ProviderTimeoutError):
        m.collect(request(), lambda r, hook: Session(), directory=tmp_path, started=0, deadline=90, clock=lambda: now[0])
    data = json.loads((tmp_path/"progress.json").read_text())
    assert data["error"] == "deadline" and data["close_state"] == "closed"
    assert data["last_event_ms"] == data["last_content_ms"] == 1000
    assert data["max_inter_event_gap_ms"] == 0  # No second accepted event.
    assert data["advance_duration_ms"] == 91000 and data["max_advance_duration_ms"] == 90000
    assert data["observed_elapsed_ms"] == 91500 and data["elapsed_ms"] == 90000
    assert data["terminal_ms"] is None and data["input_tokens"] is None


def test_request_metrics_are_body_free_and_reserved_before_io(tmp_path, monkeypatch):
    req = replace(request(), messages=(ChatMessage(MessageRole.SYSTEM, "secret-policy"),
        ChatMessage(MessageRole.USER, "secret-prompt"),
        ChatMessage(MessageRole.ASSISTANT, "secret-body", reasoning_content="secret-reasoning")))
    def fake_child(*args, **kwargs):
        data = json.loads((tmp_path/"stream-001"/"reservation.json").read_text())
        assert "secret" not in json.dumps(data)
        metrics = data["request_metrics"]
        assert metrics["message_count"] == 3 and metrics["input_token_ceiling"] > 0
        assert metrics["wire_bytes"] == len(m.validate_request(req))
        assert metrics["messages_by_role"]["assistant"]["reasoning_chars"] == 16
        raise ProviderResponseError(provider="zhipu", code="fixture")
    monkeypatch.setattr(m, "run_child", fake_child)
    provider = m.GoldenProcessStreamProvider(settings=NS(model="glm-5.3-flash",
        base_url="https://open.bigmodel.cn/api/paas/v4", api_key="secret"), directory=tmp_path)
    with pytest.raises(ProviderResponseError): provider.chat(req)
