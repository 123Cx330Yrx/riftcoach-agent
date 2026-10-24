import json
from types import SimpleNamespace

import pytest

from app.evaluation.golden_context_relation_probe import build_request, validate_response
from app.evaluation.golden_review_experiment import SourceIndex, compact, digest
from app.evaluation.golden_fact_candidate import fact_pack
from app.providers.errors import ProviderResponseError
from scripts import run_golden_context_relation_probe as runner
from tests import test_golden_evidence_runtime as shared


def fixture():
    _, request = shared.request_fixture()
    target = "差异较稳定。"
    context = "下句的较稳定仅指这四场方向一致。"
    report = context + "\n\n" + target + "\n\n建议[K1]"
    pack = fact_pack(request.player_summary)
    source = SourceIndex.build(report, pack)
    value = dict(source_digest=source.source_digest, target_ref=source.reference(target),
        disposition="sample_defined", context_ref=source.reference(context),
        referring_expression="下句的较稳定", defined_meaning="仅指这四场方向一致", explanation="前段定义下句")
    case = dict(id="test", report=report, target=target, report_sha256=digest(report), expected_target="accept")
    return request, pack, value, case


@pytest.mark.parametrize("failure", ["digest", "target", "invented_definition", "missing_definition", "extra_object"])
def test_source_binding_and_shape_reject_without_semantic_shortcuts(failure):
    request, pack, value, case = fixture()
    assert validate_response(compact(value), case["report"], pack, case["target"]).disposition == "sample_defined"
    if failure == "digest": value["source_digest"] = "0" * 64
    if failure == "target": value["target_ref"] = {"block": 1}
    if failure == "invented_definition": value["defined_meaning"] = "模型编造的定义"
    if failure == "missing_definition": value["context_ref"] = None
    raw = compact(value) + ("{}" if failure == "extra_object" else "")
    with pytest.raises(ValueError):
        validate_response(raw, case["report"], pack, case["target"])


def test_full_context_request_and_transport_keep_current_budget():
    req, pack, _, case = fixture()
    built = build_request(req.player_summary, req.deterministic_report, req.knowledge, case["report"], case["target"])
    data = json.loads(built.messages[1].content.split("[UNTRUSTED DATA]\n")[1].split("\n[END UNTRUSTED DATA]")[0])
    assert data["source_index"] == SourceIndex.build(case["report"], pack).prompt_sources()
    assert data["facts_and_provenance"] == pack
    assert data["deterministic_source_facts"] == req.deterministic_report
    assert built.max_tokens == 32768 and built.timeout_s == 300 and built.temperature == 1.0
    from app.evaluation.golden_stream_bridge import validate_request
    from app.runtime.coach_contract import CONTEXT_COACH_CONTRACT
    validate_request(built, transport_id=CONTEXT_COACH_CONTRACT.descriptor()["stream_transport_id"])
    with pytest.raises(ValueError, match="input_budget_exceeded"):
        build_request(req.player_summary, "X"*400000, req.knowledge, case["report"], case["target"])


def test_preview_never_reads_credentials_or_calls_provider(monkeypatch, capsys):
    req, pack, _, case = fixture()
    monkeypatch.setattr(runner, "load_inputs", lambda *a:(req.player_summary, req.deterministic_report, req.knowledge, [case]))
    monkeypatch.setattr(runner, "verify_public_ci", lambda *a:pytest.fail("no CI in preview"))
    import app.providers.config as config
    monkeypatch.setattr(config, "load_zhipu_settings", lambda *a:pytest.fail("no secrets in preview"))
    plan = runner.run(SimpleNamespace(source_run=None, base_report=None, execute=False))
    assert plan["max_calls"] == 4 and not plan["whole_report_acceptance"] and not plan["labels_sent_to_model"]
    built = build_request(req.player_summary, req.deterministic_report, req.knowledge, case["report"], case["target"])
    assert "expected_target" not in built.messages[1].content and "prior_verdict" not in built.messages[1].content


@pytest.mark.parametrize("failure", ["transport", "protocol", "semantic", "none"])
def test_one_call_each_and_accounting_on_failure(tmp_path, failure):
    req, pack, value, case = fixture()
    cases = [dict(case, id=f"case-{n}") for n in range(4)]
    requests = [build_request(req.player_summary, req.deterministic_report, req.knowledge, case["report"], case["target"])] * 4
    state = dict(calls=0, input_tokens=0, output_tokens=0)
    def chat(request):
        state["calls"] += 1
        if failure == "transport": raise ProviderResponseError(provider="test", code="connection_failed")
        state["input_tokens"] += 10
        state["output_tokens"] += 5
        if failure == "semantic":
            value.update(disposition="needs_clarification", context_ref=None, referring_expression=None, defined_meaning=None)
        return shared.ChatResponse(content="invalid" if failure == "protocol" else compact(value),
            provider="test", model="test", finish_reason="stop", usage=shared.TokenUsage(input_tokens=10,output_tokens=5))
    if failure == "transport":
        with pytest.raises(ProviderResponseError): runner.observe(SimpleNamespace(chat=chat),tmp_path,cases,requests,pack,state)
    else:
        runner.observe(SimpleNamespace(chat=chat),tmp_path,cases,requests,pack,state)
    receipt = json.loads((tmp_path/"receipt.json").read_text())
    assert not receipt["whole_report_acceptance"]
    counts = receipt["case_counts"]
    if failure in {"transport", "protocol"}:
        assert state["calls"] == 1 and counts["not_started"] == 3
        assert counts["interrupted"] == (1 if failure == "transport" else 0)
        assert counts["finalized"] == (0 if failure == "transport" else 1)
    else:
        assert state["calls"] == 4 and counts["finalized"] == 4
        assert receipt["automatic_target_matches"] == (0 if failure == "semantic" else 4)
