from dataclasses import replace
import json

import pytest

from app.evaluation import golden_bound_scope_review as bound
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from tests import test_golden_evidence_runtime as shared


def fixture():
    _, req = shared.request_fixture()
    target = "## 持续存在的输出差距"
    prepared = bound.prepare(req.player_summary, req.deterministic_report, req.knowledge,
        target + "\n\n本标题仅指这四场方向一致。[K1]", target)
    return prepared


def response(value, finish="stop"):
    return shared.ChatResponse(content=compact(value), provider="test", model="test", finish_reason=finish, usage=shared.TokenUsage())


def test_host_preserves_exact_heading_without_model_echo():
    prepared = fixture()
    issued = bound.seal_issued_request(prepared, prepared.request)
    value = dict(disposition="needs_clarification", context_ref=None, explanation="示例判断，不是语义标签")
    result = bound.decode(issued, response(value), receipt_request_sha256=issued.request_sha256)
    assert result["target_quote"] == "## 持续存在的输出差距"
    assert result["target_ref"] == {"block": 1} and not result["whole_report_acceptance"]
    # Model text cannot override the host's target or source identity.
    for key in ("source_digest", "target_ref", "request_sha256"):
        with pytest.raises(ValueError):
            bound.decode(issued, response(dict(value, **{key:"forged"})), receipt_request_sha256=issued.request_sha256)


def test_actual_post_budget_request_hash_is_required():
    prepared = fixture()
    original = bound.seal_issued_request(prepared, prepared.request)
    budgeted = replace(prepared.request, timeout_s=250, metadata={**prepared.request.metadata, "coach_budget_contract":"coach-bounded-review-v2"})
    issued = bound.seal_issued_request(prepared, budgeted)
    assert issued.request_sha256 != original.request_sha256
    import hashlib
    assert issued.request_sha256 == hashlib.sha256(validate_request(budgeted, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()
    value = dict(disposition="sample_defined", context_ref={"block":2}, explanation="定义指向本标题，含义明确")
    with pytest.raises(ValueError, match="receipt_mismatch"):
        bound.decode(issued, response(value), receipt_request_sha256=original.request_sha256)
    result = bound.decode(issued, response(value), receipt_request_sha256=issued.request_sha256)
    assert result["context_quote"] == "本标题仅指这四场方向一致。[K1]"
    with pytest.raises(ValueError, match="issued_input_mismatch"):
        bound.seal_issued_request(prepared, replace(budgeted, messages=budgeted.messages[::-1]))
    from app.providers.models import ToolChoiceMode
    with pytest.raises(ValueError, match="issued_input_mismatch"):
        bound.seal_issued_request(prepared, replace(budgeted, tool_choice=ToolChoiceMode.NONE))


@pytest.mark.parametrize("failure", ["missing_context", "forged_context", "unfinished", "extra_json"])
def test_source_and_completion_failures_still_reject(failure):
    prepared = fixture()
    issued = bound.seal_issued_request(prepared, prepared.request)
    value = dict(disposition="sample_defined", context_ref={"block":2}, explanation="解释")
    if failure == "missing_context": value["context_ref"] = None
    if failure == "forged_context": value["context_ref"] = {"block":64}
    actual = response(value, "length" if failure == "unfinished" else "stop")
    if failure == "extra_json": actual = replace(actual, content=actual.content + "{}")
    with pytest.raises(ValueError): bound.decode(issued, actual, receipt_request_sha256=issued.request_sha256)


def test_full_data_and_budget_remain_in_request():
    prepared = fixture()
    data = json.loads(prepared.request.messages[1].content.split("[UNTRUSTED DATA]\n")[1].split("\n[END UNTRUSTED DATA]")[0])
    assert data["source_index"] == prepared.source.prompt_sources()
    assert prepared.request.max_tokens == 32768 and prepared.request.timeout_s == 300
    assert {"facts_and_provenance","knowledge","deterministic_source_facts"} <= data.keys()
