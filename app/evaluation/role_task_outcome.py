"""Supplementary offline task judgments; never a replacement qualification gate.

Replay binds human source assessments to actual requests, reviews and edits.
It cannot decide semantic truth itself or prove fresh IO/continuous task time.
Those limits are explicit even when every supplied assessment is acceptable.
"""
from typing import Literal
import json

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import RESPONSE
from app.evaluation.role_qualification import candidate_identity, frozen_cases, replay_case

VERSION = "role-task-outcome-observation-v1"


def stage_identity(stage):
    # Journals are stored with sorted keys. Semantic stage bindings must be
    # stable across that JSON write/read, unlike original transport byte hashes.
    return digest(json.dumps({k: stage[k] for k in ('stage','report','journal')},
        sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',',':')))


DefectKind = Literal[
    "missed_error", "false_positive", "unsupported_explanation", "wrong_correction",
    "unsupported_source", "internal_contradiction", "wrong_final_report",
    "correct_content_lost", "identity_or_goal_changed",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Defect(Strict):
    kind: DefectKind
    detail: str = Field(min_length=1)


class StageAssessment(Strict):
    stage: Literal["initial", "revision", "final"]
    stage_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer: str = Field(min_length=1)
    source_review: str = Field(min_length=1)
    accepted: bool
    defects: list[Defect]

    @model_validator(mode="after")
    def consistent(self):
        if not self.reviewer.strip() or not self.source_review.strip():
            raise ValueError("task_outcome_empty_source_review")
        if self.accepted != (not self.defects):
            raise ValueError("task_outcome_defects_contradict_acceptance")
        if any(not defect.detail.strip() for defect in self.defects):
            raise ValueError("task_outcome_empty_defect")
        return self


class ReportAssessment(Strict):
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer: str = Field(min_length=1)
    source_review: str = Field(min_length=1)
    facts_and_sources_correct: bool
    correct_content_preserved: bool
    identity_and_goal_preserved: bool
    true_errors_fixed: bool

    @model_validator(mode="after")
    def nonempty(self):
        if not self.reviewer.strip() or not self.source_review.strip():
            raise ValueError("task_outcome_empty_report_review")
        return self


class Assessment(Strict):
    version: Literal["role-task-outcome-observation-v1"]
    key: str
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    replay_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    stages: list[StageAssessment]
    final_report: ReportAssessment


def may_continue_initial(assessment, *, expected_initial, target_and_correction_valid=False):
    """Prospective diagnostic allowance; a failed review never becomes accepted.

    Only a correctly targeted error with safe correction intent and solely an
    incidental explanation defect may reach the existing editor. False positives,
    misses, unsafe correction intent and all other defects still stop the batch.
    This decision is recorded outside the model input and cannot publish a task.
    """
    host = StageAssessment.model_validate(assessment)
    if host.stage != "initial" or expected_initial not in ("accept", "reject"):
        raise ValueError("task_outcome_initial_decision_invalid")
    return host.accepted or (
        expected_initial == "reject" and target_and_correction_valid is True
        and all(d.kind == "unsupported_explanation" for d in host.defects))


def prepare_observation(key, calls, *, backend=None):
    """Rebuild current original-set workflow, without issuing any request.

    Calls may include an explicitly historical injection for a diagnostic. This
    API consequently never certifies IO provenance, whole-task time or admission.
    Invalid initial decisions/protocols and incomplete/rebound sequences fail in
    the existing replay; a final score alone cannot bypass that reconstruction.
    """
    cases = {f["key"]: (f, source) for f, source in frozen_cases()[0]}
    if key not in cases:
        raise ValueError("task_outcome_unknown_original_case")
    frozen, source = cases[key]
    if (not calls or len(calls) > 5
            or any(c.get("response") is None for c in calls)):
        raise ValueError("task_outcome_incomplete_calls")
    tokens = sum(c["response"].usage.input_tokens + c["response"].usage.output_tokens for c in calls)
    if tokens > 401920:
        raise ValueError("task_outcome_replay_token_limit")
    replay = replay_case if backend is None else backend.replay_case
    identity = candidate_identity() if backend is None else backend.candidate_identity()
    replayed = replay(frozen, source, calls, include_stage_evidence=True)
    # Bind supplied response content AND usage, even in a diagnostic without
    # raw files. This prevents reusing a host assessment after in-memory edits;
    # only read_role_calls can additionally certify the original receipt files.
    response_sha256 = [digest(RESPONSE.dump_json(c['response']).decode()) for c in calls]
    binding = dict(version=VERSION, key=key,
        candidate_sha256=digest(compact(identity)),
        input_sha256=frozen["input_sha256"], replay_sha256=digest(compact(dict(
            replayed["bindings"], provided_response_sha256=response_sha256))))
    stages = [dict(stage=s["stage"], stage_sha256=stage_identity(s)) for s in replayed["stages"]]
    return dict(binding=binding, stages=stages, replayed=replayed,
        expected_initial=frozen["expected_initial"], replay_tokens=tokens)


def assess_task_outcome(key, calls, assessment, *, backend=None):
    """Validate bindings and keep reviewer quality separate from final outcome.

    Accepted means the supplied, bound full-source host judgment says accepted;
    the validator does not replace that review with string or numeric heuristics.
    Every negative judgment and its concrete defect is retained in the result.
    """
    observed = prepare_observation(key, calls, backend=backend)
    host = Assessment.model_validate(assessment)
    if any(getattr(host, k) != v for k, v in observed["binding"].items()):
        raise ValueError("task_outcome_assessment_binding_mismatch")
    if [dict(stage=s.stage, stage_sha256=s.stage_sha256) for s in host.stages] != observed["stages"]:
        raise ValueError("task_outcome_stage_inventory_or_binding_mismatch")
    final_sha = observed["replayed"]["bindings"]["final_report_sha256"]
    if host.final_report.report_sha256 != final_sha:
        raise ValueError("task_outcome_final_report_binding_mismatch")
    report = host.final_report
    report_accepted = all((report.facts_and_sources_correct, report.correct_content_preserved,
        report.identity_and_goal_preserved, report.true_errors_fixed))
    reviews = [s for s in host.stages if s.stage != "revision"]
    reviewer_quality = all(s.accepted for s in reviews)
    # Correct controls require the original first-pass path. The shared replay
    # already rejects an unnecessary revision, missed-error pass, and score <85.
    task_outcome = report_accepted and host.stages[-1].accepted
    if observed["expected_initial"] == "reject":
        task_outcome = task_outcome and host.stages[1].accepted
    else:
        task_outcome = task_outcome and host.stages[0].accepted
    return dict(**observed["binding"], evidence_scope="supplementary_offline_replay",
        reviewer_quality=reviewer_quality, task_outcome=task_outcome,
        final_report_sha256=final_sha, assessment=host.model_dump(),
        replay_bindings=observed["replayed"]["bindings"],
        original15_coverage_complete=False, fresh_execution_verified=False,
        continuous_task_budget_verified=False, review_controls_qualified=False,
        actual_product_task_qualified=False, production_admitted=False, execution_enabled=False)
