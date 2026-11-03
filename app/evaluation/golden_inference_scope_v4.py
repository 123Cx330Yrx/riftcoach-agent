"""Compact wire coverage with unchanged canonical scope validation."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from pydantic import Field
from app.evaluation.coach_grounded_contract import EvaluationResponseModelV12
from app.evaluation.golden_compact_coverage import Rows, expand_response
from app.evaluation.golden_inference_scope_v2 import AnchoredAudit
from app.evaluation.golden_inference_scope_v3 import SCOPE_V3_POLICY, inference_component_fingerprints as v3_fingerprints
from app.evaluation.prompt_context_identity import ComponentFingerprint
from app.providers.structured import contract_for_model

SCOPE_V4_POLICY_ID = "golden-inference-scope-v4"
SCOPE_V4_POLICY = SCOPE_V3_POLICY.replace("golden-inference-scope-v3", SCOPE_V4_POLICY_ID).replace(
    "严格按report_blocks顺序逐段输出coverage，每项只含block_id、metric_to_ability、cohort_comparison、scope_ambiguous。",
    "严格按report_blocks顺序逐段输出coverage，每项是四元素数组[block_id,metric_to_ability代码,cohort_comparison代码,scope_ambiguous布尔值]。"
    "两类代码均为N=not_applicable、S=supported、U=unsupported；最后一项只用true/false。"
    "例如[\"b00-1234abcd\",\"N\",\"S\",false]。仅coverage使用代码，audits/claims保持完整字段与状态。"
)

class CompactScopeResponse(EvaluationResponseModelV12):
    audits: list[AnchoredAudit] = Field(min_length=2, max_length=2)
    coverage: Rows


def inference_response_contract():
    return contract_for_model(name="coach_evaluation", version="1.9.0", output_model=CompactScopeResponse)


def audit_prompt(prompt, old_contract):
    old = json.dumps(old_contract.schema_dict(), ensure_ascii=False, indent=2)
    if old not in prompt:
        raise ValueError("inference_schema_replacement_missing")
    return SCOPE_V4_POLICY + "\n\n" + prompt.replace(old, json.dumps(
        inference_response_contract().schema_dict(), ensure_ascii=False, separators=(",", ":")), 1)


def inference_component_fingerprints(skill):
    rows = list(v3_fingerprints(skill))
    from app.evaluation import golden_compact_coverage
    probes = {
        "evaluation_schema": json.dumps(inference_response_contract().schema_dict(), sort_keys=True),
        "scope_v4_implementation": Path(__file__).read_text(encoding="utf-8"),
        "compact_coverage_implementation": Path(golden_compact_coverage.__file__).read_text(encoding="utf-8"),
    }
    for key, value in probes.items():
        row = ComponentFingerprint(component_id=key, source="app.evaluation.golden_inference_scope_v4:" + key,
                                   sha256=hashlib.sha256(value.encode()).hexdigest())
        rows = [row if old.component_id == key else old for old in rows] if any(old.component_id == key for old in rows) else [*rows, row]
    return tuple(rows)
