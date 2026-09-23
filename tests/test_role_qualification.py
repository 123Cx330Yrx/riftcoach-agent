"""Offline integrity tests; synthetic edits never establish model qualification."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation import role_qualification as qualification
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_notes import RoleNoteReviewWorkflow as RoleReviewWorkflow
from app.harness.steps import EvaluationVerdict, RevisionRequest
from app.providers.models import ChatResponse, TokenUsage
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts import prepare_role_qualification as preparation
from scripts import run_native_coach_product as product


@pytest.fixture(scope="module")
def prepared():
    return qualification.prepare_qualification()


@pytest.fixture
def isolated_source(tmp_path):
    paths = [qualification.COVERAGE, *qualification.DATASETS.values(),
        Path("tests/fixtures/native_missing_block_reassessment.json"),
        Path("tests/fixtures/native_heading_recheck_failure.json"),
        qualification.ASSETS / "prompt_programs/recent-form-review/manifest.json",
        qualification.ASSETS / "skills/recent-form-review/manifest.yaml",
        qualification.ASSETS / "skills/recent-form-review/SKILL.md"]
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(qualification.ROOT / path, target)
    return tmp_path


def test_original_fifteen_restore_from_committed_sources_without_runs(isolated_source, prepared):
    actual, requests = qualification.prepare_qualification(root=isolated_source)
    original = json.loads((qualification.ROOT / qualification.COVERAGE).read_text(encoding="utf-8"))
    assert actual == prepared[0] and requests == prepared[1]
    assert not (isolated_source / "data/runs").exists()
    assert len(actual["cases"]) == 15 and not actual["completed"]
    assert {row["status"] for row in actual["cases"]} == {"pending"}
    assert actual["aliases"] == original["aliases"]
    assert [c["key"] for c in actual["cases"]] == [
        f'{c["suite"]}:{c["index"]}' for c in original["completed"] + original["cases"]]
    for row in actual["cases"]:
        raw = requests[row["key"]]
        assert hashlib.sha256(raw).hexdigest() == row["request_sha256"]
        assert row["request_sha256"] != row["input_sha256"]
        assert b'expected_initial' not in raw and b'expected_host_only' not in raw
    assert not any(actual[k] for k in ("production_admitted", "execution_enabled",
        "review_controls_qualified", "actual_product_task_qualified"))


def test_changed_original_dataset_cannot_be_silently_requalified(isolated_source):
    path = isolated_source / qualification.DATASETS["attribution"]
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="role_qualification_dataset_changed"):
        qualification.prepare_qualification(root=isolated_source)


@pytest.mark.parametrize("old_path", [
    "golden_native_partitioned_tool_coverage_v2.json",
    "golden_explicit_source_pair_result_0c061b2.json",
])
def test_historical_coverage_or_two_diagnostics_cannot_admit_composition(old_path, tmp_path):
    old = json.loads((qualification.ROOT / "data/evaluation/results" / old_path).read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="role_qualification_identity_mismatch"):
        qualification.validate_qualification(old, evidence_root=tmp_path)


@pytest.mark.parametrize("defect", ["missing", "duplicate", "extra"])
def test_current_identity_still_requires_exact_original_fifteen(prepared, tmp_path, defect):
    plan, _ = prepared
    rows = deepcopy(plan["cases"])
    if defect == "missing":
        rows.pop()
    elif defect == "duplicate":
        rows[-1] = deepcopy(rows[0])
    else:
        rows.append(dict(rows[0], key="scope:2"))
    result = dict(qualification_version=qualification.VERSION, identity=plan["identity"],
        plan_sha256=digest(compact(plan)), cases=rows)
    with pytest.raises(ValueError, match="role_qualification_case_inventory_mismatch"):
        qualification.validate_qualification(result, evidence_root=tmp_path)


@pytest.fixture
def recorded_revision(tmp_path, monkeypatch):
    sources = {f["key"]: (f, s) for f, s in qualification.frozen_cases()[0]}
    frozen, source = sources["attribution:1"]
    _, corrected = sources["claim-scope:1"]
    previous = json.loads(preparation.PAIR_EVIDENCE.read_text(encoding="utf-8"))["original_json_contents"]
    responses = [
        bridge.RESPONSE.validate_python(previous["attribution_original-baseline/response.json"]),
        # A synthetic edit verifies plumbing only, never a real Flash edit.
        ChatResponse(content=corrected.report, model="glm-5.3-flash", provider="zhipu",
            finish_reason="stop", usage=TokenUsage(input_tokens=20, output_tokens=10)),
        bridge.RESPONSE.validate_python(previous["attribution_corrected-baseline/response.json"]),
    ]
    iterator = iter(responses)
    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        response = next(iterator)
        assert response.model == environ["LLM_MODEL"]
        write_new_json(directory / "result.json", dict(state="complete", transport_id=transport_id))
        return response
    monkeypatch.setattr(bridge, "run_child", child)
    def settings(model):
        return SimpleNamespace(model=model, base_url="https://open.bigmodel.cn/api/paas/v4", api_key="offline-only")
    provider = RunScopedRoleReceiptedProviderFactory(generator_settings=settings("glm-5.3-flash"),
        reviewer_settings=settings("glm-5.3"), transport_root=tmp_path)("case")
    def send(request):
        provider.chat(request)
        return provider.last_exchange
    workflow = RoleReviewWorkflow(send)
    initial = workflow.evaluate(source)
    assert initial.verdict is EvaluationVerdict.NEEDS_REVISION
    draft = workflow.revise(RevisionRequest(source.player_summary, source.deterministic_report,
        source.knowledge, source.report, initial))
    final = workflow.evaluate(replace(source, report=draft.report))
    assert final.verdict is EvaluationVerdict.PASS
    return tmp_path / "case", frozen, source, corrected.report, responses


def test_global_receipt_accounting_preserves_interleaved_models(recorded_revision):
    directory, _, _, _, responses = recorded_revision
    summary = qualification.summarize_role_calls(directory)
    assert summary["reserved_calls"] == summary["completed_calls"] == 3
    assert summary["unknown_usage_calls"] == summary["observed_unaccepted_calls"] == 0
    assert [c["role"] for c in summary["calls"]] == ["review", "revision", "review"]
    assert [c["model"] for c in summary["calls"]] == ["glm-5.3", "glm-5.3-flash", "glm-5.3"]
    assert summary["input_tokens"] == sum(r.usage.input_tokens for r in responses)
    assert summary["output_tokens"] == sum(r.usage.output_tokens for r in responses)


def test_replay_requires_actual_revision_and_final_review(recorded_revision):
    directory, frozen, source, corrected, _ = recorded_revision
    calls = qualification.read_role_calls(directory)
    accepted = qualification.replay_case(frozen, source, calls)
    assert accepted["final_report_sha256"] == digest(corrected)
    assert len(accepted["journals_sha256"]) == 2 and len(accepted["artifact_sha256"]) == 3
    with pytest.raises(ValueError, match="role_qualification_missing_actual_call"):
        qualification.replay_case(frozen, source, calls[:1])
    with pytest.raises(ValueError, match="role_qualification_missing_actual_call"):
        qualification.replay_case(frozen, source, calls[:2])
    with pytest.raises(ValueError, match="role_qualification_unused_actual_call"):
        qualification.replay_case(frozen, source, calls + [calls[-1]])


def test_replay_rejects_request_content_drift_even_if_receipt_hash_is_replaced(recorded_revision):
    directory, frozen, source, _, _ = recorded_revision
    calls = qualification.read_role_calls(directory)
    first = calls[0]["request"]
    changed = replace(first, messages=(replace(first.messages[0], content="changed policy"), *first.messages[1:]))
    calls[0] = dict(calls[0], request=changed)
    with pytest.raises(ValueError, match="role_qualification_replayed_request_mismatch"):
        qualification.replay_case(frozen, source, calls)


@pytest.mark.parametrize("file,field,value,error", [
    ("call-001.json", "ordinal", True, "ordinal_mismatch"),
    ("call-001.json", "model", "glm-5.3-flash", "model_mismatch"),
    ("call-001.json", "request_sha256", "0" * 64, "request_mismatch"),
    ("call-result-001.json", "response_sha256", "0" * 64, "result_mismatch"),
    ("review/stream-001/reservation.json", "ordinal", 2, "reservation_mismatch"),
    ("review/stream-001/reservation.json", "model", "glm-5.3-flash", "reservation_mismatch"),
    ("review/stream-001/result.json", "transport_id", "other", "terminal_mismatch"),
])
def test_receipt_mutation_is_rejected(recorded_revision, file, field, value, error):
    directory = recorded_revision[0]
    path = directory / file
    data = json.loads(path.read_text(encoding="utf-8"))
    data[field] = value
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        qualification.read_role_calls(directory)


def test_orphan_result_is_not_counted_as_another_completed_call(recorded_revision):
    directory = recorded_revision[0]
    (directory / "call-result-004.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="role_receipt_orphan_result"):
        qualification.summarize_role_calls(directory)


def test_incomplete_call_preserves_observed_or_unknown_usage(recorded_revision):
    directory, _, _, _, responses = recorded_revision
    (directory / "call-result-003.json").unlink()
    partial = qualification.summarize_role_calls(directory)
    assert partial["completed_calls"] == 2 and partial["observed_unaccepted_calls"] == 1
    assert partial["input_tokens"] == sum(r.usage.input_tokens for r in responses)
    (directory / "review/response-003.json").unlink()
    unknown = qualification.summarize_role_calls(directory)
    assert unknown["unknown_usage_calls"] == 1 and unknown["observed_unaccepted_calls"] == 0
    assert unknown["input_tokens"] == sum(r.usage.input_tokens for r in responses[:2])
    progress = bridge.CapacityBridgeObservation(state="failed", input_tokens=12, output_tokens=8)
    (directory / "review/stream-003/progress.json").write_text(progress.model_dump_json(), encoding="utf-8")
    observed = qualification.summarize_role_calls(directory)
    assert observed["unknown_usage_calls"] == 0 and observed["observed_unaccepted_calls"] == 1
    assert observed["input_tokens"] == sum(r.usage.input_tokens for r in responses[:2]) + 12


def test_comparison_preserves_glm_inputs_and_prepares_real_flash_sdk_wire():
    plan, requests = preparation.prepare_comparison()
    saved = json.loads(preparation.PAIR_EVIDENCE.read_text(encoding="utf-8"))["original_json_contents"]
    assert len(plan["cells"]) == 2 and not plan["paid_execution_authorized"]
    for cell in plan["cells"]:
        assert json.loads(requests[cell["id"]]) == saved[cell["id"] + "/request.json"]
        wire = cell["sdk_body"]
        assert wire["model"] == "glm-5.3-flash" and wire["reasoning_effort"] == "high"
        assert wire["stream"] is True
        assert "expected_host_only" not in json.dumps(wire)
    assert plan["proposed_diagnostic_budget"]["max_calls"] == 2
    assert plan["proposed_diagnostic_budget"]["total_token_reservation"] == sum(
        c["input_reservation"] + c["output_cap"] for c in plan["cells"])


def test_product_budget_prices_the_reassessment_path_with_three_glm_reviews():
    budget = preparation.bounded_product_estimate()
    assert budget["worst_legal_role_path"] == ["generation", "review", "review", "revision", "review"]
    assert budget["max_calls"] == 5 and budget["max_tokens"] == 401920 and budget["max_seconds"] == 900
    assert Decimal(budget["estimated_uncached_cny"]) == Decimal("4.5088768")
    assert budget["hard_billing_cap"] is False


@pytest.mark.parametrize("composition", ["native", "flash-glm-review"])
def test_product_execute_rejects_before_source_env_or_factory(composition, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("live execution gate allowed preparation or provider construction")
    monkeypatch.setattr(product, "prepare", forbidden)
    monkeypatch.setattr(product, "RunScopedReceiptedProviderFactory", forbidden)
    monkeypatch.setattr(product, "RunScopedRoleReceiptedProviderFactory", forbidden)
    with pytest.raises(ValueError, match="native_product_semantic_qualification_required"):
        product.run(SimpleNamespace(execute=True, composition=composition))

@pytest.fixture
def first_case_evidence(tmp_path, monkeypatch, prepared):
    plan, _ = prepared
    frozen, source = qualification.frozen_cases()[0][0]
    previous = json.loads(preparation.PAIR_EVIDENCE.read_text(encoding="utf-8"))["original_json_contents"]
    response = bridge.RESPONSE.validate_python(previous["attribution_corrected-baseline/response.json"])
    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        write_new_json(directory / "result.json", dict(state="complete", transport_id=transport_id))
        return response
    monkeypatch.setattr(bridge, "run_child", child)
    def settings(model):
        return SimpleNamespace(model=model, base_url="https://open.bigmodel.cn/api/paas/v4", api_key="offline-only")
    provider = RunScopedRoleReceiptedProviderFactory(generator_settings=settings("glm-5.3-flash"),
        reviewer_settings=settings("glm-5.3"), transport_root=tmp_path)("first")
    provider.chat(RoleReviewWorkflow.make_request(qualification.review.native.build_inputs(source)))
    calls = qualification.read_role_calls(tmp_path / "first")
    replayed = qualification.replay_case(frozen, source, calls)
    host = dict(candidate_sha256=digest(compact(plan["identity"])), input_sha256=frozen["input_sha256"],
        initial_request_sha256=calls[0]["binding"]["request_sha256"], **replayed,
        semantic_acceptance=True, reviewer="offline-test-fixture",
        source_review="Synthetic structural test only; does not qualify current model behavior.")
    rows = deepcopy(plan["cases"])
    rows[0].update(transport_directory="first", host_review_file="host-review.json")
    # A valid first control must proceed to the second control, never qualify 15.
    rows[1]["input_sha256"] = "0" * 64
    result = dict(qualification_version=qualification.VERSION, identity=plan["identity"],
        plan_sha256=digest(compact(plan)), cases=rows)
    return tmp_path, result, host


@pytest.mark.parametrize("field,value", [
    ("final_report_sha256", "0" * 64),
    ("artifact_sha256", []),
    ("semantic_acceptance", False),
    ("source_review", ""),
])
def test_host_approval_is_bound_to_actual_source_report_journals_and_receipts(first_case_evidence, field, value):
    root, result, host = first_case_evidence
    host[field] = value
    path = root / "host-review.json"
    path.write_text(json.dumps(host), encoding="utf-8")
    result["cases"][0]["host_review_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="role_qualification_host_review_binding_mismatch"):
        qualification.validate_qualification(result, evidence_root=root)


def test_valid_first_case_does_not_skip_remaining_fourteen(first_case_evidence):
    root, result, host = first_case_evidence
    path = root / "host-review.json"
    path.write_text(json.dumps(host), encoding="utf-8")
    result["cases"][0]["host_review_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="role_qualification_case_identity_mismatch"):
        qualification.validate_qualification(result, evidence_root=root)
