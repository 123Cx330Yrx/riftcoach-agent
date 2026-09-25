"""Explicit unadmitted Coach composition; never selected by a model resolver."""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CoachContractSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    contract_id: Literal["recent-form-review-flash-v2", "recent-form-review-roles-v1"] = "recent-form-review-flash-v2"
    version: Literal["1.0.0", "1.1.0", "1.2.0", "1.3.0", "1.3.1", "1.3.2", "1.3.3", "1.3.4", "1.3.5", "1.3.6", "1.3.7", "1.3.8", "1.3.9", "1.3.10", "1.3.11", "1.3.12", "1.3.13", "1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27", "1.4.0", "1.4.1", "1.4.2", "1.4.3", "1.4.4", "1.4.5", "1.4.6", "1.5.0", "1.5.1", "1.5.2", "1.5.3"] = "1.0.0"
    scope: Literal["unadmitted_opt_in"] = "unadmitted_opt_in"
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class CoachExecutionContract:
    version: str = "1.0.0"

    @property
    def grounded(self):
        return self.version in ("1.1.0", "1.2.0", "1.3.0", "1.3.1", "1.3.2", "1.3.3", "1.3.4", "1.3.5", "1.3.6", "1.3.7", "1.3.8", "1.3.9", "1.3.10", "1.3.11", "1.3.12", "1.3.13", "1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27")

    @property
    def context_policy(self):
        if self.grounded:
            from app.evaluation.coach_grounded_contract import grounded_context_policy
            base = grounded_context_policy()
            if self.version in ("1.3.7", "1.3.8", "1.3.9", "1.3.10", "1.3.11", "1.3.12", "1.3.13", "1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
                from app.evaluation.golden_inference_audit import INFERENCE_POLICY
                if self.version in ("1.3.8", "1.3.9", "1.3.10", "1.3.11", "1.3.12", "1.3.13", "1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
                    from app.evaluation.golden_inference_audit_v2 import INFERENCE_POLICY
                if self.version == "1.3.9":
                    from app.evaluation.golden_inference_audit_v3 import INFERENCE_POLICY
                if self.version == "1.3.13":
                    from app.evaluation.golden_inference_scope_v3 import SCOPE_V3_POLICY as INFERENCE_POLICY
                if self.version in ("1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
                    from app.evaluation.golden_inference_scope_v4 import SCOPE_V4_POLICY as INFERENCE_POLICY
                if self.version == "1.3.12":
                    from app.evaluation.golden_inference_scope_v2 import SCOPE_V2_POLICY as INFERENCE_POLICY
                if self.version == "1.3.11":
                    from app.evaluation.golden_inference_scope import SCOPE_POLICY as INFERENCE_POLICY
                if self.version == "1.3.10":
                    from app.evaluation.golden_inference_coverage import COVERAGE_POLICY as INFERENCE_POLICY
                if self.version == "1.3.16":
                    from app.evaluation.golden_inference_scope_v5 import SCOPE_V5_POLICY as INFERENCE_POLICY
                if self.version == "1.3.17":
                    from app.evaluation.golden_fact_runtime import INFERENCE_POLICY
                if self.version == "1.3.18":
                    from app.evaluation.golden_evidence_runtime import INFERENCE_POLICY
                if self.version in ("1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
                    from app.evaluation.golden_evidence_runtime_v2 import INFERENCE_POLICY
                if self.version == "1.3.21":
                    from app.evaluation.golden_evidence_runtime_v3 import INFERENCE_POLICY
                if self.version == "1.3.22":
                    from app.evaluation.golden_evidence_runtime_v4 import INFERENCE_POLICY
                if self.version == "1.3.23":
                    from app.evaluation.golden_evidence_runtime_v5 import INFERENCE_POLICY
                if self.version == "1.3.24":
                    from app.evaluation.golden_evidence_runtime_v6 import INFERENCE_POLICY
                if self.version == "1.3.25":
                    from app.evaluation.golden_evidence_runtime_v7 import INFERENCE_POLICY
                if self.version == "1.3.26":
                    from app.evaluation.golden_evidence_runtime_v8 import INFERENCE_POLICY
                if self.version == "1.3.27":
                    from app.evaluation.golden_context_runtime import INFERENCE_POLICY
                base += "\n\n" + INFERENCE_POLICY
            if self.position_policy:
                base += "\n\n" + self.position_policy
            if self.source_use_policy:
                base += "\n\n" + self.source_use_policy
            return base + "\n\n" + self.compact_report_policy if self.compact_report_policy else base
        from app.evaluation.glm53_report_contract import REPORT_CONTRACT_ID, candidate_context_policy
        return candidate_context_policy(REPORT_CONTRACT_ID)

    @property
    def position_policy(self):
        if self.version in ("1.3.3", "1.3.4", "1.3.5", "1.3.6", "1.3.7", "1.3.8", "1.3.9", "1.3.10", "1.3.11", "1.3.12", "1.3.13", "1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            from app.evaluation.golden_position_policy import POSITION_POLICY
            return POSITION_POLICY
        return ""

    @property
    def source_use_policy(self):
        if self.version in ("1.3.5", "1.3.6", "1.3.7", "1.3.8", "1.3.9", "1.3.10", "1.3.11", "1.3.12", "1.3.13", "1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            from app.evaluation.golden_source_use_policy import SOURCE_USE_POLICY
            return SOURCE_USE_POLICY
        return ""

    @property
    def compact_report_policy(self):
        if self.version in ("1.3.6", "1.3.7", "1.3.8", "1.3.9", "1.3.10", "1.3.11", "1.3.12", "1.3.13", "1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
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
        if self.version in ("1.2.0", "1.3.0", "1.3.1", "1.3.2", "1.3.3", "1.3.4", "1.3.5", "1.3.6", "1.3.7", "1.3.8", "1.3.9", "1.3.10", "1.3.11", "1.3.12", "1.3.13", "1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            value.update(skill_version="0.4.0", program_version="2.2.0", max_tool_calls=8)
        if self.version in ("1.3.0", "1.3.1", "1.3.2", "1.3.3", "1.3.4", "1.3.5", "1.3.6", "1.3.7", "1.3.8", "1.3.9", "1.3.10", "1.3.11", "1.3.12", "1.3.13", "1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            value.update(skill_version="0.5.0", program_version="2.3.0", max_context_tokens=28000)
        if self.version in ("1.3.1", "1.3.2", "1.3.3", "1.3.4", "1.3.5", "1.3.6", "1.3.7", "1.3.8", "1.3.9", "1.3.10", "1.3.11", "1.3.12", "1.3.13", "1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            value.update(skill_version="0.5.1", program_version="2.3.1", include_deterministic_source_facts=True)
        if self.version in ("1.3.2", "1.3.3", "1.3.4", "1.3.5", "1.3.6", "1.3.7", "1.3.8", "1.3.9", "1.3.10", "1.3.11", "1.3.12", "1.3.13", "1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            value.update(skill_version="0.5.2", program_version="2.3.2", request_timeout_s=90)
        if self.version in ("1.3.3", "1.3.4", "1.3.5", "1.3.6", "1.3.7", "1.3.8", "1.3.9", "1.3.10", "1.3.11", "1.3.12", "1.3.13", "1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            from app.evaluation.golden_position_policy import POSITION_POLICY_ID
            value.update(skill_version="0.5.3", program_version="2.3.3", position_policy_id=POSITION_POLICY_ID)
        if self.version in ("1.3.4", "1.3.5", "1.3.6", "1.3.7", "1.3.8", "1.3.9", "1.3.10", "1.3.11", "1.3.12", "1.3.13", "1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            value.update(skill_version="0.5.4", program_version="2.3.4", include_generation_facts=True)
        if self.version in ("1.3.5", "1.3.6", "1.3.7", "1.3.8", "1.3.9", "1.3.10", "1.3.11", "1.3.12", "1.3.13", "1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            from app.evaluation.golden_source_use_policy import SOURCE_USE_POLICY_ID
            value.update(skill_version="0.5.5", program_version="2.3.5", source_use_policy_id=SOURCE_USE_POLICY_ID)
        if self.version in ("1.3.6", "1.3.7", "1.3.8", "1.3.9", "1.3.10", "1.3.11", "1.3.12", "1.3.13", "1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            from app.evaluation.golden_compact_report_policy import COMPACT_REPORT_POLICY_ID
            value.update(skill_version="0.5.6", program_version="2.3.6", compact_report_policy_id=COMPACT_REPORT_POLICY_ID)
        if self.version == "1.3.7":
            from app.evaluation.golden_inference_audit import INFERENCE_POLICY_ID
            value.update(skill_version="0.5.7", program_version="2.3.7", evaluation_contract_version="1.3.0", inference_policy_id=INFERENCE_POLICY_ID)
        if self.version == "1.3.8":
            from app.evaluation.golden_inference_audit_v2 import INFERENCE_POLICY_ID
            value.update(skill_version="0.5.8", program_version="2.3.8", evaluation_contract_version="1.4.0", inference_policy_id=INFERENCE_POLICY_ID)
        if self.version == "1.3.9":
            from app.evaluation.golden_inference_audit_v3 import INFERENCE_POLICY_ID
            value.update(skill_version="0.5.9", program_version="2.3.9", evaluation_contract_version="1.4.0", inference_policy_id=INFERENCE_POLICY_ID, anchor_repair_policy="shared-single-structured-repair")
        if self.version == "1.3.13":
            from app.evaluation.golden_inference_scope_v3 import SCOPE_V3_POLICY_ID
            value.update(skill_version="0.5.13", program_version="2.3.13", evaluation_contract_version="1.8.0", inference_policy_id=SCOPE_V3_POLICY_ID, anchor_repair_policy="shared-single-structured-repair")
        if self.version in ("1.3.14", "1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            from app.evaluation.golden_inference_scope_v4 import SCOPE_V4_POLICY_ID
            value.update(skill_version="0.5.14", program_version="2.3.14", evaluation_contract_version="1.9.0", inference_policy_id=SCOPE_V4_POLICY_ID, anchor_repair_policy="shared-single-structured-repair")
        if self.version == "1.3.12":
            from app.evaluation.golden_inference_scope_v2 import SCOPE_V2_POLICY_ID
            value.update(skill_version="0.5.12", program_version="2.3.12", evaluation_contract_version="1.7.0", inference_policy_id=SCOPE_V2_POLICY_ID, anchor_repair_policy="shared-single-structured-repair")
        if self.version == "1.3.11":
            from app.evaluation.golden_inference_scope import SCOPE_POLICY_ID
            value.update(skill_version="0.5.11", program_version="2.3.11", evaluation_contract_version="1.6.0", inference_policy_id=SCOPE_POLICY_ID, anchor_repair_policy="shared-single-structured-repair")
        if self.version == "1.3.10":
            from app.evaluation.golden_inference_coverage import COVERAGE_POLICY_ID
            value.update(skill_version="0.5.10", program_version="2.3.10", evaluation_contract_version="1.5.0", inference_policy_id=COVERAGE_POLICY_ID, anchor_repair_policy="shared-single-structured-repair")
        if self.version in ("1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            value.update(skill_version="0.5.15", program_version="2.3.15",
                         max_calls=5, max_output_tokens=16384, total_tokens=5 * (64000 + 16384),
                         request_timeout_s=180, agent_timeout_s=240, execution_timeout_s=900,
                         stream_transport_id="golden-process-stream-high-16384-v1")
        if self.version == "1.3.16":
            from app.evaluation.golden_inference_scope_v5 import SCOPE_V5_POLICY_ID
            value.update(skill_version="0.5.16", program_version="2.3.16", evaluation_contract_version="1.10.0",
                         inference_policy_id=SCOPE_V5_POLICY_ID, evaluation_repair_policy="one-grounded-correction-with-bounded-diagnostics")
        if self.version == "1.3.17":
            from app.evaluation.golden_fact_runtime import INFERENCE_POLICY_ID
            value.update(skill_version="0.5.17", program_version="2.3.17", evaluation_contract_version="1.11.0",
                         inference_policy_id=INFERENCE_POLICY_ID, evaluation_repair_policy="one-grounded-correction-with-fact-diagnostics")
        if self.version == "1.3.18":
            from app.evaluation.golden_evidence_runtime import INFERENCE_POLICY_ID
            value.update(skill_version="0.5.18", program_version="2.3.18", evaluation_contract_version="1.12.0",
                         inference_policy_id=INFERENCE_POLICY_ID, evaluation_repair_policy="one-grounded-correction-with-evidence-diagnostics")
        if self.version in ("1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            from app.evaluation.golden_evidence_runtime_v2 import INFERENCE_POLICY_ID
            value.update(skill_version="0.5.19", program_version="2.3.19", evaluation_contract_version="1.13.0",
                         inference_policy_id=INFERENCE_POLICY_ID, evaluation_repair_policy="one-grounded-correction-with-evidence-diagnostics")
        if self.version in ("1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            value.update(skill_version="0.5.20", program_version="2.3.20", max_output_tokens=32768,
                         request_timeout_s=300, agent_timeout_s=330, total_tokens=401920,
                         stream_transport_id="golden-process-stream-high-32768-v1")
        if self.version == "1.3.21":
            from app.evaluation.golden_evidence_runtime_v3 import INFERENCE_POLICY_ID
            value.update(skill_version="0.5.21", program_version="2.3.21", evaluation_contract_version="1.14.0",
                         inference_policy_id=INFERENCE_POLICY_ID)
        if self.version == "1.3.22":
            from app.evaluation.golden_evidence_runtime_v4 import INFERENCE_POLICY_ID
            value.update(skill_version="0.5.22", program_version="2.3.22", evaluation_contract_version="1.15.0",
                         inference_policy_id=INFERENCE_POLICY_ID)
        if self.version == "1.3.23":
            from app.evaluation.golden_evidence_runtime_v5 import INFERENCE_POLICY_ID
            value.update(skill_version="0.5.23", program_version="2.3.23", evaluation_contract_version="1.16.0",
                         inference_policy_id=INFERENCE_POLICY_ID)

        if self.version == "1.3.24":
            from app.evaluation.golden_evidence_runtime_v6 import INFERENCE_POLICY_ID
            value.update(skill_version="0.5.24", program_version="2.3.24", evaluation_contract_version="1.17.0",
                         inference_policy_id=INFERENCE_POLICY_ID)

        if self.version == "1.3.25":
            from app.evaluation.golden_evidence_runtime_v7 import INFERENCE_POLICY_ID
            value.update(skill_version="0.5.25", program_version="2.3.25", evaluation_contract_version="1.18.0",
                         inference_policy_id=INFERENCE_POLICY_ID)

        if self.version == "1.3.26":
            from app.evaluation.golden_evidence_runtime_v8 import INFERENCE_POLICY_ID
            value.update(skill_version="0.5.26", program_version="2.3.26", evaluation_contract_version="1.19.0",
                         inference_policy_id=INFERENCE_POLICY_ID)
        if self.version == "1.3.27":
            from app.evaluation.golden_context_runtime import INFERENCE_POLICY_ID
            value.update(skill_version="0.5.27", program_version="2.3.27", evaluation_contract_version="1.20.0",
                         inference_policy_id=INFERENCE_POLICY_ID,
                         evaluation_repair_policy="one-reference-patch-or-full-reassessment")
        return value

    def snapshot(self):
        raw = json.dumps(self.descriptor(), sort_keys=True, separators=(",", ":"))
        return CoachContractSnapshot(version=self.version, sha256=hashlib.sha256(raw.encode()).hexdigest())

    @property
    def request_policy(self):
        if self.version in ("1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            return _capacity_request_policy()
        if self.version in ("1.3.15", "1.3.16", "1.3.17", "1.3.18", "1.3.19", "1.3.20", "1.3.21", "1.3.22", "1.3.23", "1.3.24", "1.3.25", "1.3.26", "1.3.27"):
            return _expanded_request_policy()
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


@lru_cache(maxsize=1)
def _expanded_request_policy():
    from app.model_runtime import _issue_candidate_evaluation_request_policy
    return _issue_candidate_evaluation_request_policy(
        policy_id="glm-5.3-flash-coach-high-16384", version="1.0.0", provider_id="zhipu", model="glm-5.3-flash",
        agent_timeout_s=240.0, llm_tool_timeout_s=240.0, transport_timeout_s=270.0,
        max_output_tokens=16384, temperature=1.0, top_p=0.95)


@lru_cache(maxsize=1)
def _capacity_request_policy():
    from app.model_runtime import _issue_candidate_evaluation_request_policy
    return _issue_candidate_evaluation_request_policy(
        policy_id="glm-5.3-flash-coach-high-32768", version="1.0.0", provider_id="zhipu", model="glm-5.3-flash",
        agent_timeout_s=330.0, llm_tool_timeout_s=330.0, transport_timeout_s=360.0,
        max_output_tokens=32768, temperature=1.0, top_p=0.95)


CONTEXT_COACH_CONTRACT = CoachExecutionContract(version="1.3.27")
EVIDENCE_V8_COACH_CONTRACT = CoachExecutionContract(version="1.3.26")
EVIDENCE_V7_COACH_CONTRACT = CoachExecutionContract(version="1.3.25")
EVIDENCE_V6_COACH_CONTRACT = CoachExecutionContract(version="1.3.24")
EVIDENCE_V5_COACH_CONTRACT = CoachExecutionContract(version="1.3.23")
EVIDENCE_V4_COACH_CONTRACT = CoachExecutionContract(version="1.3.22")
EVIDENCE_V3_COACH_CONTRACT = CoachExecutionContract(version="1.3.21")
CAPACITY_COACH_CONTRACT = CoachExecutionContract(version="1.3.20")
EXPANDED_COACH_CONTRACT = CoachExecutionContract(version="1.3.15")
FEEDBACK_COACH_CONTRACT = CoachExecutionContract(version="1.3.16")
FACT_INFERENCE_COACH_CONTRACT = CoachExecutionContract(version="1.3.17")
EVIDENCE_COACH_CONTRACT = CoachExecutionContract(version="1.3.18")
EVIDENCE_V2_COACH_CONTRACT = CoachExecutionContract(version="1.3.19")
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
INFERENCE_COACH_CONTRACT = CoachExecutionContract(version="1.3.7")
CLAIM_COACH_CONTRACT = CoachExecutionContract(version="1.3.8")
ANCHOR_COACH_CONTRACT = CoachExecutionContract(version="1.3.9")
SCOPE_V3_COACH_CONTRACT = CoachExecutionContract(version="1.3.13")
SCOPE_V4_COACH_CONTRACT = CoachExecutionContract(version="1.3.14")
SCOPE_V2_COACH_CONTRACT = CoachExecutionContract(version="1.3.12")
SCOPE_COACH_CONTRACT = CoachExecutionContract(version="1.3.11")
COVERAGE_COACH_CONTRACT = CoachExecutionContract(version="1.3.10")


class NativeCoachExecutionContract(CoachExecutionContract):
    @property
    def grounded(self):
        return True

    @property
    def context_policy(self):
        from .native_coach_contract import generation_policy
        return generation_policy()

    @property
    def request_policy(self):
        return _capacity_request_policy()

    def descriptor(self):
        value = CONTEXT_COACH_CONTRACT.descriptor()
        value.update(version=self.version, skill_version="0.6.0", program_version="3.0.6",
            evaluation_contract_version="3.2.0", inference_policy_id="golden-native-issues-review-v3.6",
            evaluation_repair_policy="one-full-native-reassessment-with-original-response",
            context_policy_sha256=hashlib.sha256(self.context_policy.encode()).hexdigest())
        return value


NATIVE_COACH_CONTRACT = NativeCoachExecutionContract(version="1.4.6")


@lru_cache(maxsize=1)
def _role_request_policy():
    from app.model_runtime import _issue_candidate_evaluation_request_policy
    from .reviewer_roles import ROLE_COMPOSITION_ID
    return _issue_candidate_evaluation_request_policy(
        policy_id="flash-generation-glm53-review-high-32768", version="1.0.0",
        provider_id="zhipu", model=ROLE_COMPOSITION_ID,
        agent_timeout_s=330.0, llm_tool_timeout_s=330.0, transport_timeout_s=360.0,
        max_output_tokens=32768, temperature=1.0, top_p=0.95)


class RoleCoachExecutionContract(NativeCoachExecutionContract):
    """Opt-in roles are explicit in the immutable execution snapshot."""
    @property
    def request_policy(self):
        return _role_request_policy()

    def descriptor(self):
        from .reviewer_roles import ROLE_COMPOSITION_ID, ROLE_PROFILE_ID, role_descriptor
        from app.evaluation.golden_explicit_source_projection import VERSION
        value = super().descriptor()
        value.update(contract_id="recent-form-review-roles-v1", model=ROLE_COMPOSITION_ID,
            thinking_profile_id=ROLE_PROFILE_ID, skill_version="0.6.1", program_version="3.1.1",
            evaluation_contract_version="3.4.0", inference_policy_id="golden-role-review-notes-v1",
            roles=role_descriptor(), source_projection=VERSION,
            stream_transport_id="per-role-explicit", evaluation_repair_policy="one-full-native-reassessment-with-original-response")
        if self.version == "1.5.0":
            # Readback only: preserve the trusted descriptor of saved traces.
            value.update(program_version="3.1.0", evaluation_contract_version="3.3.0",
                         inference_policy_id="golden-role-review-v1")
        elif self.version == "1.5.2":
            value.update(program_version="3.1.2", evaluation_contract_version="3.5.0",
                         inference_policy_id="golden-role-review-clarity-markers-v1")
        policy = self.request_policy
        value.update(request_policy_id=policy.policy_id, request_policy_version=policy.version,
            request_policy={key: getattr(policy, key) for key in value["request_policy"]},
            target_runtime_profile_id=ROLE_PROFILE_ID, target_runtime_profile_version="1.0.0")
        return value

    def snapshot(self):
        raw = json.dumps(self.descriptor(), sort_keys=True, separators=(",", ":"))
        return CoachContractSnapshot(contract_id="recent-form-review-roles-v1", version=self.version,
            sha256=hashlib.sha256(raw.encode()).hexdigest())

    @staticmethod
    def request_identity(request):
        from .reviewer_roles import request_identity
        return request_identity(request)

    def require_provider(self, provider):
        from .reviewer_roles import ROLE_COMPOSITION_ID, ROLE_PROFILE_ID
        if (provider.provider_name != "zhipu" or provider.model_name != ROLE_COMPOSITION_ID
                or getattr(provider, "thinking_profile_id", None) != ROLE_PROFILE_ID
                or type(getattr(provider, "sdk_max_retries", None)) is not int or provider.sdk_max_retries != 0
                or getattr(provider, "runtime_profile", None) is not None):
            raise ValueError("role_contract_provider_mismatch")
        projection = getattr(provider, "source_projection", None)
        if projection is not None and projection != self.descriptor()["source_projection"]:
            raise ValueError("role_contract_projection_mismatch")

    @property
    def pricing_profiles(self):
        # ADR0108 official-price snapshot; conservative uncached estimate, not a bill.
        from decimal import Decimal
        from .models import RuntimePricingProfile
        return {( "zhipu", model): RuntimePricingProfile(profile_id="glm53-roles-uncached-20260922", version="1.0.0",
            provider_id="zhipu", model=model, currency="CNY",
            input_cost_per_million=Decimal(input_price), output_cost_per_million=Decimal(output_price))
            for model, input_price, output_price in (
                ("glm-5.3-flash", "0.8", "2.8"),
                ("glm-5.3", "8", "28"))}


ROLE_COACH_CONTRACT = RoleCoachExecutionContract(version="1.5.2")


class CoarseRoleCoachExecutionContract(RoleCoachExecutionContract):
    def descriptor(self):
        from app.evaluation.golden_coarse_source_projection import VERSION
        from app.evaluation.golden_role_coarse import CONTRACT_ID
        value = super().descriptor()
        value.update(skill_version="0.6.2", program_version="3.2.0",
            evaluation_contract_version="3.6.0", inference_policy_id=CONTRACT_ID,
            source_projection=VERSION)
        return value

    @staticmethod
    def request_identity(request):
        from app.evaluation.golden_coarse_source_projection import VERSION
        from .reviewer_roles import request_identity
        return request_identity(request, source_projection=VERSION)

    def require_provider(self, provider):
        super().require_provider(provider)
        from app.evaluation.golden_coarse_source_projection import VERSION
        if getattr(provider, "source_projection", None) != VERSION:
            raise ValueError("role_contract_projection_mismatch")


COARSE_ROLE_COACH_CONTRACT = CoarseRoleCoachExecutionContract(version="1.5.3")
LEGACY_NOTE_ROLE_COACH_CONTRACT = RoleCoachExecutionContract(version="1.5.1")
LEGACY_ROLE_COACH_CONTRACT = RoleCoachExecutionContract(version="1.5.0")


def require_coach_contract(value):
    if value is not None and all(value is not c for c in (COACH_CONTRACT, NATIVE_COACH_CONTRACT, ROLE_COACH_CONTRACT, COARSE_ROLE_COACH_CONTRACT, CONTEXT_COACH_CONTRACT, EVIDENCE_V8_COACH_CONTRACT, EVIDENCE_V7_COACH_CONTRACT, EVIDENCE_V6_COACH_CONTRACT, EVIDENCE_V5_COACH_CONTRACT, EVIDENCE_V4_COACH_CONTRACT, EVIDENCE_V3_COACH_CONTRACT, CAPACITY_COACH_CONTRACT, EVIDENCE_V2_COACH_CONTRACT, EVIDENCE_COACH_CONTRACT, FACT_INFERENCE_COACH_CONTRACT, FEEDBACK_COACH_CONTRACT, EXPANDED_COACH_CONTRACT, GROUNDED_COACH_CONTRACT, BATCH_COACH_CONTRACT, GOLDEN_COACH_CONTRACT, SOURCE_COACH_CONTRACT, LATENCY_COACH_CONTRACT, POSITION_COACH_CONTRACT, FACT_COACH_CONTRACT, ADVICE_COACH_CONTRACT, COMPACT_COACH_CONTRACT, INFERENCE_COACH_CONTRACT, CLAIM_COACH_CONTRACT, ANCHOR_COACH_CONTRACT, COVERAGE_COACH_CONTRACT, SCOPE_COACH_CONTRACT, SCOPE_V2_COACH_CONTRACT, SCOPE_V3_COACH_CONTRACT, SCOPE_V4_COACH_CONTRACT)):
        raise ValueError("unsupported Coach execution contract")
    return value


def coach_component_fingerprint(contract=COACH_CONTRACT):
    from app.evaluation.prompt_context_identity import ComponentFingerprint
    require_coach_contract(contract)
    return ComponentFingerprint(component_id="coach_execution_contract",
                                source=(f"app.runtime.reviewer_roles:v{contract.version}" if contract in (ROLE_COACH_CONTRACT, COARSE_ROLE_COACH_CONTRACT) else f"app.runtime.native_coach_contract:v{contract.version}" if contract is NATIVE_COACH_CONTRACT else "app.runtime.coach_contract:v1.3.19" if contract.version == "1.3.19" else "app.runtime.coach_contract:v1.3.18" if contract.version == "1.3.18" else "app.runtime.coach_contract:v1.3.17" if contract.version == "1.3.17" else "app.runtime.coach_contract:v1.3.16" if contract.version == "1.3.16" else "app.runtime.coach_contract:v1.3.15" if contract.version == "1.3.15" else "app.runtime.coach_contract:v1.3.14" if contract.version == "1.3.14" else "app.runtime.coach_contract:v1.3.13" if contract.version == "1.3.13" else "app.runtime.coach_contract:v1.3.12" if contract.version == "1.3.12" else "app.runtime.coach_contract:v1.3.11" if contract.version == "1.3.11" else "app.runtime.coach_contract:v1.3.10" if contract.version == "1.3.10" else
                                        "app.runtime.coach_contract:v1.3.9" if contract.version == "1.3.9" else
                                        "app.runtime.coach_contract:v1.3.8" if contract.version == "1.3.8" else
                                        "app.runtime.coach_contract:v1.3.7" if contract.version == "1.3.7" else
                                        "app.runtime.coach_contract:v1.3.6" if contract.version == "1.3.6" else
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
