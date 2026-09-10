"""Explicit unadmitted Coach composition; never selected by a model resolver."""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CoachContractSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    contract_id: Literal["recent-form-review-flash-v2"] = "recent-form-review-flash-v2"
    version: Literal["1.0.0", "1.1.0", "1.2.0", "1.3.0", "1.3.1", "1.3.2", "1.3.3", "1.3.4", "1.3.5", "1.3.6"] = "1.0.0"
    scope: Literal["unadmitted_opt_in"] = "unadmitted_opt_in"
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class CoachExecutionContract:
    version: str = "1.0.0"

    @property
    def grounded(self):
        return self.version in ("1.1.0", "1.2.0", "1.3.0", "1.3.1", "1.3.2", "1.3.3", "1.3.4", "1.3.5", "1.3.6")

    @property
    def context_policy(self):
        if self.grounded:
            from app.evaluation.coach_grounded_contract import grounded_context_policy
            base = grounded_context_policy()
            if self.position_policy:
                base += "\n\n" + self.position_policy
            if self.source_use_policy:
                base += "\n\n" + self.source_use_policy
            return base + "\n\n" + self.compact_report_policy if self.compact_report_policy else base
        from app.evaluation.glm53_report_contract import REPORT_CONTRACT_ID, candidate_context_policy
        return candidate_context_policy(REPORT_CONTRACT_ID)

    @property
    def position_policy(self):
        if self.version in ("1.3.3", "1.3.4", "1.3.5", "1.3.6"):
            from app.evaluation.golden_position_policy import POSITION_POLICY
            return POSITION_POLICY
        return ""

    @property
    def source_use_policy(self):
        if self.version in ("1.3.5", "1.3.6"):
            from app.evaluation.golden_source_use_policy import SOURCE_USE_POLICY
            return SOURCE_USE_POLICY
        return ""

    @property
    def compact_report_policy(self):
        if self.version == "1.3.6":
            from app.evaluation.golden_compact_report_policy import COMPACT_REPORT_POLICY
            return COMPACT_REPORT_POLICY
        return ""

    def descriptor(self):
        from app.evaluation.glm53_report_contract import REPORT_CONTRACT_ID, candidate_context_policy
        policy = self.request_policy
        from app.rag.coaching_query import POLICY_ID
        value = {
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
        if self.grounded:
            from app.evaluation.coach_grounded_contract import GROUNDED_REPORT_ID
            value.update(version=self.version, program_version="2.1.0", evaluation_contract_version="1.2.0",
                         report_contract_id=GROUNDED_REPORT_ID,
                         context_policy_sha256=hashlib.sha256(self.context_policy.encode()).hexdigest(),
                         missing_citation_policy="existing-single-revision", evaluation_repair_policy="one-evidence-grounded-correction")
            value.update(reasoning_effort="high", max_output_tokens=8192, total_tokens=9 * (64000 + 8192),
                         request_timeout_s=60, agent_timeout_s=120, execution_timeout_s=480)
        if self.version in ("1.2.0", "1.3.0", "1.3.1", "1.3.2", "1.3.3", "1.3.4", "1.3.5", "1.3.6"):
            value.update(skill_version="0.4.0", program_version="2.2.0", max_tool_calls=8)
        if self.version in ("1.3.0", "1.3.1", "1.3.2", "1.3.3", "1.3.4", "1.3.5", "1.3.6"):
            value.update(skill_version="0.5.0", program_version="2.3.0", max_context_tokens=28000)
        if self.version in ("1.3.1", "1.3.2", "1.3.3", "1.3.4", "1.3.5", "1.3.6"):
            value.update(skill_version="0.5.1", program_version="2.3.1", include_deterministic_source_facts=True)
        if self.version in ("1.3.2", "1.3.3", "1.3.4", "1.3.5", "1.3.6"):
            value.update(skill_version="0.5.2", program_version="2.3.2", request_timeout_s=90)
        if self.version in ("1.3.3", "1.3.4", "1.3.5", "1.3.6"):
            from app.evaluation.golden_position_policy import POSITION_POLICY_ID
            value.update(skill_version="0.5.3", program_version="2.3.3", position_policy_id=POSITION_POLICY_ID)
        if self.version in ("1.3.4", "1.3.5", "1.3.6"):
            value.update(skill_version="0.5.4", program_version="2.3.4", include_generation_facts=True)
        if self.version in ("1.3.5", "1.3.6"):
            from app.evaluation.golden_source_use_policy import SOURCE_USE_POLICY_ID
            value.update(skill_version="0.5.5", program_version="2.3.5", source_use_policy_id=SOURCE_USE_POLICY_ID)
        if self.version == "1.3.6":
            from app.evaluation.golden_compact_report_policy import COMPACT_REPORT_POLICY_ID
            value.update(skill_version="0.5.6", program_version="2.3.6", compact_report_policy_id=COMPACT_REPORT_POLICY_ID)
        return value

    def snapshot(self):
        raw = json.dumps(self.descriptor(), sort_keys=True, separators=(",", ":"))
        return CoachContractSnapshot(version=self.version, sha256=hashlib.sha256(raw.encode()).hexdigest())

    @property
    def request_policy(self):
        if self.grounded:
            return _grounded_request_policy()
        from app.evaluation.glm53_flash_candidate_profile import GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
        return GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY

    def require_provider(self, provider):
        from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_LOW_CANDIDATE_PROFILE, ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
        profile = ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE if self.grounded else ZHIPU_GLM53_FLASH_LOW_CANDIDATE_PROFILE
        if (provider.provider_name != "zhipu" or provider.model_name != "glm-5.3-flash"
                or getattr(provider, "thinking_profile_id", None) != profile.profile_id
                or type(getattr(provider, "sdk_max_retries", None)) is not int
                or provider.sdk_max_retries != 0
                or getattr(provider, "runtime_profile", None) is not None):
            raise ValueError("explicit Coach contract requires its exact unadmitted thinking profile and zero SDK retries")


@lru_cache(maxsize=1)
def _grounded_request_policy():
    from app.model_runtime import _issue_candidate_evaluation_request_policy
    return _issue_candidate_evaluation_request_policy(
        policy_id="glm-5.3-flash-coach-high-8192", version="1.0.0", provider_id="zhipu", model="glm-5.3-flash",
        agent_timeout_s=120.0, llm_tool_timeout_s=120.0, transport_timeout_s=150.0,
        max_output_tokens=8192, temperature=1.0, top_p=0.95,
    )


COACH_CONTRACT = CoachExecutionContract()
GROUNDED_COACH_CONTRACT = CoachExecutionContract(version="1.1.0")
BATCH_COACH_CONTRACT = CoachExecutionContract(version="1.2.0")
GOLDEN_COACH_CONTRACT = CoachExecutionContract(version="1.3.0")
SOURCE_COACH_CONTRACT = CoachExecutionContract(version="1.3.1")
LATENCY_COACH_CONTRACT = CoachExecutionContract(version="1.3.2")
POSITION_COACH_CONTRACT = CoachExecutionContract(version="1.3.3")
FACT_COACH_CONTRACT = CoachExecutionContract(version="1.3.4")
ADVICE_COACH_CONTRACT = CoachExecutionContract(version="1.3.5")
COMPACT_COACH_CONTRACT = CoachExecutionContract(version="1.3.6")


def require_coach_contract(value):
    if value is not None and all(value is not c for c in (COACH_CONTRACT, GROUNDED_COACH_CONTRACT, BATCH_COACH_CONTRACT, GOLDEN_COACH_CONTRACT, SOURCE_COACH_CONTRACT, LATENCY_COACH_CONTRACT, POSITION_COACH_CONTRACT, FACT_COACH_CONTRACT, ADVICE_COACH_CONTRACT, COMPACT_COACH_CONTRACT)):
        raise ValueError("unsupported Coach execution contract")
    return value


def coach_component_fingerprint(contract=COACH_CONTRACT):
    from app.evaluation.prompt_context_identity import ComponentFingerprint
    require_coach_contract(contract)
    return ComponentFingerprint(component_id="coach_execution_contract",
                                source=("app.runtime.coach_contract:v1.3.6" if contract.version == "1.3.6" else
                                        "app.runtime.coach_contract:v1.3.5" if contract.version == "1.3.5" else
                                        "app.runtime.coach_contract:v1.3.4" if contract.version == "1.3.4" else
                                        "app.runtime.coach_contract:v1.3.3" if contract.version == "1.3.3" else
                                        "app.runtime.coach_contract:v1.3.2" if contract.version == "1.3.2" else
                                        "app.runtime.coach_contract:v1.3.1" if contract.version == "1.3.1" else
                                        "app.runtime.coach_contract:v1.3" if contract.version == "1.3.0" else
                                        "app.runtime.coach_contract:v1.2" if contract.version == "1.2.0" else
                                        "app.runtime.coach_contract:v1.1" if contract.grounded else "app.runtime.coach_contract:v1"),
                                sha256=contract.snapshot().sha256)


def require_coach_context(context, contract=COACH_CONTRACT):
    from app.agent.context import ContextBundle, ContextTrust
    if not isinstance(context, ContextBundle):
        raise ValueError("Coach requires a validated ContextBundle")
    policies = [row for row in context.sections if row.section_id == "candidate:policy_addendum"]
    if (len(policies) != 1 or policies[0].trust is not ContextTrust.INTERNAL_POLICY
            or not policies[0].required
            or policies[0].content != contract.context_policy):
        raise ValueError("Coach Context does not contain the bound trusted policy")


def guard_coach_draft(draft, _knowledge):
    from app.evaluation.coach_report import validate_revised_report
    validate_revised_report(draft.report, draft.report)
    return draft
