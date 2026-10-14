"""Actual worker/SDK/process and receipt path, with network replaced by fixtures."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation import document_review_timing_adapter as timing
from app.evaluation.document_review_timed_transport import TimedDocumentProviderFactory
from app.evaluation.golden_coarse_source_projection import VERSION as PROJECTION
from app.harness.steps import RevisionRequest
from app.providers.errors import ProviderError, ProviderResponseError, ProviderTimeoutError
from app.providers.zhipu import ZhipuProvider
from app.providers.zhipu_profiles import ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE
from app.runtime.review_sender import SharedBudgetReviewSender
from app.evaluation.golden_journal import write_new_json
from scripts.report_timed_document_workflow import TimedDocumentWorkflow as Workflow, request_sha
from tests.test_coarse_revision_editor import cases, BEFORE, AFTER
from tests.test_document_review_timed_budget import review
from tests.test_zhipu_stream_adapter import FakeClient, ClosableStream, chunk, usage, tool_fragment


def factory(tmp_path):
    def settings(model):
        return NS(model=model, api_key="OFFLINE_FIXTURE", base_url="https://open.bigmodel.cn/api/paas/v4")
    return TimedDocumentProviderFactory(generator_settings=settings("glm-5.3-flash"),
        reviewer_settings=settings("glm-5.3"), transport_root=tmp_path, source_projection=PROJECTION)


def test_time_identity_and_sdk_policy_are_explicit_and_old_boundary_refuses():
    request = review()
    assert bridge.validate_request(request, transport_id=bridge.TIMED_REVIEW_TRANSPORT_ID) == timing.request_bytes(request)
    assert bridge.transport_limits(bridge.TIMED_REVIEW_TRANSPORT_ID) == (32768, 600, 65536)
    assert bridge.transport_limits(bridge.TIMED_FLASH_TRANSPORT_ID) == (32768, 300, 65536)
    policy = bridge.transport_request_policy(bridge.TIMED_REVIEW_TRANSPORT_ID)
    assert (policy.agent_timeout_s, policy.llm_tool_timeout_s, policy.transport_timeout_s) == (630, 630, 660)
    descriptor = timing._TimedLimits().descriptor()
    assert descriptor["roles"]["review"]["transport_id"] == bridge.TIMED_REVIEW_TRANSPORT_ID
    assert descriptor["roles"]["generation"]["request_timeout_s"] == 300
    assert descriptor["request_policy"]["review"]["evaluation_transport_timeout_s"] == 660
    for transport in (bridge.REVIEW_MODEL_TRANSPORT_ID, bridge.CAPACITY_TRANSPORT_ID, bridge.TIMED_FLASH_TRANSPORT_ID):
        with pytest.raises(ProviderResponseError): bridge.validate_request(replace(request, timeout_s=100), transport_id=transport)
    with pytest.raises(ValueError): bridge.validate_request(replace(request, metadata={}), transport_id=bridge.TIMED_REVIEW_TRANSPORT_ID)
    from app.model_runtime import _issue_candidate_evaluation_request_policy, require_candidate_evaluation_request_policy
    with pytest.raises(ValueError): require_candidate_evaluation_request_policy(replace(policy), provider_id="zhipu", model="glm-5.3")
    with pytest.raises(ValueError):
        _issue_candidate_evaluation_request_policy(policy_id="other", version="1.0.0", provider_id="zhipu",
            model="glm-5.3", agent_timeout_s=630, llm_tool_timeout_s=630, transport_timeout_s=660,
            max_output_tokens=32768, temperature=1, top_p=.95)


def test_stream_can_complete_at_450_seconds_and_never_sends_host_metadata(tmp_path):
    request = review()
    raw = ClosableStream([chunk(content="Synthetic complete", finish_reason="stop", model="glm-5.3"), chunk(raw_usage=usage(10, 20), model="glm-5.3")])
    client = FakeClient(raw)
    provider = ZhipuProvider.from_candidate_profile(client=client, model="glm-5.3", profile=ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE)
    response = bridge.collect(request, lambda r, hook: provider.stream_adapter(
        evaluation_request_policy=bridge.transport_request_policy(bridge.TIMED_REVIEW_TRANSPORT_ID)).stream_session(r, include_usage_tail=True),
        directory=tmp_path, started=0, deadline=600, clock=lambda:450, transport_id=bridge.TIMED_REVIEW_TRANSPORT_ID)
    assert raw.closed and response.model == "glm-5.3"
    payload = client.completions.calls[0]
    assert payload["timeout"] == 150 and payload["extra_body"]["reasoning_effort"] == "high"
    assert "metadata" not in payload and timing.TIMED_MARKER not in json.dumps(payload)
    progress = json.loads((tmp_path / "progress.json").read_text())
    assert progress["schema_version"] == "1.4" and progress["elapsed_ms"] == 450000
    with pytest.raises(ValueError): bridge.CapacityBridgeObservation(elapsed_ms=450000)


def test_close_included_in_same_deadline_and_no_late_response(tmp_path):
    request = review(); clock = NS(now=599)
    raw = ClosableStream([chunk(content="complete", finish_reason="stop", model="glm-5.3"), chunk(raw_usage=usage(10,20), model="glm-5.3")])
    provider = ZhipuProvider.from_candidate_profile(client=FakeClient(raw), model="glm-5.3", profile=ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE)
    def opener(r, hook):
        session = provider.stream_adapter(evaluation_request_policy=bridge.transport_request_policy(bridge.TIMED_REVIEW_TRANSPORT_ID)).stream_session(r, include_usage_tail=True)
        close = session.close
        def delayed():
            close(); clock.now = 601
        session.close = delayed
        return session
    with pytest.raises(ProviderTimeoutError): bridge.collect(request, opener, directory=tmp_path,
        started=0, deadline=600, clock=lambda:clock.now, transport_id=bridge.TIMED_REVIEW_TRANSPORT_ID)
    assert raw.closed and json.loads((tmp_path / "progress.json").read_text())["state"] == "failed"


@pytest.mark.parametrize("reject_fresh", [False, True])
def test_actual_child_worker_sdk_receipt_and_full_workflow(tmp_path, monkeypatch, reject_fresh):
    """Each send invokes run_child + worker + SDK encoder, only client is fake."""
    real_child = bridge.run_child
    seen = []; digests = []
    def child(command, raw, **kwargs):
        req = bridge.REQUEST.validate_json(raw)
        seen.append(req)
        digests.append(hashlib.sha256(raw).hexdigest())
        phase = req.metadata.get("review_phase")
        if phase is None:
            model, tool, args = "glm-5.3-flash", None, None
        elif phase == "native_business_revision":
            model, tool, args = "glm-5.3-flash", "submit_block_edits", {"edits":{"block_4":[{
                "before":BEFORE,"after":AFTER,"reason":"Synthetic fixture edit; no business certification"}]}}
        else:
            model, tool = "glm-5.3", "submit_report_review"
            args = json.loads(cases()["claim-scope:4"][3]) if sum(timing.role_for_request(r) == "review" for r in seen) == 1 else {
                "score":96,"verdict":"pass","issues":[],"issue_resolutions":[],"advisories":[]}
            if reject_fresh and sum(timing.role_for_request(r) == "review" for r in seen) > 1:
                args = dict(json.loads(cases()["claim-scope:4"][3]), score=40, verdict="fail")
        code = """import sys,json,openai,socket
from pathlib import Path
from app.evaluation.golden_stream_bridge import worker
from tests.test_zhipu_stream_adapter import FakeClient,ClosableStream,chunk,usage,tool_fragment
def forbidden(*a,**k): raise AssertionError('No network allowed')
socket.socket.connect=forbidden
socket.create_connection=forbidden
tool=TOOL
args=ARGS
model=MODEL
events=[chunk(content='Synthetic generation',finish_reason='stop',model=model)] if tool is None else [chunk(tool_calls=[tool_fragment(index=0,call_id='fixture',name=tool,arguments=json.dumps(args,ensure_ascii=False))],finish_reason='tool_calls',model=model)]
events.append(chunk(raw_usage=usage(10,20),model=model))
raw=ClosableStream(events)
client=FakeClient(raw)
def close():
 assert raw.closed
 sent=client.completions.calls[0]
 assert sent['extra_body']['reasoning_effort']=='high' and sent['max_tokens']==32768
 assert 'metadata' not in sent and 'document-review-time-600-v1' not in json.dumps(sent)
client.close=close
openai.OpenAI=lambda **kw:client
worker(Path(DIRECTORY),float(sys.argv[-3]),float(sys.argv[-1]),TRANSPORT)
"""
        for marker, value in (("TOOL",tool),("ARGS",args),("MODEL",model),("DIRECTORY",str(kwargs["directory"])),("TRANSPORT",kwargs["transport_id"])):
            code = code.replace(marker, repr(value))
        return real_child([sys.executable,"-B","-c",code], raw, **kwargs)
    monkeypatch.setattr(bridge, "run_child", child)
    budget = timing.TimedDocumentBudget(factory(tmp_path)("chain"))
    from app.providers.models import ChatRequest, ChatMessage, MessageRole
    for n in (1,2):
        budget.chat(timing.prepare_request(ChatRequest(messages=(ChatMessage(MessageRole.USER,"Synthetic generation"),),
            max_tokens=32768, timeout_s=300, temperature=1, top_p=.95, metadata={"agent_loop_iteration":n})))
    req, _, _, _ = cases()["claim-scope:4"]
    flow = Workflow(SharedBudgetReviewSender(budget))
    initial = flow.evaluate(req)
    draft = flow.revise(RevisionRequest(req.player_summary,req.deterministic_report,req.knowledge,req.report,initial))
    assert draft.report == req.report.replace(BEFORE,AFTER)
    assert flow.evaluate(replace(req,report=draft.report)).verdict.value == ("fail" if reject_fresh else "pass")
    assert budget.calls == 5 and budget.tokens == 150 and budget.reserved_tokens == 0
    assert [r.timeout_s for r in seen[:4]] == [300,300,600,300]
    assert 590 < seen[-1].timeout_s <= 600
    # IPC decoder normalizes float annotations; receipt binds original raw
    # bytes (e.g. 600 vs 600.0), never a child reserialization.
    assert flow.last_edit_journal["final_review_receipt_request_sha256"] == digests[-1]
    assert len(list((tmp_path / "chain").glob("call-*.json"))) == 10
    assert flow.last_edit_journal["semantic_approval"] is False
    for role in ("generation","review"):
        for path in (tmp_path / "chain" / role).glob("stream-*/result.json"):
            assert json.loads(path.read_text())["state"] == "complete"


def test_parent_kills_timed_child_and_does_not_retry(tmp_path):
    with pytest.raises(ProviderTimeoutError):
        bridge.run_child([sys.executable,"-c","import time; time.sleep(10)"], timing.request_bytes(review()),
            directory=tmp_path, timeout_s=1, transport_id=bridge.TIMED_REVIEW_TRANSPORT_ID)
    result = json.loads((tmp_path / "result.json").read_text())
    assert result["state"] == "deadline" and result["body_free"]


@pytest.mark.parametrize("fault", ["unknown", "receipt", "wrong_model"])
def test_actual_factory_failures_keep_usage_and_poison_shared_task(tmp_path, monkeypatch, fault):
    from app.providers.models import ChatResponse, TokenUsage
    sent = []
    def child(command, raw, *, directory, **kwargs):
        sent.append(raw)
        if fault == "unknown":
            write_new_json(directory / "result.json", {"state":"deadline", "transport_id":kwargs["transport_id"]})
            raise ProviderTimeoutError(provider="zhipu", code="stream_deadline")
        write_new_json(directory / "result.json", {"state":"complete", "transport_id":kwargs["transport_id"]})
        if fault == "receipt":
            # Actual transport returned a response; its terminal file is bad.
            (directory / "result.json").write_text("malformed", encoding="utf-8")
        return ChatResponse(content="Synthetic response", provider="zhipu",
            model="wrong-model" if fault == "wrong_model" else "glm-5.3",
            finish_reason="stop", usage=TokenUsage(11,7))
    monkeypatch.setattr(bridge, "run_child", child)
    budget = timing.TimedDocumentBudget(factory(tmp_path)("failure"))
    with pytest.raises(ProviderError): budget.chat(review())
    assert budget.calls == 1 and budget.stopped and budget.last_exchange is None
    if fault == "receipt":
        assert budget.tokens == 18 and budget.reserved_tokens == 0
    else:
        assert budget.tokens == 0 and budget.reserved_tokens > 32768
    with pytest.raises(ProviderResponseError): budget.chat(review())
    assert len(sent) == 1
    assert len(list((tmp_path / "failure").glob("call-[0-9]*.json"))) == 1


def test_new_flash_identity_refused_by_legacy_transport_even_below_300():
    from app.providers.models import ChatRequest, ChatMessage, MessageRole
    request = timing.prepare_request(ChatRequest(messages=(ChatMessage(MessageRole.USER,"Synthetic generation"),),
        max_tokens=32768, timeout_s=300, temperature=1, top_p=.95, metadata={"agent_loop_iteration":1}))
    assert bridge.validate_request(request, transport_id=bridge.TIMED_FLASH_TRANSPORT_ID)
    with pytest.raises(ProviderResponseError, match="stream_transport_identity"):
        bridge.validate_request(replace(request, timeout_s=1), transport_id=bridge.CAPACITY_TRANSPORT_ID)


def test_duplicate_task_ordinal_cannot_send_second_request(tmp_path, monkeypatch):
    from app.providers.models import ChatResponse, TokenUsage
    sent = []
    def child(command, raw, *, directory, **kwargs):
        sent.append(raw)
        write_new_json(directory / "result.json", {"state":"complete", "transport_id":kwargs["transport_id"]})
        return ChatResponse(content="Synthetic response", provider="zhipu", model="glm-5.3", finish_reason="stop", usage=TokenUsage(11,7))
    monkeypatch.setattr(bridge, "run_child", child)
    create = factory(tmp_path)
    timing.TimedDocumentBudget(create("duplicate")).chat(review())
    second = timing.TimedDocumentBudget(create("duplicate"))
    with pytest.raises(FileExistsError): second.chat(review())
    assert second.stopped and len(sent) == 1 and second.reserved_tokens > 0


def test_direct_role_mismatch_stops_before_reservation(tmp_path):
    from app.providers.models import ChatRequest, ChatMessage, MessageRole
    router = factory(tmp_path)("mismatch")
    request = timing.prepare_request(ChatRequest(messages=(ChatMessage(MessageRole.USER,"Synthetic generation"),),
        max_tokens=32768, timeout_s=300, temperature=1, top_p=.95, metadata={"agent_loop_iteration":1}))
    with pytest.raises(ProviderResponseError, match="role_transport_identity_mismatch"):
        router.generator.chat_at_ordinal(request, ordinal=1, role="revision")
    assert not (tmp_path / "mismatch").exists()
