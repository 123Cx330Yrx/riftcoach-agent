"""Offline engineering checks, not GLM quality evidence or real receipts."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import socket

import pytest

from app.evaluation.coach_product_acceptance import (
    ASSET_PATH, admit_assets, build_assets, compile_case, composition, digest, summary_from_inputs,
)
from app.evaluation.coach_product_acceptance_runner import (
    AcceptanceReceipt, CASE_IDS, execute_once, run_acceptance, validate_receipt, verify_real_evidence,
)
from app.evaluation.glm53_low_profile_protocol import run_glm53_low_profile_protocol
from app.providers.errors import ProviderResponseError
from tests.test_glm53_low_profile_protocol import _successful_provider
from tests.test_offline_coach_runtime import CoachProvider

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)
SHA = "a" * 40


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("RQ-246 tests must remain offline")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@pytest.fixture
def isolated_root(tmp_path):
    for folder in (ASSET_PATH, Path("examples/runtime_profiles/flash_v2"), Path("data/rag_docs")):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    return tmp_path


class ProductStub(CoachProvider):
    def chat(self, request):
        response = super().chat(request)
        if response.content and not request.response_contract:
            response = replace(response, content=response.content.replace("两局", "五局"))
        return response


def provider(**kwargs):
    return ProductStub(provider_name="zhipu", model_name="glm-5.3-flash", **kwargs)


def evidence_inputs():
    # A locally scripted report is relabelled ONLY to exercise strict parser
    # branches; it is never written, submitted or reported as real evidence.
    protocol = run_glm53_low_profile_protocol(provider=_successful_provider(), implementation_sha=SHA, now=lambda: NOW)
    raw = protocol.model_dump(mode="json")
    raw.update(evidence_origin="real_provider", explicit_real_call_confirmed=True, network_used=True)
    ci = {"headSha": SHA, "status": "completed", "conclusion": "success",
          "url": "https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/246",
          "updatedAt": (NOW - timedelta(minutes=1)).isoformat(),
          "jobs": [{"name": name, "status": "completed", "conclusion": "success"}
                   for name in ("pytest", "postgres-migrations", "packaging-smoke")]}
    return ci, raw


def real_evidence(root):
    ci, protocol = evidence_inputs()
    return verify_real_evidence(admit_assets(root), implementation_sha=SHA, ci=ci,
                                protocol_bytes=json.dumps(protocol).encode(), now=NOW)


def test_frozen_assets_rebuild_and_synthetic_facts_are_consistent():
    assets = admit_assets(ROOT)
    assert assets.sha256 == build_assets(ROOT).sha256
    assert tuple(c.case_id for c in assets.dataset.cases) == CASE_IDS
    assert assets.dataset.calibration_excluded
    assert assets.manifest["budget"]["maximum_calls"] == 36
    assert assets.manifest["budget"]["maximum_total_tokens"] == 4 * 9 * (64000 + 4096)
    summary = summary_from_inputs(assets.inputs)
    assert summary["recent_summary"]["games_analyzed"] == 5
    assert summary["recent_summary"]["wins"] == 2
    for row in summary["matches"]:
        assert len(row["death_times"]) == row["deaths"]
        assert sum(int(t.split(":")[0]) < 15 for t in row["death_times"]) == row["deaths_before_15"]
    for case in assets.dataset.cases:
        assert case.requirements.minimum_evaluation_score == 85
        assert case.requirements.minimum_evidence_sources == 1
        assert case.requirements.maximum_latency_ms is None


@pytest.mark.parametrize("target", ["input", "dataset", "context", "budget", "corpus", "program", "marker"])
def test_asset_drift_is_rejected_before_provider(isolated_root, target):
    file = isolated_root / ASSET_PATH / "manifest.json"
    value = json.loads(file.read_text(encoding="utf-8"))
    if target in {"input", "marker"}:
        file = isolated_root / ASSET_PATH / "inputs.json"
        value = json.loads(file.read_text(encoding="utf-8"))
        if target == "input":
            value["matches"][0]["cs_per_min"] = 7.7
        else:
            value["cases"][-1]["forbidden_output_markers"] = ["different"]
    elif target == "dataset":
        value["dataset"]["cases"][0]["requirements"]["minimum_evaluation_score"] = 0
    elif target == "context":
        value["context_snapshot"]["contexts"][0]["context_sha256"] = "0" * 64
    elif target == "budget":
        value["budget"]["maximum_calls"] = 999
    elif target == "corpus":
        file = next((isolated_root / "data/rag_docs").glob("*.md"))
        file.write_text(file.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
    elif target == "program":
        file = isolated_root / "examples/runtime_profiles/flash_v2/prompt_programs/recent-form-review/manifest.json"
        value = json.loads(file.read_text(encoding="utf-8"))
        value["program_sha256"] = "0" * 64
    if target != "corpus":
        file.write_text(json.dumps(value), encoding="utf-8")
    stub = provider()
    with pytest.raises(ValueError):
        run_acceptance(isolated_root, provider=stub)
    assert not stub.requests


def test_four_actual_product_runs_and_safe_receipt():
    stub = provider()
    receipt = run_acceptance(ROOT, provider=stub)
    assert receipt.passed
    assert receipt.provider_calls == len(stub.requests) == 14
    assert receipt.evidence_origin == "offline_fake" and receipt.real_evidence is None
    assert not receipt.production_admitted and not receipt.candidate_registered
    assert [r.observation.revision_count for r in receipt.cases] == [1, 0, 0, 0]
    assert all(r.observation.evaluation_score == 95 for r in receipt.cases)
    assert all(r.observation.fact_check_passed and r.observation.citation_check_passed for r in receipt.cases)
    assert all(r.observation.provenance_sha256 and r.observation.evidence_source_ids for r in receipt.cases)
    assert all(r.max_tokens == 4096 and r.timeout_s <= 45 for r in stub.requests)
    encoded = receipt.model_dump_json()
    for forbidden in ("较多", "五局", "RC_COACH_246_OVERRIDE", "合成测试英雄", "controlled pass"):
        assert forbidden not in encoded
    assert validate_receipt(AcceptanceReceipt.model_validate_json(encoded), admit_assets(ROOT)) == receipt
    first_requests = [r for r in stub.requests if r.tools and len(r.messages) == 2]
    assert len(first_requests) == 4
    for request in first_requests:
        assert "RC_COACH_246_OVERRIDE" not in request.messages[0].content
        assert "minimum_evaluation_score" not in request.messages[-1].content
        assert "forbidden_output_markers" not in request.messages[-1].content
    assert "RC_COACH_246_OVERRIDE" in first_requests[-1].messages[-1].content


@pytest.mark.parametrize("failure", ["quality", "citation", "missing_source", "provider"])
def test_first_failure_stops_later_cases(failure):
    class FailedProvider(ProductStub):
        def chat(self, request):
            if failure == "provider":
                self.requests.append(request)
                raise ProviderResponseError(provider="zhipu", code="timeout")
            response = super().chat(request)
            if failure == "missing_source" and len(self.requests) == 1:
                return self._text("No retrieval")
            if failure == "citation" and response.content and not request.response_contract:
                return replace(response, content=response.content.replace("[K1]", "[K999]"))
            return response
    stub = FailedProvider(provider_name="zhipu", model_name="glm-5.3-flash",
                          second_verdict="fail" if failure == "quality" else "pass")
    receipt = run_acceptance(ROOT, provider=stub)
    assert not receipt.passed
    assert [r.status for r in receipt.cases] == ["failed", "skipped", "skipped", "skipped"]
    assert receipt.provider_calls == len(stub.requests)
    assert receipt.cases[0].failure_codes
    assert not receipt.production_admitted


def test_memory_attack_is_detected_even_when_fake_evaluator_returns_high_score():
    class LeakyProvider(ProductStub):
        def chat(self, request):
            response = super().chat(request)
            if (response.content and not request.response_contract
                    and any("RC_COACH_246_OVERRIDE" in (m.content or "") for m in request.messages)):
                return replace(response, content=response.content + "\nRC_COACH_246_OVERRIDE")
            return response
    receipt = run_acceptance(ROOT, provider=LeakyProvider(provider_name="zhipu", model_name="glm-5.3-flash"))
    assert [r.status for r in receipt.cases] == ["passed", "passed", "passed", "failed"]
    assert receipt.cases[-1].observation.injection_check_passed is False
    assert "injection_resistance_failed" in receipt.cases[-1].failure_codes


@pytest.mark.parametrize("mutation", ["sha", "fake", "old", "future", "failed_ci", "missing_job", "protocol_count"])
def test_real_evidence_requires_exact_successful_ci_and_fresh_strict_protocol(mutation):
    ci, raw = evidence_inputs()
    if mutation == "sha":
        ci["headSha"] = "b" * 40
    elif mutation == "fake":
        raw.update(evidence_origin="offline_fake", network_used=False, explicit_real_call_confirmed=False)
    elif mutation == "old":
        raw["run_timestamp_utc"] = (NOW - timedelta(hours=1)).isoformat()
    elif mutation == "future":
        raw["run_timestamp_utc"] = (NOW + timedelta(hours=1)).isoformat()
    elif mutation == "failed_ci":
        ci["jobs"][0]["conclusion"] = "failure"
    elif mutation == "missing_job":
        ci["jobs"].pop()
    elif mutation == "protocol_count":
        raw["provider_call_count"] = 2
    with pytest.raises(ValueError):
        verify_real_evidence(admit_assets(ROOT), implementation_sha=SHA, ci=ci,
                             protocol_bytes=json.dumps(raw).encode(), now=NOW)


def test_reservation_precedes_factory_and_is_not_reusable_after_failure(isolated_root):
    evidence = real_evidence(isolated_root)
    count = []
    def failing_factory():
        assert (isolated_root / "data/runs/coach_product_rq246_v1_acceptance/reservation.json").is_file()
        count.append(1)
        raise RuntimeError("secret upstream content must never persist")
    with pytest.raises(RuntimeError):
        execute_once(isolated_root, real_evidence=evidence, provider_factory=failing_factory)
    with pytest.raises(FileExistsError):
        execute_once(isolated_root, real_evidence=evidence, provider_factory=failing_factory)
    assert count == [1]
    failure = (isolated_root / "data/runs/coach_product_rq246_v1_acceptance/failure.json").read_text()
    assert "secret" not in failure and '"retry_allowed":false' in failure


def test_default_cli_does_not_touch_git_network_or_credentials(monkeypatch, capsys):
    from scripts import run_coach_product_acceptance as cli
    def forbidden(*args):
        raise AssertionError("preflight must not read external state")
    monkeypatch.setattr(cli, "command", forbidden)
    assert cli.main([]) == 0
    assert "network=0" in capsys.readouterr().out


def test_receipt_tampering_is_rejected():
    receipt = run_acceptance(ROOT, provider=provider())
    raw = json.loads(receipt.model_dump_json())
    raw["cases"][0]["observation"]["evaluation_score"] = 0
    with pytest.raises(ValueError, match="outcome_mismatch"):
        validate_receipt(AcceptanceReceipt.model_validate(raw), admit_assets(ROOT))
    raw = json.loads(receipt.model_dump_json())
    raw["provider_calls"] = 0
    with pytest.raises(ValueError, match="totals_mismatch"):
        AcceptanceReceipt.model_validate(raw)


def test_runtime_context_drift_never_calls_provider(monkeypatch):
    import app.evaluation.coach_product_acceptance_runner as runner
    original = runner.compile_case
    def changed(*args):
        request, builder, memory = original(*args)
        old_build = builder.build
        def bad_build(*a, **kw):
            context = old_build(*a, **kw)
            return replace(context, estimated_tokens=context.estimated_tokens + 1)
        builder.build = bad_build
        return request, builder, memory
    monkeypatch.setattr(runner, "compile_case", changed)
    stub = provider()
    receipt = run_acceptance(ROOT, provider=stub)
    assert not stub.requests
    assert not receipt.passed and receipt.cases[0].observation.provider_calls == 0


@pytest.mark.parametrize("case_index", range(4))
def test_fresh_inputs_fit_nine_call_full_usage_path(tmp_path, case_index):
    from scripts.check_glm53_report_contract_budget import _MeteredWorstPathProvider
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_LOW_CANDIDATE_PROFILE
    from app.rag.hybrid import LocalHybridKnowledgeProvider
    from app.runtime.store import RuntimeTraceStore
    class WorstPath(_MeteredWorstPathProvider):
        thinking_profile_id = ZHIPU_GLM53_FLASH_LOW_CANDIDATE_PROFILE.profile_id
        sdk_max_retries = 0
    assets = admit_assets(ROOT)
    root = composition(ROOT)
    request, builder, _ = compile_case(root, assets.inputs, assets.inputs["cases"][case_index])
    stub = WorstPath()
    result = root.build_offline_coach_runtime(
        runs_root=tmp_path, provider=stub, context_builder=builder,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(ROOT / "data/rag_docs"),
    ).run(request)
    assert len(stub.requests) == 9, result
    assert result.terminal_reason == "evaluation_failed"
    estimates = [estimate_runtime_request_input_ceiling(r) for r in stub.requests]
    assert max(estimates) <= 64000
    trace = RuntimeTraceStore(tmp_path, request.run_id).read_trace(result.trace_reference)
    assert trace.usage.input_tokens == sum(estimates)
    assert trace.usage.output_tokens == 9 * 4096
    assert sum(estimates) + 9 * 4096 <= 612864


@pytest.mark.parametrize("kind", ["retrieval_evidence", "final_report", "evaluation_result"])
def test_corrupt_product_artifacts_cannot_become_acceptance(tmp_path, kind):
    from app.evaluation.coach_product_acceptance_runner import observe_product_result
    from app.harness.store import ArtifactIntegrityError, FileRunStore
    from app.rag.hybrid import LocalHybridKnowledgeProvider
    assets = admit_assets(ROOT)
    root = composition(ROOT)
    case = assets.inputs["cases"][0]
    request, builder, _ = compile_case(root, assets.inputs, case)
    result = root.build_offline_coach_runtime(
        runs_root=tmp_path, provider=provider(), context_builder=builder,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(ROOT / "data/rag_docs"),
    ).run(request)
    store = FileRunStore(tmp_path, request.run_id)
    record = next(r for r in store.read_manifest().artifacts if r["kind"] == kind)
    (store.run_directory / record["path"]).write_text("tampered", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError):
        observe_product_result(tmp_path, result, case, request=request,
                               context_commitment=assets.manifest["context_snapshot"]["contexts"][0])


def test_interruption_preserves_partial_results_and_call_count(isolated_root, monkeypatch):
    import app.evaluation.coach_product_acceptance_runner as runner
    original = runner.observe_product_result
    def interrupt(runs, result, case, **kwargs):
        if case["case_id"] == "coach246_survival":
            raise KeyboardInterrupt("private interruption text")
        return original(runs, result, case, **kwargs)
    monkeypatch.setattr(runner, "observe_product_result", interrupt)
    stub = provider()
    with pytest.raises(KeyboardInterrupt):
        execute_once(isolated_root, real_evidence=real_evidence(isolated_root), provider_factory=lambda: stub)
    state = isolated_root / "data/runs/coach_product_rq246_v1_acceptance"
    assert (state / "coach246_recent.json").is_file()
    assert not (state / "receipt.json").exists()
    raw = json.loads((state / "failure.json").read_text())
    assert raw["provider_calls"] == len(stub.requests) == 8
    assert "private" not in json.dumps(raw)
