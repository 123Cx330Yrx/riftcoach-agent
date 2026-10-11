from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from app.evaluation.golden_review_experiment import digest, compact
from app.evaluation.golden_inference_coverage import CoveredEvaluationResult
from app.harness.steps import EvaluationVerdict
from scripts import run_golden_context_controls as controls
from tests.test_golden_context_review import wire, claim
from app.evaluation.golden_context_review import expand_context
from tests import test_golden_evidence_runtime as shared


def result_fixture():
    value, report, pack = wire()
    claim(value, report, pack)
    payload = expand_context(compact(value), report, pack)
    base = shared.module.GroundedChatEvaluationAdapter._result(payload)
    return CoveredEvaluationResult(**base.__dict__, audits=tuple(a.model_dump(mode="json") for a in payload.audits),
        coverage=tuple(c.model_dump(mode="json") for c in payload.coverage)), report


def test_target_correctness_is_independent_of_whole_report_failure():
    result, target = result_fixture()
    case = dict(id="target", target=target, report=target, expected_target="accept", expected_report="reject", must_flag="长期能力差。")
    audits = json.loads(json.dumps(result.audits))
    audits[1]["claims"].append(dict(audits[1]["claims"][0], quote="长期能力差。", status="unsupported", scope="beyond_sample"))
    bad = replace(result, verdict=EvaluationVerdict.NEEDS_REVISION, audits=tuple(audits),
        issues=({"quote":"长期能力差。","category":"unsupported_comparison"},))
    row = controls.score(case, bad)
    assert row["target_matched"] and row["report_matched"]
    unrelated = replace(bad, issues=({"quote":"无关错误","category":"other"},))
    assert not controls.score(case, unrelated)["report_matched"]


def test_pass_without_target_claim_does_not_count_as_semantic_acceptance():
    result, target = result_fixture()
    case = dict(id="target", target=target, report=target, expected_target="accept", expected_report="accept")
    row = controls.score(case, replace(result, audits=()))
    assert row["report_matched"] and not row["target_matched"]


def test_terminal_full_stop_does_not_hide_wrong_acceptance_but_words_and_block_are_exact():
    result, target = result_fixture()
    audits = json.loads(json.dumps(result.audits))
    original = audits[1]["claims"][0]
    target = target.replace("。[K1]", "。")
    from app.evaluation.golden_inference_coverage import report_blocks
    original.update(quote=target[:-1], block_id=report_blocks(target)[0]["block_id"])
    case = dict(id="target", target=target, report=target, expected_target="clarify", expected_report="clarify")
    row = controls.score(case, replace(result, audits=tuple(audits)))
    assert row["target_accepted"] and not row["target_matched"]
    original["quote"] = original["quote"][:-2]
    assert not controls.score(case, replace(result, audits=tuple(audits)))["target_accepted"]
    original.update(quote=target, block_id="b99-invalid")
    assert not controls.score(case, replace(result, audits=tuple(audits)))["target_accepted"]


def test_complete_assembly_removes_confounding_definition_and_preserves_rest(monkeypatch):
    base = "before\n\n## 3. 主要风险点\n\n- **输局经济与输出同位置差距明显**：old definition\n- remaining risk\n\n## 4. 赢局与输局差异\nafter"
    monkeypatch.setattr(controls, "BASE_SHA", digest(base))
    result = controls.assemble(base, "new context\n\ntarget")
    assert result == "before\n\n## 3. 主要风险点\n\nnew context\n\ntarget\n\n- remaining risk\n\n## 4. 赢局与输局差异\nafter"
    with pytest.raises(ValueError, match="verified_base_report_required"): controls.assemble(base+"changed", "target")


def test_preview_has_zero_provider_ci_or_secret_io_and_no_labels(monkeypatch, capsys):
    _, request = shared.request_fixture()
    case = dict(id="test", pair=controls.PAIRS[0], report=request.report, report_sha256=digest(request.report),
        expected_target="hidden_label", rationale="do_not_send")
    monkeypatch.setattr(controls, "load_inputs", lambda *a:(request.player_summary, request.deterministic_report, request.knowledge, [case]))
    monkeypatch.setattr(controls, "verify_public_ci", lambda *a:pytest.fail("preview must not query CI"))
    import app.providers.config as config
    monkeypatch.setattr(config, "load_zhipu_settings", lambda *a:pytest.fail("preview must not load credentials"))
    seen=[]
    original=controls.evaluation_request
    def build(*a,**k):
        request=original(*a,**k); seen.append(request); return request
    monkeypatch.setattr(controls,"evaluation_request",build)
    controls.run(SimpleNamespace(source_run=None,base_report=None,pair=[1],execute=False))
    plan=json.loads(capsys.readouterr().out)
    assert plan["max_calls"]==4 and plan["reasoning_effort"]=="high"
    assert "hidden_label" not in seen[0].messages[1].content and "do_not_send" not in seen[0].messages[1].content


def test_public_freeze_retains_separate_target_and_report_expectations():
    manifest=json.loads(controls.MANIFEST.read_text(encoding="utf-8"))
    assert manifest["fragment_sha256"]==digest(controls.FRAGMENTS.read_text(encoding="utf-8"))
    cases=manifest["cases"]
    assert len(cases)==10 and {c["pair"] for c in cases}==set(controls.PAIRS)
    conflict=next(c for c in cases if c["id"]=="local_observation_with_later_conflict")
    assert (conflict["expected_target"],conflict["expected_report"])==("accept","reject")
