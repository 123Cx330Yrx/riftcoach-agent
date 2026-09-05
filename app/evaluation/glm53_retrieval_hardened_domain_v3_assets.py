"""No-I/O admission for the fresh GLM-5.3 retrieval hardened V3 assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from app.agent.context import CANDIDATE_CONTEXT_SAFETY_POLICY_V1
from app.rag.coaching_query import POLICY_ID as RETRIEVAL_POLICY_ID

from .domain_e2e import (
    DomainDatasetRole,
    load_domain_dataset,
    validate_domain_dataset_usage,
)
from .glm53_bounded_revision_budget import (
    V3_CASE_MAX_CALLS,
    V3_DOMAIN_MAX_CALLS,
)
from .glm53_bounded_revision_budget_reachability import (
    ALGORITHM_VERSION,
    load_v3_budget_reachability_report,
)
from .glm53_flash_candidate_profile import (
    MAX_OUTPUT_TOKENS,
    MODEL,
    PROVIDER_ID,
    REQUEST_POLICY_ID,
    REQUEST_POLICY_VERSION,
)
from .prompt_context_identity import (
    build_prompt_context_snapshot_for_cases,
    case_context_sha256,
    load_prompt_context_snapshot,
)
from .provider_domain_plan import load_domain_case_input_plan
from .provider_domain_production import CANDIDATE_QUALITY_HARDENING_VERSION


PROTOCOL_PATH = Path(
    "data/evaluation/glm53_flash_retrieval_hardened_domain_protocol_v3.json"
)
DATASET_PATH = Path("data/evaluation/glm53_flash_retrieval_hardened_domain_heldout_v3.json")
INPUT_PLAN_PATH = Path(
    "data/evaluation/glm53_flash_retrieval_hardened_domain_v3_input_plan.json"
)
SNAPSHOT_PATH = Path(
    "data/evaluation/contracts/glm53_flash_retrieval_hardened_context_v3.json"
)
BUDGET_REPORT_PATH = Path("data/evaluation/contracts/glm53_flash_retrieval_hardened_v3_budget_reachability.json")
PROTOCOL_ID = "glm53-flash-retrieval-hardened-domain-observation-v3"
PROTOCOL_VERSION = "3.1.0"
DATASET_ID = "glm53-flash-retrieval-hardened-domain-heldout-v3"
DATASET_VERSION = "3.1.0"
SNAPSHOT_ID = "glm53-flash-retrieval-hardened-context-v3"
QUALITY_HARDENING_VERSION = CANDIDATE_QUALITY_HARDENING_VERSION
EVALUATION_DIAGNOSTICS_VERSION = "body-free-evaluation-diagnostics-v1"
RETRIEVAL_CASE_MAX_TOKENS = 205_000
RETRIEVAL_DOMAIN_MAX_TOKENS = 613_000
CASE_IDS = (
    "retrieval_short_survival_83",
    "retrieval_explicit_economy_89",
    "retrieval_injection_boundary_97",
)

_HISTORICAL_PLAN_PATHS = (
    Path("data/evaluation/glm53_flash_low_profile_domain_v1_1_input_plan.json"),
    Path("data/evaluation/glm53_flash_hardened_domain_v2_input_plan.json"),
    Path("data/evaluation/glm53_flash_hardened_domain_v3_input_plan.json"),
)

Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RetrievalHardenedDomainV3Protocol(_FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    protocol_id: Literal[PROTOCOL_ID] = PROTOCOL_ID
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    retrieval_policy_id: Literal[RETRIEVAL_POLICY_ID]
    quality_hardening: Literal[True]
    retrieval_hardening: Literal[True]
    provider_id: Literal[PROVIDER_ID] = PROVIDER_ID
    model: Literal[MODEL] = MODEL
    request_policy_id: Literal[REQUEST_POLICY_ID] = REQUEST_POLICY_ID
    request_policy_version: Literal[REQUEST_POLICY_VERSION] = (
        REQUEST_POLICY_VERSION
    )
    quality_hardening_version: Literal[QUALITY_HARDENING_VERSION] = (
        QUALITY_HARDENING_VERSION
    )
    evaluation_diagnostics_version: Literal[EVALUATION_DIAGNOSTICS_VERSION] = (
        EVALUATION_DIAGNOSTICS_VERSION
    )
    budget_algorithm_version: Literal[ALGORITHM_VERSION] = ALGORITHM_VERSION
    budget_report_sha256: Sha256Text
    reasoning_effort: Literal["low"] = "low"
    max_output_tokens: Literal[MAX_OUTPUT_TOKENS] = MAX_OUTPUT_TOKENS
    sdk_max_retries: Literal[0] = 0
    max_revisions: Literal[1] = 1
    minimum_evidence_sources: Literal[1] = 1
    case_max_calls: Literal[V3_CASE_MAX_CALLS] = V3_CASE_MAX_CALLS
    domain_max_calls: Literal[V3_DOMAIN_MAX_CALLS] = V3_DOMAIN_MAX_CALLS
    case_max_tokens: Literal[RETRIEVAL_CASE_MAX_TOKENS] = RETRIEVAL_CASE_MAX_TOKENS
    domain_max_tokens: Literal[RETRIEVAL_DOMAIN_MAX_TOKENS] = RETRIEVAL_DOMAIN_MAX_TOKENS
    stop_on_first_unsafe: Literal[True] = True
    body_free_receipt: Literal[True] = True


class GLM53RetrievalHardenedDomainV3AssetAdmission(_FrozenModel):
    """Public-safe identities for V3; no question or marker text is exposed."""

    schema_version: Literal["1.0"] = "1.0"
    admission_id: NonBlankText = "glm53-retrieval-hardened-domain-v3-assets-admission"
    protocol_id: Literal[PROTOCOL_ID] = PROTOCOL_ID
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    retrieval_policy_id: Literal[RETRIEVAL_POLICY_ID] = RETRIEVAL_POLICY_ID
    quality_hardening: Literal[True] = True
    retrieval_hardening: Literal[True] = True
    dataset_id: Literal[DATASET_ID] = DATASET_ID
    dataset_version: Literal[DATASET_VERSION] = DATASET_VERSION
    snapshot_id: Literal[SNAPSHOT_ID] = SNAPSHOT_ID
    request_policy_id: Literal[REQUEST_POLICY_ID] = REQUEST_POLICY_ID
    request_policy_version: Literal[REQUEST_POLICY_VERSION] = (
        REQUEST_POLICY_VERSION
    )
    quality_hardening_version: Literal[QUALITY_HARDENING_VERSION] = (
        QUALITY_HARDENING_VERSION
    )
    evaluation_diagnostics_version: Literal[EVALUATION_DIAGNOSTICS_VERSION] = (
        EVALUATION_DIAGNOSTICS_VERSION
    )
    budget_algorithm_version: Literal[ALGORITHM_VERSION] = ALGORITHM_VERSION
    budget_report_sha256: Sha256Text
    budget_report_file_sha256: Sha256Text
    snapshot_sha256: Sha256Text
    case_ids: tuple[NonBlankText, ...]
    forbidden_marker_sha256: tuple[Sha256Text, ...]
    artifact_sha256: tuple[Sha256Text, ...]
    rules_frozen: Literal[True] = True
    external_provider_calls: Literal[0] = 0
    admitted: Literal[True] = True

    @model_validator(mode="after")
    def validate_identity(self) -> "GLM53RetrievalHardenedDomainV3AssetAdmission":
        if self.case_ids != CASE_IDS:
            raise ValueError("retrieval hardened V3 case order is not canonical")
        if len(self.artifact_sha256) != 7:
            raise ValueError("retrieval hardened V3 admission must bind seven artifacts")
        if len(set(self.artifact_sha256)) != len(self.artifact_sha256):
            raise ValueError("retrieval hardened V3 artifact digests must be unique")
        if len(set(self.forbidden_marker_sha256)) != len(
            self.forbidden_marker_sha256
        ):
            raise ValueError("retrieval hardened V3 marker digests must be unique")
        return self

    @property
    def protocol_file_sha256(self) -> str:
        return self.artifact_sha256[0]

    @property
    def dataset_file_sha256(self) -> str:
        return self.artifact_sha256[1]

    @property
    def input_plan_file_sha256(self) -> str:
        return self.artifact_sha256[2]

    @property
    def snapshot_file_sha256(self) -> str:
        return self.artifact_sha256[3]

    @property
    def summary_fixture_sha256(self) -> str:
        return self.artifact_sha256[5]

    @property
    def report_fixture_sha256(self) -> str:
        return self.artifact_sha256[6]


def admit_retrieval_hardened_domain_v3_assets(
    *,
    project_root: str | Path,
    confirm_rules_frozen: bool = False,
    protocol_path: str | Path = PROTOCOL_PATH,
    dataset_path: str | Path = DATASET_PATH,
    input_plan_path: str | Path = INPUT_PLAN_PATH,
    snapshot_path: str | Path = SNAPSHOT_PATH,
    budget_report_path: str | Path = BUDGET_REPORT_PATH,
) -> GLM53RetrievalHardenedDomainV3AssetAdmission:
    """Cross-check fresh V3 bytes and contracts without Provider construction."""

    if confirm_rules_frozen is not True:
        raise RuntimeError("held-out asset admission requires frozen-rule confirmation")
    root = Path(project_root).resolve()
    protocol_file = _inside(root, protocol_path)
    dataset_file = _inside(root, dataset_path)
    plan_file = _inside(root, input_plan_path)
    snapshot_file = _inside(root, snapshot_path)
    budget_file = _inside(root, budget_report_path)

    protocol = RetrievalHardenedDomainV3Protocol.model_validate_json(
        protocol_file.read_bytes()
    )
    budget = load_v3_budget_reachability_report(budget_file)
    if (
        protocol.budget_report_sha256 != budget.report_sha256
        or protocol.case_max_calls != budget.case_max_calls
        or protocol.domain_max_calls != budget.domain_max_calls
        or protocol.case_max_tokens != budget.case_token_limit
        or protocol.domain_max_tokens != budget.domain_token_limit
    ):
        raise ValueError("retrieval hardened V3 protocol does not match the budget proof")

    dataset = load_domain_dataset(dataset_file)
    validate_domain_dataset_usage(
        dataset,
        DomainDatasetRole.HELD_OUT,
        confirm_rules_frozen=True,
    )
    if (dataset.dataset_id, dataset.dataset_version) != (
        DATASET_ID,
        DATASET_VERSION,
    ):
        raise ValueError("unexpected retrieval hardened V3 Dataset identity")
    if tuple(row.case_id for row in dataset.cases) != CASE_IDS:
        raise ValueError("retrieval hardened V3 Dataset case IDs drifted")
    if any(
        row.requirements.minimum_evidence_sources
        != protocol.minimum_evidence_sources
        or row.requirements.maximum_provider_calls != protocol.case_max_calls
        or row.requirements.maximum_total_tokens != protocol.case_max_tokens
        or row.requirements.minimum_evaluation_score != 85
        or not all((
            row.requirements.require_fact_check,
            row.requirements.require_citation_check,
            row.requirements.require_injection_check,
            row.requirements.require_validated_evaluation,
        ))
        or not row.expect_task_success
        or row.requirements.allowed_terminal_statuses != ("published",)
        for row in dataset.cases
    ):
        raise ValueError("retrieval hardened V3 Dataset quality or resource walls drifted")

    snapshot = load_prompt_context_snapshot(snapshot_file)
    if (snapshot.snapshot_id, snapshot.snapshot_sha256) != (
        SNAPSHOT_ID,
        dataset.contract_snapshot.prompt_context_snapshot_sha256,
    ):
        raise ValueError("retrieval hardened V3 Dataset and Context snapshot identities differ")
    plan = load_domain_case_input_plan(
        plan_file,
        project_root=root,
        dataset=dataset,
        expected_max_revisions=1,
    )
    if (
        plan.artifact.schema_version != "1.1"
        or plan.artifact.sdk_max_retries != 0
        or plan.artifact.max_revisions != 1
        or plan.artifact.prompt_context_snapshot_id != SNAPSHOT_ID
        or plan.artifact.prompt_context_snapshot_sha256 != snapshot.snapshot_sha256
    ):
        raise ValueError("retrieval hardened V3 input plan revision or Context contract drifted")
    if (
        plan.artifact.request_policy_id != REQUEST_POLICY_ID
        or plan.artifact.request_policy_version != REQUEST_POLICY_VERSION
        or plan.artifact.quality_hardening is not True
        or plan.artifact.retrieval_hardening is not True
    ):
        raise ValueError("retrieval hardened V3 input plan must bind candidate retrieval policy")
    expected_commitments = tuple(
        (row.case_id, row.context_sha256)
        for row in plan.artifact.case_context_commitments
    )
    actual_commitments = tuple(
        (row.case_id, case_context_sha256(row)) for row in snapshot.case_contexts
    )
    if expected_commitments != actual_commitments:
        raise ValueError("retrieval hardened V3 input plan Context commitments differ from snapshot")
    rebuilt = build_prompt_context_snapshot_for_cases(
        skills_root=root / "skills",
        player_summary=json.loads(
            plan.player_summary_path.read_text(encoding="utf-8")
        ),
        deterministic_report=plan.deterministic_report_path.read_text(
            encoding="utf-8"
        ),
        cases=plan.artifact.cases,
        snapshot_id=SNAPSHOT_ID,
        evaluation_contract_version="1.1.0",
        policy_addendum=CANDIDATE_CONTEXT_SAFETY_POLICY_V1,
    )
    if rebuilt != snapshot:
        raise ValueError("frozen retrieval hardened V3 Context snapshot cannot be rebuilt")
    if (
        budget.input_plan_sha256 != _canonical_sha256(plan_file)
        or budget.snapshot_file_sha256 != _canonical_sha256(snapshot_file)
        or budget.snapshot_sha256 != snapshot.snapshot_sha256
        or tuple(row.case_id for row in budget.cases) != CASE_IDS
        or tuple(row.context_sha256 for row in budget.cases)
        != tuple(value for _, value in actual_commitments)
    ):
        raise ValueError("retrieval hardened V3 budget proof does not bind the frozen assets")

    markers = tuple(
        marker
        for case in plan.artifact.cases
        for marker in case.forbidden_output_markers
    )
    historical = _historical_identities(root)
    if (
        set(CASE_IDS) & historical["case_ids"]
        or {row.run_id for row in plan.artifact.cases} & historical["run_ids"]
        or {row.user_utterance for row in plan.artifact.cases}
        & historical["utterances"]
        or set(markers) & historical["markers"]
        or {
            plan.artifact.player_summary.sha256,
            plan.artifact.deterministic_report.sha256,
        }
        & historical["fixture_sha256"]
    ):
        raise ValueError("retrieval hardened V3 assets reuse consumed historical identity")
    if len(set(markers)) != len(markers):
        raise ValueError("retrieval hardened V3 forbidden markers must be unique")

    artifacts = (
        _sha256_file(protocol_file),
        _sha256_file(dataset_file),
        _sha256_file(plan_file),
        _sha256_file(snapshot_file),
        _sha256_file(budget_file),
        _sha256_file(plan.player_summary_path),
        _sha256_file(plan.deterministic_report_path),
    )
    return GLM53RetrievalHardenedDomainV3AssetAdmission(
        budget_report_sha256=budget.report_sha256,
        budget_report_file_sha256=artifacts[4],
        snapshot_sha256=snapshot.snapshot_sha256,
        case_ids=CASE_IDS,
        forbidden_marker_sha256=tuple(_sha256_text(value) for value in markers),
        artifact_sha256=artifacts,
    )


def _historical_identities(root: Path) -> dict[str, set[str]]:
    result = {
        "case_ids": set(),
        "run_ids": set(),
        "utterances": set(),
        "markers": set(),
        "fixture_sha256": set(),
    }
    for relative in _HISTORICAL_PLAN_PATHS:
        payload = json.loads(_inside(root, relative).read_text(encoding="utf-8"))
        result["fixture_sha256"].update(
            {
                payload["player_summary"]["sha256"],
                payload["deterministic_report"]["sha256"],
            }
        )
        for case in payload["cases"]:
            result["case_ids"].add(case["case_id"])
            result["run_ids"].add(case["run_id"])
            result["utterances"].add(case["user_utterance"])
            result["markers"].update(case["forbidden_output_markers"])
    return result


def _inside(root: Path, value: str | Path) -> Path:
    path = Path(value)
    resolved = (path if path.is_absolute() else root / path).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise FileNotFoundError("V3 asset must be a file inside the repository")
    return resolved


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "CASE_IDS",
    "DATASET_ID",
    "DATASET_PATH",
    "DATASET_VERSION",
    "EVALUATION_DIAGNOSTICS_VERSION",
    "GLM53RetrievalHardenedDomainV3AssetAdmission",
    "RetrievalHardenedDomainV3Protocol",
    "INPUT_PLAN_PATH",
    "PROTOCOL_ID",
    "PROTOCOL_PATH",
    "QUALITY_HARDENING_VERSION",
    "SNAPSHOT_ID",
    "SNAPSHOT_PATH",
    "admit_retrieval_hardened_domain_v3_assets",
]
