"""Offline request-envelope proof for the GLM-5.3 hardened V3 gate.

The proof executes the real local Agent/RAG/Harness path against a deterministic
fake Provider.  It retains only request identities and body-free size counters;
credentials, network I/O, prompts, reports, and model response bodies are never
written to the report.
"""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.agent.context import DeterministicContextSizer
from app.evaluation.coach_report import REVISER_SYSTEM_PROMPT
from app.providers.capabilities import ProviderCapabilities
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    TokenUsage,
    ToolCall,
)

from .glm53_flash_candidate_profile import (
    GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
    MAX_OUTPUT_TOKENS,
    MODEL,
    PROVIDER_ID,
    REQUEST_POLICY_ID,
    REQUEST_POLICY_VERSION,
)
from .prompt_context_identity import (
    case_context_sha256,
    load_prompt_context_snapshot,
)
from .provider_domain_experiment import DomainCaseExecutionPlan
from .provider_domain_plan import (
    DomainCaseInputPlanArtifact,
    LoadedDomainCaseInputPlan,
)
from .provider_domain_production import ProductionDomainCaseExecutor


ALGORITHM_VERSION = "deterministic-full-request-envelope-v1"
CASE_MAX_CALLS = 9
DOMAIN_MAX_CALLS = 27
INPUT_SAFETY_MULTIPLIER = 2
REPORT_PATH = Path(
    "data/evaluation/contracts/glm53_flash_hardened_v3_budget_reachability.json"
)
INPUT_PLAN_PATH = Path(
    "data/evaluation/glm53_flash_hardened_domain_v3_input_plan.json"
)
SNAPSHOT_PATH = Path(
    "data/evaluation/contracts/glm53_flash_hardened_context_v3.json"
)

_STAGES = (
    "agent_initial",
    "agent_after_tool_1",
    "agent_after_tool_2",
    "agent_after_tool_3",
    "evaluation_initial",
    "evaluation_repair_initial",
    "revision",
    "evaluation_recheck",
    "evaluation_repair_recheck",
)
_CARRYOVER_OUTPUT_COUNTS = (0, 1, 2, 3, 1, 1, 2, 1, 1)

Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
SafeIdText = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$"),
]
StageName = Literal[
    "agent_initial",
    "agent_after_tool_1",
    "agent_after_tool_2",
    "agent_after_tool_3",
    "evaluation_initial",
    "evaluation_repair_initial",
    "revision",
    "evaluation_recheck",
    "evaluation_repair_recheck",
]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class V3RequestEnvelope(_FrozenModel):
    ordinal: int = Field(ge=1, le=CASE_MAX_CALLS)
    stage: StageName
    request_sha256: Sha256Text
    message_count: int = Field(gt=0)
    message_roles: tuple[Literal["system", "user", "assistant", "tool"], ...]
    tool_count: int = Field(ge=0)
    structured_output: bool
    measured_local_units: int = Field(gt=0)
    prior_output_carryover_reservation: int = Field(ge=0)
    estimated_input_token_ceiling: int = Field(gt=0)
    output_token_reservation: Literal[MAX_OUTPUT_TOKENS] = MAX_OUTPUT_TOKENS
    reserved_total_tokens: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_envelope(self) -> "V3RequestEnvelope":
        if len(self.message_roles) != self.message_count:
            raise ValueError("message roles must match the message count")
        expected_input = (
            self.measured_local_units * INPUT_SAFETY_MULTIPLIER
            + self.prior_output_carryover_reservation
        )
        if self.estimated_input_token_ceiling != expected_input:
            raise ValueError("request input ceiling is inconsistent")
        if self.reserved_total_tokens != (
            self.estimated_input_token_ceiling + self.output_token_reservation
        ):
            raise ValueError("request total reservation is inconsistent")
        return self


class V3CaseBudgetReachability(_FrozenModel):
    case_id: SafeIdText
    context_sha256: Sha256Text
    requests: tuple[V3RequestEnvelope, ...]
    estimated_input_token_ceiling: int = Field(gt=0)
    output_token_reservation: int = Field(gt=0)
    reserved_total_tokens: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_case(self) -> "V3CaseBudgetReachability":
        if tuple(row.ordinal for row in self.requests) != tuple(
            range(1, CASE_MAX_CALLS + 1)
        ):
            raise ValueError("case requests must contain all nine ordinals")
        if tuple(row.stage for row in self.requests) != _STAGES:
            raise ValueError("case requests do not follow the V3 reachable path")
        if self.estimated_input_token_ceiling != sum(
            row.estimated_input_token_ceiling for row in self.requests
        ):
            raise ValueError("case input ceiling is inconsistent")
        if self.output_token_reservation != sum(
            row.output_token_reservation for row in self.requests
        ):
            raise ValueError("case output reservation is inconsistent")
        if self.reserved_total_tokens != sum(
            row.reserved_total_tokens for row in self.requests
        ):
            raise ValueError("case total reservation is inconsistent")
        return self


class V3BudgetReachabilityReport(_FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    algorithm_version: Literal[ALGORITHM_VERSION] = ALGORITHM_VERSION
    provider_id: Literal[PROVIDER_ID] = PROVIDER_ID
    model: Literal[MODEL] = MODEL
    request_policy_id: Literal[REQUEST_POLICY_ID] = REQUEST_POLICY_ID
    request_policy_version: Literal[REQUEST_POLICY_VERSION] = REQUEST_POLICY_VERSION
    sdk_max_retries: Literal[0] = 0
    max_revisions: Literal[1] = 1
    case_max_calls: Literal[CASE_MAX_CALLS] = CASE_MAX_CALLS
    domain_max_calls: Literal[DOMAIN_MAX_CALLS] = DOMAIN_MAX_CALLS
    input_plan_sha256: Sha256Text
    snapshot_file_sha256: Sha256Text
    snapshot_sha256: Sha256Text
    cases: tuple[V3CaseBudgetReachability, ...]
    case_token_limit: int = Field(gt=0)
    domain_token_limit: int = Field(gt=0)
    external_provider_calls: Literal[0] = 0
    report_sha256: Sha256Text

    @model_validator(mode="after")
    def validate_report(self) -> "V3BudgetReachabilityReport":
        if len(self.cases) != 3 or len({row.case_id for row in self.cases}) != 3:
            raise ValueError("V3 reachability report requires three unique cases")
        if self.case_token_limit != _round_up(
            max(row.reserved_total_tokens for row in self.cases),
            1000,
        ):
            raise ValueError("case token limit is inconsistent")
        if self.domain_token_limit != _round_up(
            sum(row.reserved_total_tokens for row in self.cases),
            1000,
        ):
            raise ValueError("domain token limit is inconsistent")
        expected = _digest_json(
            self.model_dump(mode="json", exclude={"report_sha256"})
        )
        if self.report_sha256 != expected:
            raise ValueError("report_sha256 does not match report content")
        return self


def build_v3_budget_reachability_report(
    *,
    project_root: str | Path,
    input_plan_path: str | Path = INPUT_PLAN_PATH,
    snapshot_path: str | Path = SNAPSHOT_PATH,
    retrieval_hardening: bool = False,
) -> V3BudgetReachabilityReport:
    """Trace all three worst paths locally and return only body-free evidence."""

    root = Path(project_root).resolve()
    plan_path = _inside_file(root, input_plan_path)
    snapshot_file = _inside_file(root, snapshot_path)
    loaded_plan = _load_plan(root, plan_path)
    snapshot = load_prompt_context_snapshot(snapshot_file)
    context_by_case = {
        row.case_id: case_context_sha256(row) for row in snapshot.case_contexts
    }
    if tuple(context_by_case) != loaded_plan.execution_plan.case_ids:
        raise ValueError("V3 Context case order does not match the input plan")

    cases = []
    for case_id in loaded_plan.execution_plan.case_ids:
        provider = _WorstPathProvider()
        with tempfile.TemporaryDirectory(prefix="glm53-v3-reachability-") as directory:
            observation = ProductionDomainCaseExecutor(
                project_root=root,
                input_plan=loaded_plan,
                runs_root=directory,
                request_policy=GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
                quality_hardening=True,
                retrieval_hardening=retrieval_hardening,
                max_revisions=1,
            ).execute(case_id=case_id, provider=provider)
        if (
            len(provider.requests) != CASE_MAX_CALLS
            or observation.normalized_response_count != CASE_MAX_CALLS
            or observation.revision_count != 1
            or observation.terminal_reason != "evaluation_failed"
        ):
            raise ValueError("fake V3 trace did not reach the required worst path")
        requests = tuple(
            measure_request_envelope(request, ordinal=index)
            for index, request in enumerate(provider.requests, start=1)
        )
        cases.append(
            V3CaseBudgetReachability(
                case_id=case_id,
                context_sha256=context_by_case[case_id],
                requests=requests,
                estimated_input_token_ceiling=sum(
                    row.estimated_input_token_ceiling for row in requests
                ),
                output_token_reservation=sum(
                    row.output_token_reservation for row in requests
                ),
                reserved_total_tokens=sum(
                    row.reserved_total_tokens for row in requests
                ),
            )
        )
    case_rows = tuple(cases)
    payload = {
        "schema_version": "1.0",
        "algorithm_version": ALGORITHM_VERSION,
        "provider_id": PROVIDER_ID,
        "model": MODEL,
        "request_policy_id": REQUEST_POLICY_ID,
        "request_policy_version": REQUEST_POLICY_VERSION,
        "sdk_max_retries": 0,
        "max_revisions": 1,
        "case_max_calls": CASE_MAX_CALLS,
        "domain_max_calls": DOMAIN_MAX_CALLS,
        "input_plan_sha256": _canonical_sha256(plan_path),
        "snapshot_file_sha256": _canonical_sha256(snapshot_file),
        "snapshot_sha256": snapshot.snapshot_sha256,
        "cases": [row.model_dump(mode="json") for row in case_rows],
        "case_token_limit": _round_up(
            max(row.reserved_total_tokens for row in case_rows),
            1000,
        ),
        "domain_token_limit": _round_up(
            sum(row.reserved_total_tokens for row in case_rows),
            1000,
        ),
        "external_provider_calls": 0,
    }
    return V3BudgetReachabilityReport(
        **payload,
        report_sha256=_digest_json(payload),
    )


def measure_request_envelope(
    request: ChatRequest,
    *,
    ordinal: int,
) -> V3RequestEnvelope:
    if not isinstance(request, ChatRequest):
        raise TypeError("request must be a ChatRequest")
    if not 1 <= ordinal <= CASE_MAX_CALLS:
        raise ValueError("ordinal must be between 1 and 9")
    stage = _STAGES[ordinal - 1]
    measured = _measure_full_request_units(request)
    carryover = _CARRYOVER_OUTPUT_COUNTS[ordinal - 1] * MAX_OUTPUT_TOKENS
    input_ceiling = measured * INPUT_SAFETY_MULTIPLIER + carryover
    return V3RequestEnvelope(
        ordinal=ordinal,
        stage=stage,
        request_sha256=_request_sha256(request),
        message_count=len(request.messages),
        message_roles=tuple(row.role.value for row in request.messages),
        tool_count=len(request.tools),
        structured_output=request.response_contract is not None,
        measured_local_units=measured,
        prior_output_carryover_reservation=carryover,
        estimated_input_token_ceiling=input_ceiling,
        reserved_total_tokens=input_ceiling + MAX_OUTPUT_TOKENS,
    )


def estimate_runtime_request_input_ceiling(request: ChatRequest) -> int:
    """Conservative runtime check over the actual fully materialized request."""

    if not isinstance(request, ChatRequest):
        raise TypeError("request must be a ChatRequest")
    return _measure_full_request_units(request) * INPUT_SAFETY_MULTIPLIER


def load_v3_budget_reachability_report(
    path: str | Path,
) -> V3BudgetReachabilityReport:
    return V3BudgetReachabilityReport.model_validate_json(Path(path).read_bytes())


def canonical_v3_budget_reachability_bytes(
    report: V3BudgetReachabilityReport,
) -> bytes:
    if not isinstance(report, V3BudgetReachabilityReport):
        raise TypeError("report must be a V3BudgetReachabilityReport")
    return (report.model_dump_json(indent=2) + "\n").encode("utf-8")


def _measure_full_request_units(request: ChatRequest) -> int:
    sizer = DeterministicContextSizer()
    units = sizer.estimate_messages(request.messages)
    auxiliary = {
        "tools": [
            {
                "name": row.name,
                "description": row.description,
                "input_schema": dict(row.input_schema),
            }
            for row in request.tools
        ],
        "tool_choice": request.tool_choice.value,
        "response_contract": (
            None
            if request.response_contract is None
            else {
                "name": request.response_contract.name,
                "version": request.response_contract.version,
                "strict": request.response_contract.strict,
                "json_schema": request.response_contract.schema_dict(),
            }
        ),
    }
    if request.tools or request.response_contract is not None:
        units += sizer.estimate_messages(
            (
                ChatMessage(
                    MessageRole.USER,
                    json.dumps(
                        auxiliary,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                ),
            )
        )
    return units


def _request_sha256(request: ChatRequest) -> str:
    return _digest_json(
        {
            "messages": [
                {
                    "role": row.role.value,
                    "content": row.content,
                    "reasoning_content": row.reasoning_content,
                    "tool_call_id": row.tool_call_id,
                    "name": row.name,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "name": call.name,
                            "arguments": dict(call.arguments),
                        }
                        for call in row.tool_calls
                    ],
                }
                for row in request.messages
            ],
            "tools": [
                {
                    "name": row.name,
                    "description": row.description,
                    "input_schema": dict(row.input_schema),
                }
                for row in request.tools
            ],
            "tool_choice": request.tool_choice.value,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "response_contract": (
                None
                if request.response_contract is None
                else {
                    "name": request.response_contract.name,
                    "version": request.response_contract.version,
                    "json_schema": request.response_contract.schema_dict(),
                }
            ),
            "top_p": request.top_p,
        }
    )


def _load_plan(root: Path, path: Path) -> LoadedDomainCaseInputPlan:
    artifact = DomainCaseInputPlanArtifact.model_validate_json(path.read_bytes())
    if artifact.max_revisions != 1:
        raise ValueError("V3 reachability requires exactly one revision")
    summary = _inside_file(root, artifact.player_summary.relative_path)
    report = _inside_file(root, artifact.deterministic_report.relative_path)
    if _canonical_sha256(summary) != artifact.player_summary.sha256:
        raise ValueError("V3 summary fixture digest mismatch")
    if _canonical_sha256(report) != artifact.deterministic_report.sha256:
        raise ValueError("V3 report fixture digest mismatch")
    return LoadedDomainCaseInputPlan(
        artifact=artifact,
        execution_plan=DomainCaseExecutionPlan(
            plan_id=artifact.plan_id,
            plan_version=artifact.plan_version,
            plan_sha256=_canonical_sha256(path),
            case_ids=tuple(row.case_id for row in artifact.cases),
        ),
        player_summary_path=summary,
        deterministic_report_path=report,
    )


@dataclass
class _WorstPathProvider:
    provider_name: str = PROVIDER_ID
    model_name: str = MODEL
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )
    requests: list[ChatRequest] = field(default_factory=list)

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        ordinal = len(self.requests)
        if ordinal in (1, 2, 3):
            return ChatResponse(
                content=None,
                provider=self.provider_name,
                model=self.model_name,
                finish_reason="tool_calls",
                tool_calls=(
                    ToolCall(
                        id=f"reachability-tool-{ordinal}",
                        name="knowledge.search",
                        arguments={
                            "query": (
                                "早期死亡"
                                if ordinal == 1
                                else "补刀趋势"
                                if ordinal == 2
                                else "训练目标"
                            ),
                            "top_k": 2,
                        },
                    ),
                ),
                usage=TokenUsage(),
            )
        if ordinal == 4:
            return self._text(_FULL_REPORT)
        if ordinal in (5, 8):
            return self._text("{invalid-structured-output")
        if ordinal == 6:
            return self._text(
                json.dumps(_evaluation_payload("needs_revision"), ensure_ascii=False)
            )
        if ordinal == 7 and any(
            row.content == REVISER_SYSTEM_PROMPT for row in request.messages
        ):
            return self._text(_FULL_REPORT.replace("需要核验", "应当核验"))
        if ordinal == 9:
            return self._text(json.dumps(_evaluation_payload("fail"), ensure_ascii=False))
        raise AssertionError("unexpected V3 reachability request sequence")

    def _text(self, content: str) -> ChatResponse:
        return ChatResponse(
            content=content,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="stop",
            usage=TokenUsage(),
        )


def _evaluation_payload(verdict: Literal["needs_revision", "fail"]) -> dict:
    return {
        "score": 80 if verdict == "fail" else 70,
        "verdict": verdict,
        "issues": [
            {
                "severity": "low" if verdict == "fail" else "medium",
                "category": "other" if verdict == "fail" else "fact_error",
                "quote": "bounded synthetic quote",
                "evidence": "bounded synthetic evidence",
                "explanation": "bounded synthetic explanation",
                "suggested_correction": "bounded synthetic correction",
            }
        ],
        "passed_checks": ["schema", "citations"],
        "summary": "bounded synthetic evaluation",
    }


_FULL_REPORT = """# RiftCoach 教练式复盘报告

## 1. 总体结论
五局合成样本只支持谨慎复盘，知识依据见 [K1]。

## 2. 当前表现亮点
当前样本中有可继续观察的稳定片段。

## 3. 主要风险点
前期阵亡差异需要核验，不能直接解释胜负。

## 4. 赢局与输局差异
这里只描述样本差异，不声明因果关系。

## 5. 下一步复盘建议
优先回看第一次阵亡前的兵线与视野信息。

## 6. 训练计划
下一局记录两个可验证的决策节点。

## 7. 数据边界与知识来源
玩家数据为匿名合成数据，知识来源见 [K1]。
"""


def _inside_file(root: Path, path: str | Path) -> Path:
    candidate = (root / Path(path)).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise FileNotFoundError("required V3 asset is missing")
    return candidate


def _canonical_sha256(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def _digest_json(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _round_up(value: int, unit: int) -> int:
    return math.ceil(value / unit) * unit


__all__ = [
    "ALGORITHM_VERSION",
    "CASE_MAX_CALLS",
    "DOMAIN_MAX_CALLS",
    "INPUT_SAFETY_MULTIPLIER",
    "REPORT_PATH",
    "V3BudgetReachabilityReport",
    "build_v3_budget_reachability_report",
    "canonical_v3_budget_reachability_bytes",
    "estimate_runtime_request_input_ceiling",
    "load_v3_budget_reachability_report",
    "measure_request_envelope",
]
