"""Candidate-only binding for the versioned coaching retrieval guidance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.agent.context import CANDIDATE_CONTEXT_SAFETY_POLICY_V1
from app.evaluation.prompt_context_identity import (
    PromptContextSnapshot,
    build_prompt_context_snapshot_for_cases,
    case_context_sha256,
)
from app.evaluation.provider_domain_plan import LoadedDomainCaseInputPlan
from app.rag.coaching_query import COACHING_QUERY_GUIDANCE_V1, POLICY_ID

GUIDANCE_ID = "coaching-query-guidance-v1"
GUIDANCE_SHA256 = hashlib.sha256(COACHING_QUERY_GUIDANCE_V1.encode("utf-8")).hexdigest()
GUIDANCE_POLICY_ID = POLICY_ID


def _canonical_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def build_guided_context_snapshot(
    *, project_root: str | Path, input_plan: LoadedDomainCaseInputPlan
) -> PromptContextSnapshot:
    """Rebuild the exact candidate Context identity; never trust a caller hash."""

    artifact = input_plan.artifact
    if artifact.schema_version != "1.1":
        raise ValueError("guided candidate requires a schema 1.1 input plan")
    if artifact.dataset_id.startswith("glm53-flash-retrieval-hardened-domain-heldout"):
        raise ValueError("guided candidate cannot reuse a held-out dataset")
    if not (artifact.quality_hardening and artifact.retrieval_hardening):
        raise ValueError("guided candidate requires quality and retrieval hardening")
    if artifact.request_policy_id is None or artifact.request_policy_version is None:
        raise ValueError("guided candidate requires an explicit request policy")
    if artifact.max_revisions != 1:
        raise ValueError("guided candidate requires one bounded revision")
    root = Path(project_root).resolve()
    summary = input_plan.player_summary_path.read_bytes()
    report = input_plan.deterministic_report_path.read_bytes()
    if _canonical_digest(input_plan.player_summary_path) != artifact.player_summary.sha256:
        raise ValueError("guided candidate player summary drifted")
    if _canonical_digest(input_plan.deterministic_report_path) != artifact.deterministic_report.sha256:
        raise ValueError("guided candidate deterministic report drifted")
    snapshot = build_prompt_context_snapshot_for_cases(
        skills_root=root / "skills",
        player_summary=json.loads(summary.decode("utf-8")),
        deterministic_report=report.replace(b"\r\n", b"\n").decode("utf-8"),
        cases=artifact.cases,
        snapshot_id=artifact.prompt_context_snapshot_id or "",
        evaluation_contract_version="1.1.0",
        policy_addendum="\n\n".join((CANDIDATE_CONTEXT_SAFETY_POLICY_V1, COACHING_QUERY_GUIDANCE_V1)),
    )
    if snapshot.snapshot_id != artifact.prompt_context_snapshot_id:
        raise ValueError("guided candidate snapshot ID mismatch")
    if snapshot.snapshot_sha256 != artifact.prompt_context_snapshot_sha256:
        raise ValueError("guided candidate Context snapshot drifted")
    committed = tuple(row.context_sha256 for row in artifact.case_context_commitments)
    if committed != tuple(case_context_sha256(row) for row in snapshot.case_contexts):
        raise ValueError("guided candidate case Context commitment drifted")
    return snapshot


def require_guided_candidate(
    *, project_root: str | Path, input_plan: LoadedDomainCaseInputPlan
) -> PromptContextSnapshot:
    """Public candidate gate used by future real runners before Provider I/O."""

    return build_guided_context_snapshot(project_root=project_root, input_plan=input_plan)
