"""Offline preparation: the host binds a target to the exact issued request.

Not registered as a Coach evaluator or a third live diagnostic. Transport receipt
identity must come from trusted host code, never from model-generated JSON.
"""
from dataclasses import dataclass, replace
import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.evaluation import golden_context_relation_probe_v2 as previous
from app.evaluation.golden_context_requests import checked
from app.evaluation.golden_fact_candidate import fact_pack
from app.evaluation.golden_review_experiment import SourceIndex, QuoteRef, compact
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from app.providers.models import ChatMessage, ChatRequest, MessageRole
from app.providers.structured import contract_for_model


class ScopeJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    disposition: Literal["sample_defined", "needs_clarification", "beyond_sample", "negated"]
    context_ref: QuoteRef | None
    explanation: str = Field(min_length=1, max_length=1600)

    @model_validator(mode="after")
    def definition_requires_source(self):
        if (self.disposition in {"sample_defined", "negated"}) != (self.context_ref is not None):
            raise ValueError("bound_scope_context_required")
        return self


@dataclass(frozen=True)
class PreparedScopeReview:
    source: SourceIndex
    target: str
    request: ChatRequest


@dataclass(frozen=True)
class IssuedScopeReview:
    source: SourceIndex
    target: str
    request_sha256: str


def prepare(summary, deterministic, knowledge, report, target):
    old = previous.build_request(summary, deterministic, knowledge, report, target)
    contract = contract_for_model(name="bound_scope_judgment", version="1.0.0", output_model=ScopeJudgment)
    before = compact(previous.response_contract().schema_dict())
    if not old.messages[1].content.startswith(before + "\n"):
        raise ValueError("bound_scope_schema_identity")
    echo = "source_digest复制source_index.source_digest；target_ref使用输入给定的完整目标引用。"
    if previous.POLICY.count(echo) != 1:
        raise ValueError("bound_scope_policy_identity")
    policy = previous.POLICY.replace(echo,
        "本请求只有一个给定target，身份由程序绑定。只返回判断、实际定义的context_ref及解释，不复述目标或摘要。", 1)
    request = checked(replace(old, messages=(ChatMessage(role=MessageRole.SYSTEM, content=policy),
        ChatMessage(role=MessageRole.USER, content=compact(contract.schema_dict()) + old.messages[1].content[len(before):])),
        response_contract=contract))
    return PreparedScopeReview(SourceIndex.build(report, fact_pack(summary)), target, request)


def seal_issued_request(prepared, issued_request):
    """Run at the transport boundary AFTER any trusted budget-wrapper changes."""
    if (issued_request.messages != prepared.request.messages
            or issued_request.response_contract != prepared.request.response_contract
            or issued_request.tools != prepared.request.tools
            or issued_request.tool_choice != prepared.request.tool_choice):
        raise ValueError("bound_scope_issued_input_mismatch")
    wire = validate_request(issued_request, transport_id=CAPACITY_TRANSPORT_ID)
    return IssuedScopeReview(prepared.source, prepared.target, hashlib.sha256(wire).hexdigest())


def decode(issued, response, *, receipt_request_sha256):
    """Join trusted receipt identity, source text and model judgment, never score."""
    if receipt_request_sha256 != issued.request_sha256:
        raise ValueError("bound_scope_receipt_mismatch")
    if response.finish_reason != "stop" or response.tool_calls:
        raise ValueError("bound_scope_incomplete_response")
    value = ScopeJudgment.model_validate(strict_json(response.content), strict=True)
    context = (issued.source.resolve(value.context_ref.model_dump()) if value.context_ref else None)
    return dict(request_sha256=issued.request_sha256, source_digest=issued.source.source_digest,
        target_ref=issued.source.reference(issued.target), target_quote=issued.target,
        disposition=value.disposition,
        context_ref=value.context_ref.model_dump(exclude_none=True) if value.context_ref else None,
        context_quote=context, explanation=value.explanation, whole_report_acceptance=False)
