"""Explicit unadmitted Coach composition; never selected by a model resolver."""
from dataclasses import dataclass
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CoachContractSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    contract_id: Literal["recent-form-review-flash-v2"] = "recent-form-review-flash-v2"
    version: Literal["1.0.0"] = "1.0.0"
    scope: Literal["unadmitted_opt_in"] = "unadmitted_opt_in"
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class CoachExecutionContract:
    def descriptor(self):
        from app.evaluation.glm53_report_contract import REPORT_CONTRACT_ID, candidate_context_policy
        from app.evaluation.glm53_flash_candidate_profile import GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY as policy
        from app.rag.coaching_query import POLICY_ID
        return {
            "contract_id": "recent-form-review-flash-v2", "version": "1.0.0", "scope": "unadmitted_opt_in",
            "target_runtime_profile_id": "glm-5.3-flash-runtime-v2", "target_runtime_profile_version": "2.0.0",
            "skill_version": "0.3.0", "program_version": "2.0.0",
            "request_policy_id": policy.policy_id, "request_policy_version": policy.version,
            "request_policy": {key: getattr(policy, key) for key in (
                "provider_id", "model", "agent_timeout_s", "llm_tool_timeout_s", "transport_timeout_s",
                "max_output_tokens", "temperature", "top_p", "max_retries", "deterministic_fallback_allowed")},
            "report_contract_id": REPORT_CONTRACT_ID, "retrieval_policy_id": POLICY_ID,
            "context_policy_sha256": hashlib.sha256(candidate_context_policy(REPORT_CONTRACT_ID).encode()).hexdigest(),
            "minimum_evidence_sources": 1, "minimum_score": 85, "max_revisions": 1,
            "max_calls": 9, "max_input_tokens": 64000, "max_output_tokens": 4096,
            "total_tokens": 9 * (64000 + 4096), "request_timeout_s": 45,
            "agent_timeout_s": 90, "execution_timeout_s": 360, "extra_retries": 0,
            "allow_deterministic_fallback": False,
        }

    def snapshot(self):
        raw = json.dumps(self.descriptor(), sort_keys=True, separators=(",", ":"))
        return CoachContractSnapshot(sha256=hashlib.sha256(raw.encode()).hexdigest())

    @property
    def request_policy(self):
        from app.evaluation.glm53_flash_candidate_profile import GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
        return GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY

    def require_provider(self, provider):
        from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_LOW_CANDIDATE_PROFILE
        if (provider.provider_name != "zhipu" or provider.model_name != "glm-5.3-flash"
                or getattr(provider, "thinking_profile_id", None) != ZHIPU_GLM53_FLASH_LOW_CANDIDATE_PROFILE.profile_id
                or type(getattr(provider, "sdk_max_retries", None)) is not int
                or provider.sdk_max_retries != 0
                or getattr(provider, "runtime_profile", None) is not None):
            raise ValueError("explicit Coach contract requires the exact unadmitted low profile and zero SDK retries")


COACH_CONTRACT = CoachExecutionContract()


def require_coach_contract(value):
    if value is not None and value is not COACH_CONTRACT:
        raise ValueError("unsupported Coach execution contract")
    return value


def coach_component_fingerprint():
    from app.evaluation.prompt_context_identity import ComponentFingerprint
    return ComponentFingerprint(component_id="coach_execution_contract", source="app.runtime.coach_contract:v1",
                                sha256=COACH_CONTRACT.snapshot().sha256)


def require_coach_context(context):
    from app.agent.context import ContextBundle, ContextTrust
    from app.evaluation.glm53_report_contract import REPORT_CONTRACT_ID, candidate_context_policy
    if not isinstance(context, ContextBundle):
        raise ValueError("Coach requires a validated ContextBundle")
    policies = [row for row in context.sections if row.section_id == "candidate:policy_addendum"]
    if (len(policies) != 1 or policies[0].trust is not ContextTrust.INTERNAL_POLICY
            or not policies[0].required
            or policies[0].content != candidate_context_policy(REPORT_CONTRACT_ID)):
        raise ValueError("Coach Context does not contain the bound trusted policy")


def guard_coach_draft(draft, _knowledge):
    from app.evaluation.coach_report import validate_revised_report
    validate_revised_report(draft.report, draft.report)
    return draft
