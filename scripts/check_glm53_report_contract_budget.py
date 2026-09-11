"""No-network budget proof through the opt-in report-contract development entry."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.evaluation.glm53_bounded_revision_budget_reachability import (
    ALGORITHM_VERSION, V3CaseBudgetReachability, Sha256Text,
    _WorstPathProvider, estimate_runtime_request_input_ceiling, measure_request_envelope,
)
from app.evaluation.glm53_flash_candidate_profile import REQUEST_POLICY_ID, REQUEST_POLICY_VERSION
from app.evaluation.glm53_guided_candidate import GUIDANCE_ID, GUIDANCE_SHA256, require_guided_candidate
from app.evaluation.glm53_report_contract import REPORT_CONTRACT_ID, REPORT_CONTRACT_SHA256
from app.providers.models import TokenUsage
from app.rag.coaching_query import COACHING_QUERY_GUIDANCE_V1, POLICY_ID
from scripts.probe_glm53_development_retrieval import DEVELOPMENT_SCENARIOS, development_plan, observe

REPORT_PATH = Path("data/evaluation/contracts/glm53_report_contract_development_budget_v1.json")
SCENARIOS = tuple(DEVELOPMENT_SCENARIOS)
CASE_TOKEN_LIMIT = 205_000


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CaseProof(_Frozen):
    scenario: Literal["recent_review", "survival_adjustment", "economy_adjustment"]
    plan_sha256: Sha256Text
    snapshot_sha256: Sha256Text
    envelope: V3CaseBudgetReachability
    settled_input_tokens: int = Field(gt=0)
    settled_output_tokens: Literal[36864] = 9 * 4096
    settled_total_tokens: int = Field(gt=0)
    token_margin: int = Field(ge=0)
    calls_used: Literal[9] = 9
    revision_count: Literal[1] = 1
    terminal_reason: Literal["evaluation_failed"] = "evaluation_failed"
    # At the actual Provider seam (not nominal profile values).
    request_timeouts_s: tuple[float, ...]
    output_limits: tuple[int, ...]

    @model_validator(mode="after")
    def validate_case(self):
        if self.envelope.case_id != f"development_report_contract_{self.scenario}_v1":
            raise ValueError("case identity mismatch")
        if self.settled_input_tokens != sum(row.measured_local_units * 2 for row in self.envelope.requests):
            raise ValueError("full input envelope was not settled")
        if self.settled_total_tokens != self.settled_input_tokens + self.settled_output_tokens:
            raise ValueError("settled token total mismatch")
        if self.token_margin != CASE_TOKEN_LIMIT - self.envelope.reserved_total_tokens:
            raise ValueError("case budget margin mismatch")
        if self.request_timeouts_s != (45.0,) * 9 or self.output_limits != (4096,) * 9:
            raise ValueError("actual request policy drifted")
        return self


class ReportContractBudgetProof(_Frozen):
    schema_version: Literal["1.0"] = "1.0"
    proof_id: Literal["glm53-report-contract-development-budget-v1"] = "glm53-report-contract-development-budget-v1"
    scope: Literal["development_not_admission"] = "development_not_admission"
    algorithm_version: Literal[ALGORITHM_VERSION] = ALGORITHM_VERSION
    provider_id: Literal["zhipu"] = "zhipu"
    model: Literal["glm-5.3-flash"] = "glm-5.3-flash"
    report_contract_id: Literal[REPORT_CONTRACT_ID] = REPORT_CONTRACT_ID
    report_contract_sha256: Sha256Text = REPORT_CONTRACT_SHA256
    guidance_id: Literal[GUIDANCE_ID] = GUIDANCE_ID
    guidance_sha256: Sha256Text = GUIDANCE_SHA256
    retrieval_policy_id: Literal[POLICY_ID] = POLICY_ID
    request_policy_id: Literal[REQUEST_POLICY_ID] = REQUEST_POLICY_ID
    request_policy_version: Literal[REQUEST_POLICY_VERSION] = REQUEST_POLICY_VERSION
    case_token_limit: Literal[205000] = CASE_TOKEN_LIMIT
    cases: tuple[CaseProof, ...]
    external_provider_calls: Literal[0] = 0
    network_used: Literal[False] = False
    report_sha256: Sha256Text

    @model_validator(mode="after")
    def validate_proof(self):
        if tuple(row.scenario for row in self.cases) != SCENARIOS:
            raise ValueError("three distinct ordered development scenarios required")
        if self.report_contract_sha256 != REPORT_CONTRACT_SHA256 or self.guidance_sha256 != GUIDANCE_SHA256:
            raise ValueError("policy digest mismatch")
        if self.report_sha256 != _digest(self.model_dump(mode="json", exclude={"report_sha256"})):
            raise ValueError("proof digest mismatch")
        return self


class _MeteredWorstPathProvider(_WorstPathProvider):
    """Reuse the old nine-step fixture, but bill full input and output reservations."""

    def chat(self, request):
        response = super().chat(request)
        # The development fixture is two games, not the old V3 five-game fixture.
        content = response.content.replace("五局合成样本", "两局合成样本") if response.content else None
        return replace(response, content=content, usage=TokenUsage(
            input_tokens=estimate_runtime_request_input_ceiling(request), output_tokens=4096,
        ))


def build_report_contract_budget_proof(project_root: Path = ROOT) -> ReportContractBudgetProof:
    root = project_root.resolve()
    rows = []
    for scenario in SCENARIOS:
        plan = development_plan(root, guided=True, scenario=scenario, report_contract_id=REPORT_CONTRACT_ID)
        snapshot = require_guided_candidate(project_root=root, input_plan=plan, report_contract_id=REPORT_CONTRACT_ID)
        provider = _MeteredWorstPathProvider()
        with tempfile.TemporaryDirectory(prefix="glm53-report-budget-") as directory:
            result = observe(provider, root=root, runs_root=Path(directory), scenario=scenario,
                             retrieval_guidance=COACHING_QUERY_GUIDANCE_V1, report_contract_id=REPORT_CONTRACT_ID)
        observation, resources = result["observation"], result["resources"]
        if (result["report_contract_id"] != REPORT_CONTRACT_ID
                or result["report_contract_sha256"] != REPORT_CONTRACT_SHA256
                or result["retrieval_guidance_id"] != GUIDANCE_ID
                or result["retrieval_guidance_sha256"] != GUIDANCE_SHA256
                or result["plan_sha256"] != plan.execution_plan.plan_sha256):
            raise ValueError("observed development contract identity mismatch")
        if (result["execution_error"] is not None or resources["stop_code"] is not None
                or observation is None or observation["terminal_reason"] != "evaluation_failed"
                or observation["revision_count"] != 1 or resources["calls_used"] != 9
                or observation["normalized_response_count"] != 9
                or not result["evaluation_history"]["complete"]):
            raise ValueError("new contract did not reach the nine-call bounded revision path")
        if any(request.temperature != 1.0 or request.top_p != 0.95
               or request.metadata.get("evaluation_policy_id") != REQUEST_POLICY_ID
               or request.metadata.get("evaluation_policy_version") != REQUEST_POLICY_VERSION
               for request in provider.requests):
            raise ValueError("new contract actual request policy mismatch")
        requests = tuple(measure_request_envelope(request, ordinal=index)
                         for index, request in enumerate(provider.requests, 1))
        envelope = V3CaseBudgetReachability(
            case_id=plan.execution_plan.case_ids[0],
            context_sha256=plan.artifact.case_context_commitments[0].context_sha256,
            requests=requests,
            estimated_input_token_ceiling=sum(row.estimated_input_token_ceiling for row in requests),
            output_token_reservation=sum(row.output_token_reservation for row in requests),
            reserved_total_tokens=sum(row.reserved_total_tokens for row in requests),
        )
        rows.append(CaseProof(
            scenario=scenario, plan_sha256=plan.execution_plan.plan_sha256,
            snapshot_sha256=snapshot.snapshot_sha256, envelope=envelope,
            settled_input_tokens=resources["input_tokens"], settled_total_tokens=resources["total_tokens"],
            settled_output_tokens=resources["output_tokens"], calls_used=resources["calls_used"],
            revision_count=observation["revision_count"], terminal_reason=observation["terminal_reason"],
            token_margin=CASE_TOKEN_LIMIT - envelope.reserved_total_tokens,
            request_timeouts_s=tuple(row.timeout_s for row in provider.requests),
            output_limits=tuple(row.max_tokens for row in provider.requests),
        ))
    draft = ReportContractBudgetProof.model_construct(cases=tuple(rows), report_sha256="0" * 64)
    payload = draft.model_dump(mode="json", exclude={"report_sha256"})
    return ReportContractBudgetProof.model_validate({**payload, "report_sha256": _digest(payload)})


def canonical_proof_bytes(proof: ReportContractBudgetProof) -> bytes:
    return (proof.model_dump_json(indent=2) + "\n").encode("utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print proof instead of checking frozen evidence")
    args = parser.parse_args(argv)
    proof = build_report_contract_budget_proof()
    if args.json:
        print(canonical_proof_bytes(proof).decode(), end="")
    else:
        frozen = ReportContractBudgetProof.model_validate_json((ROOT / REPORT_PATH).read_bytes())
        if proof != frozen:
            raise ValueError("frozen development budget proof drifted")
        print(json.dumps({"status": "passed", "external_provider_calls": 0,
                          "case_token_limit": CASE_TOKEN_LIMIT,
                          "reserved_total_tokens": [row.envelope.reserved_total_tokens for row in proof.cases]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
