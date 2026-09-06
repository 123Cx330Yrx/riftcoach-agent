"""Observe the actual opt-in product Runtime, not a second domain executor."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.evaluation.coach_product_acceptance import (
    AcceptanceAssets, admit_assets, compile_case, composition, digest, json_bytes,
)
from app.evaluation.domain_e2e import DomainCandidate, DomainCandidateCase, FailureCode, LayerVerdict, evaluate_domain_candidate
from app.evaluation.glm53_low_profile_protocol import GLM53LowProfileProtocolReport
from app.evaluation.coach_report import EvaluationResponseModelV11
from app.evaluation.provider_domain_production import _evaluation_observation, _FACT_ISSUE_CATEGORIES
from app.harness.models import ArtifactKind
from app.harness.runtime import _SAFE_FAILURE_CODES
from app.harness.store import FileRunStore
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.coach_contract import COACH_CONTRACT, GROUNDED_COACH_CONTRACT
from app.runtime.store import RuntimeTraceStore


CASE_IDS = ("coach246_recent", "coach246_survival", "coach246_economy", "coach246_memory")
REQUIRED_CI_JOBS = {"pytest", "postgres-migrations", "packaging-smoke"}


class RealEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    implementation_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    assets_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    public_ci_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    protocol_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    protocol_calls: Literal[3] = 3
    protocol_input_tokens: int = Field(ge=0)
    protocol_output_tokens: int = Field(ge=0)


def verify_real_evidence(assets, *, implementation_sha, ci, protocol_bytes, now=None):
    """Only same-code, successful public CI and subsequent real protocol qualify."""
    jobs = ci.get("jobs", [])
    if (ci.get("headSha") != implementation_sha or ci.get("status") != "completed"
            or ci.get("conclusion") != "success"
            or not ci.get("url", "").startswith("https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/")
            or len(jobs) != len(REQUIRED_CI_JOBS)
            or {job.get("name") for job in jobs} != REQUIRED_CI_JOBS
            or any(job.get("status") != "completed" or job.get("conclusion") != "success" for job in jobs)):
        raise ValueError("acceptance_public_ci_mismatch")
    protocol = GLM53LowProfileProtocolReport.model_validate_json(protocol_bytes)
    ci_completed = datetime.fromisoformat(ci["updatedAt"].replace("Z", "+00:00"))
    now = now or datetime.now(timezone.utc)
    if (protocol.implementation_sha != implementation_sha or protocol.evidence_origin != "real_provider"
            or not protocol.protocol.admitted or not protocol.network_used
            or protocol.run_timestamp_utc.tzinfo is None or ci_completed.tzinfo is None
            or not ci_completed <= protocol.run_timestamp_utc <= now):
        raise ValueError("acceptance_fresh_protocol_required")
    return RealEvidence(
        implementation_sha=implementation_sha, assets_sha256=assets.sha256, public_ci_sha256=digest(ci),
        protocol_sha256=hashlib.sha256(protocol_bytes).hexdigest(),
        protocol_input_tokens=protocol.input_tokens, protocol_output_tokens=protocol.output_tokens,
    )


class EvaluationResponseDiagnostic(BaseModel):
    """Local response classification only: never a quote, report or reasoning."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    call_ordinal: int = Field(ge=1, le=36)
    finish_reason: Literal["stop", "length", "tool_calls", "content_filter", "other"] | None
    schema_valid: bool
    verdict: Literal["pass", "needs_revision", "fail"] | None = None
    issue_count: int | None = Field(default=None, ge=0)
    consistency_error: Literal["pass_with_issues", "revision_without_issues"] | None = None

    @model_validator(mode="after")
    def validate_classification(self):
        if not self.schema_valid:
            if any(value is not None for value in (self.verdict, self.issue_count, self.consistency_error)):
                raise ValueError("invalid_evaluation_has_no_parsed_fields")
            return self
        if self.verdict is None or self.issue_count is None:
            raise ValueError("valid_evaluation_requires_parsed_fields")
        expected = ("pass_with_issues" if self.verdict == "pass" and self.issue_count else
                    "revision_without_issues" if self.verdict == "needs_revision" and not self.issue_count else None)
        if self.consistency_error != expected:
            raise ValueError("evaluation_consistency_diagnostic_mismatch")
        return self


class ProductCaseDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    citation_markers_seen: int = Field(ge=0)
    unknown_citation_markers: int = Field(ge=0)
    evaluation_artifact_count: int = Field(ge=0, le=2)
    harness_failure_code: str | None = None
    trace_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluation_responses: tuple[EvaluationResponseDiagnostic, ...] = ()

    @model_validator(mode="after")
    def validate_safe_diagnostics(self):
        if self.harness_failure_code is not None and self.harness_failure_code not in _SAFE_FAILURE_CODES:
            raise ValueError("acceptance_unknown_failure_code")
        if self.unknown_citation_markers > self.citation_markers_seen:
            raise ValueError("acceptance_citation_counts_mismatch")
        return self


class CaseReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    case_id: Literal["coach246_recent", "coach246_survival", "coach246_economy", "coach246_memory"]
    status: Literal["passed", "failed", "skipped"]
    observation: DomainCandidateCase | None = None
    failure_codes: tuple[FailureCode | Literal["incomplete_evidence"], ...] = ()
    diagnostics: ProductCaseDiagnostics | None = Field(default=None, exclude_if=lambda value: value is None)


class AcceptanceReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1.0", "1.1"] = "1.1"
    acceptance_id: Literal["coach-product-rq246-v1"] = "coach-product-rq246-v1"
    assets_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_origin: Literal["offline_fake", "real_provider"]
    real_evidence: RealEvidence | None = None
    cases: tuple[CaseReceipt, ...]
    passed: bool
    provider_calls: int = Field(ge=0, le=36)
    observed_input_tokens: int = Field(ge=0)
    observed_output_tokens: int = Field(ge=0)
    candidate_registered: Literal[False] = False
    production_admitted: Literal[False] = False

    @model_validator(mode="after")
    def verify_counts(self):
        if tuple(row.case_id for row in self.cases) != CASE_IDS:
            raise ValueError("acceptance_case_identity_mismatch")
        stopped = False
        for row in self.cases:
            if self.schema_version == "1.0" and row.diagnostics is not None:
                raise ValueError("legacy_acceptance_has_no_diagnostics")
            if (row.status == "skipped") != stopped:
                raise ValueError("acceptance_must_stop_after_first_failure")
            if row.status == "skipped":
                if row.observation is not None or row.failure_codes or row.diagnostics is not None:
                    raise ValueError("skipped_case_has_no_observation")
                continue
            if row.observation is None or row.observation.case_id != row.case_id:
                raise ValueError("acceptance_observation_required")
            if self.schema_version == "1.1" and row.diagnostics is None:
                raise ValueError("acceptance_diagnostics_required")
            if row.diagnostics:
                ordinals = tuple(d.call_ordinal for d in row.diagnostics.evaluation_responses)
                if (len(ordinals) > 4 or ordinals != tuple(sorted(set(ordinals)))
                        or any(i > row.observation.provider_calls for i in ordinals)):
                    raise ValueError("acceptance_evaluation_call_ordinals_mismatch")
            if (row.status == "passed") != (not row.failure_codes):
                raise ValueError("acceptance_failure_codes_mismatch")
            stopped = row.status == "failed"
        observations = [row.observation for row in self.cases if row.observation is not None]
        if (self.passed != all(row.status == "passed" for row in self.cases)
                or self.provider_calls != sum(row.provider_calls for row in observations)
                or self.observed_input_tokens != sum(row.input_tokens or 0 for row in observations)
                or self.observed_output_tokens != sum(row.output_tokens or 0 for row in observations)):
            raise ValueError("acceptance_totals_mismatch")
        if (self.evidence_origin == "real_provider") != (self.real_evidence is not None):
            raise ValueError("acceptance_evidence_origin_mismatch")
        if self.real_evidence and self.real_evidence.assets_sha256 != self.assets_sha256:
            raise ValueError("acceptance_real_assets_mismatch")
        return self


def observe_product_result(runs_root, result, case, *, request, context_commitment, diagnostics_sink=None):
    contract = next((c for c in (COACH_CONTRACT, GROUNDED_COACH_CONTRACT)
                     if c.snapshot() == request.policy.coach_contract), None)
    if contract is None:
        raise ValueError("acceptance_unknown_coach_contract")
    trace = RuntimeTraceStore(runs_root, result.run_id).read_trace(result.trace_reference)
    if (trace.run_id != case["case_id"] or trace.policy != request.policy
            or trace.identity.coach_contract != contract.snapshot()
            or trace.identity.skill_version != "0.3.0" or trace.identity.prompt_profile_version != contract.descriptor()["program_version"]
            or trace.identity.provider_id != "zhipu" or trace.identity.provider_model != "glm-5.3-flash"
            or trace.publication_status != result.publication_status
            or trace.runtime_status != result.runtime_status or trace.terminal_reason != result.terminal_reason):
        raise ValueError("acceptance_trace_identity_mismatch")
    store = FileRunStore(runs_root, result.run_id)
    manifest = store.read_manifest() if store.manifest_path.exists() else None
    records = manifest.artifacts if manifest else []
    trace_records = {(r.kind, r.relative_path, r.sha256, r.producer, r.schema_version) for r in trace.artifacts}
    expected_records = {(r["kind"], r["path"], r["sha256"], r["producer"], r["schema_version"]) for r in records}
    if trace_records != expected_records:
        raise ValueError("acceptance_artifact_trace_mismatch")
    bodies = {row["path"]: store.read_artifact(row).decode("utf-8") for row in records}
    def artifact(kind):
        return [bodies[row["path"]] for row in records if row["kind"] == kind.value]
    evidence_rows = artifact(ArtifactKind.RETRIEVAL_EVIDENCE)
    if len(evidence_rows) > 1:
        raise ValueError("acceptance_duplicate_evidence")
    evidence = json.loads(evidence_rows[0]) if evidence_rows else {}
    source_ids = tuple(evidence.get("source_ids", ()))
    final = artifact(ArtifactKind.FINAL_REPORT)
    drafts = artifact(ArtifactKind.REVISED_REPORT) or artifact(ArtifactKind.COACH_DRAFT)
    report = (final or drafts or [""])[-1]
    if manifest and trace.publication_status is not None and manifest.status.value != trace.publication_status.value:
        raise ValueError("acceptance_terminal_mismatch")
    if final and (len(final) != 1 or result.output is None or result.output.report.strip() != final[0].strip()
                  or tuple(result.output.evidence_source_ids) != source_ids):
        raise ValueError("acceptance_publication_mismatch")
    if trace.publication_status is not None and (trace.publication_status.value == "published") != bool(final):
        raise ValueError("acceptance_final_artifact_mismatch")
    diagnostics, evaluation = _evaluation_observation(manifest, store) if manifest else (None, None)
    if final and (evaluation is None or result.output.evaluation_score != evaluation["score"]):
        raise ValueError("acceptance_evaluation_mismatch")
    signals = [event.signal for event in trace.events]
    terminated = [signal for signal in signals if signal.kind == "agent_run_terminated"]
    agent = terminated[-1] if terminated else None
    citations = {row["citation_id"] for row in evidence.get("citations", ()) if row.get("source_id") in source_ids}
    cited = set(re.findall(r"\[(K\d+)\]", report))
    if diagnostics_sink is not None:
        diagnostics_sink(ProductCaseDiagnostics(
            citation_markers_seen=len(cited), unknown_citation_markers=len(cited.difference(citations)),
            evaluation_artifact_count=len(artifact(ArtifactKind.EVALUATION_RESULT)),
            harness_failure_code=manifest.failure_code if manifest and manifest.failure_code in _SAFE_FAILURE_CODES else None,
            trace_sha256=result.trace_reference.sha256,
        ))
    observation = DomainCandidateCase(
        case_id=case["case_id"], provider_calls=trace.usage.provider_calls_attempted,
        normalized_response_count=trace.usage.provider_responses_observed,
        safe_provider_error_code="provider_error" if any(s.kind == "provider_call_failed" for s in signals) else None,
        agent_status=agent.status.value if agent else None, agent_stop_reason=agent.stop_reason.value if agent else None,
        proposed_tool_names=tuple(sorted({s.tool_name for s in signals if s.kind == "tool_call_started"})),
        successful_tool_names=tuple(sorted({s.tool_name for s in signals if s.kind == "tool_call_completed" and s.success})),
        evidence_source_ids=tuple("sha256_" + hashlib.sha256(s.encode()).hexdigest() for s in source_ids),
        revision_count=manifest.revision_count if manifest else 0,
        **({"evaluation_diagnostics": diagnostics} if diagnostics else {}),
        fact_check_passed=None if evaluation is None else not any(i["category"] in _FACT_ISSUE_CATEGORIES for i in evaluation["issues"]),
        citation_check_passed=bool(cited) and cited.issubset(citations) if report else None,
        injection_check_passed=not any(marker in report for marker in case["forbidden_output_markers"]) if report else None,
        evaluation_validated=evaluation is not None, evaluation_score=evaluation["score"] if evaluation else None,
        terminal_status=trace.publication_status.value if trace.publication_status else None,
        terminal_reason=trace.terminal_reason if trace.publication_status else None,
        latency_ms=trace.elapsed_ms, input_tokens=trace.usage.input_tokens, output_tokens=trace.usage.output_tokens,
        provenance_sha256=digest({"trace": result.trace_reference.sha256, "context": context_commitment}),
    )
    return observation


def adjudicate(assets, case_index, observation, *, real=False):
    dataset = assets.dataset.model_copy(update={"case_count": 1, "cases": (assets.dataset.cases[case_index],)})
    candidate = DomainCandidate(
        schema_version="1.2", candidate_id="coach246-product-observation",
        candidate_kind="real_provider_recorded" if real else "offline_executable",
        dataset_id=dataset.dataset_id, dataset_version=dataset.dataset_version, contract_snapshot=dataset.contract_snapshot,
        external_provider_calls=observation.provider_calls if real else 0, case_count=1, cases=(observation,),
    )
    result = evaluate_domain_candidate(dataset, candidate).cases[0]
    passed = result.task_succeeded and result.layers.resources.verdict is LayerVerdict.PASS
    return passed, tuple(code.value for code in result.failure_codes) or (() if passed else ("incomplete_evidence",))


def validate_receipt(receipt: AcceptanceReceipt, assets: AcceptanceAssets):
    """Recompute outcomes from observations; a hand-edited pass flag is not evidence."""
    receipt = AcceptanceReceipt.model_validate_json(receipt.model_dump_json())
    if receipt.assets_sha256 != assets.sha256:
        raise ValueError("acceptance_receipt_assets_mismatch")
    for index, row in enumerate(receipt.cases):
        if row.status == "skipped":
            continue
        passed, failures = adjudicate(assets, index, row.observation, real=receipt.real_evidence is not None)
        if (row.status == "passed") != passed or tuple(row.failure_codes) != failures:
            raise ValueError("acceptance_receipt_outcome_mismatch")
    return receipt


def run_acceptance(project_root: Path, *, provider, real_evidence: RealEvidence | None = None, on_case=None) -> AcceptanceReceipt:
    assets = admit_assets(project_root)
    if real_evidence and real_evidence.assets_sha256 != assets.sha256:
        raise ValueError("acceptance_real_assets_mismatch")
    COACH_CONTRACT.require_provider(provider)
    provider = provider if isinstance(provider, _CallCounter) else _CallCounter(provider)
    root = composition(project_root)
    rows = []
    stopped = False
    # These are ephemeral product artifacts, not public receipts. A new private
    # namespace avoids collisions; all bodies are removed even on failure.
    with tempfile.TemporaryDirectory(prefix="riftcoach-246-") as temp:
        for index, case in enumerate(assets.inputs["cases"]):
            if stopped:
                rows.append(CaseReceipt(case_id=case["case_id"], status="skipped"))
                if on_case:
                    on_case(rows[-1])
                continue
            request, builder, memory = compile_case(root, assets.inputs, case)
            commitment = assets.manifest["context_snapshot"]["contexts"][index]
            if digest(request.model_dump(mode="json")) != commitment["request_sha256"]:
                raise ValueError("acceptance_request_drift")
            # The same Builder used by the product must produce the frozen
            # Context at execution time, before the first Provider call.
            original_build = builder.build
            def checked_build(*args, **kwargs):
                bundle = original_build(*args, **kwargs)
                if digest(asdict(bundle)) != commitment["context_sha256"]:
                    raise ValueError("acceptance_context_drift")
                if memory and memory.manifest_hashes != commitment["memory_manifest_sha256s"]:
                    raise ValueError("acceptance_memory_drift")
                return bundle
            builder.build = checked_build
            runtime = root.build_offline_coach_runtime(
                runs_root=temp, provider=provider, context_builder=builder,
                knowledge_provider=LocalHybridKnowledgeProvider.from_directory(project_root / "data/rag_docs"),
            )
            calls_before = provider.calls
            result = runtime.run(request)
            collected = []
            observation = observe_product_result(temp, result, case, request=request,
                                                 context_commitment=commitment, diagnostics_sink=collected.append)
            case_diagnostics = collected[0].model_copy(update={"evaluation_responses": tuple(
                row.model_copy(update={"call_ordinal": row.call_ordinal - calls_before})
                for row in provider.evaluation_responses if row.call_ordinal > calls_before
            )})
            passed, failures = adjudicate(assets, index, observation, real=real_evidence is not None)
            rows.append(CaseReceipt(case_id=case["case_id"], status="passed" if passed else "failed",
                                    observation=observation, failure_codes=failures, diagnostics=case_diagnostics))
            if on_case:
                on_case(rows[-1])
            stopped = not passed
    observations = [row.observation for row in rows if row.observation]
    receipt = AcceptanceReceipt(
        assets_sha256=assets.sha256, evidence_origin="real_provider" if real_evidence else "offline_fake",
        real_evidence=real_evidence, cases=tuple(rows), passed=not stopped,
        provider_calls=sum(row.provider_calls for row in observations),
        observed_input_tokens=sum(row.input_tokens or 0 for row in observations),
        observed_output_tokens=sum(row.output_tokens or 0 for row in observations),
    )
    return validate_receipt(receipt, assets)


class _CallCounter:
    """No new retries or budgets; retain only usage if a later observer fails."""

    def __init__(self, provider):
        self.provider = provider
        self.calls = self.input_tokens = self.output_tokens = 0
        self.evaluation_responses = []

    def __getattr__(self, name):
        return getattr(self.provider, name)

    def chat(self, request):
        self.calls += 1
        response = self.provider.chat(request)
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens
        if request.response_contract is not None and request.response_contract.name == "coach_evaluation":
            reason = response.finish_reason
            if reason is not None and reason not in {"stop", "length", "tool_calls", "content_filter"}:
                reason = "other"
            values = {"call_ordinal": self.calls, "finish_reason": reason, "schema_valid": False}
            try:
                evaluation = EvaluationResponseModelV11.model_validate_json(response.content or "", strict=True)
            except ValueError:
                pass
            else:
                error = None
                if evaluation.verdict == "pass" and evaluation.issues:
                    error = "pass_with_issues"
                if evaluation.verdict == "needs_revision" and not evaluation.issues:
                    error = "revision_without_issues"
                values.update(schema_valid=True, verdict=evaluation.verdict,
                              issue_count=len(evaluation.issues), consistency_error=error)
            self.evaluation_responses.append(EvaluationResponseDiagnostic(**values))
        return response


def _write_new(path, value):
    with path.open("xb") as stream:
        stream.write(json_bytes(value))


def execute_once(project_root: Path, *, real_evidence, provider_factory):
    """Reserve a fixed identity before loading credentials or creating a client."""
    assets = admit_assets(project_root)
    if not isinstance(real_evidence, RealEvidence) or real_evidence.assets_sha256 != assets.sha256:
        raise ValueError("acceptance_real_evidence_required")
    state = project_root / "data/runs/coach_product_rq246_v1_acceptance"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.mkdir(exist_ok=False)
    _write_new(state / "reservation.json", real_evidence.model_dump(mode="json"))
    counter = None
    try:
        counter = _CallCounter(provider_factory())
        receipt = run_acceptance(project_root, provider=counter, real_evidence=real_evidence,
                                 on_case=lambda row: _write_new(state / f"{row.case_id}.json", row.model_dump(mode="json")))
        _write_new(state / "receipt.json", receipt.model_dump(mode="json"))
        return receipt
    except BaseException:
        # Keep the consumed identity even after interruption. Never serialize
        # exception text: upstream errors may include credentials or bodies.
        _write_new(state / "failure.json", {
            "status": "interrupted_or_failed", "retry_allowed": False,
            "provider_calls": counter.calls if counter else 0,
            "observed_input_tokens": counter.input_tokens if counter else 0,
            "observed_output_tokens": counter.output_tokens if counter else 0,
            "evaluation_responses": [row.model_dump(mode="json") for row in counter.evaluation_responses] if counter else [],
        })
        raise
