"""Exact anchors participate in the same single structured repair budget."""
import hashlib
import json
from pathlib import Path
from app.evaluation.golden_inference_audit_v2 import (INFERENCE_POLICY as V2_POLICY, EvaluationResponseModelV14, inference_response_contract, inference_component_fingerprints as v2_fingerprints)
from app.evaluation.prompt_context_identity import ComponentFingerprint
INFERENCE_POLICY_ID = "golden-inference-audit-v3"
INFERENCE_POLICY = V2_POLICY.replace("golden-inference-audit-v2", INFERENCE_POLICY_ID) + """
quote必须逐字复制报告中的连续原文，包括原有Markdown加粗符号和中英文引号；不要改写或拼接原句。
可选择较短但足以表达待审查判断的连续原句，不能为了缩短引用丢失否定或条件限定。
"""
def audit_prompt(prompt, old_contract):
    old=json.dumps(old_contract.schema_dict(),ensure_ascii=False,indent=2)
    if old not in prompt:raise ValueError("inference_schema_replacement_missing")
    return INFERENCE_POLICY + "\n\n" + prompt.replace(old,json.dumps(inference_response_contract().schema_dict(),ensure_ascii=False,indent=2),1)
def inference_component_fingerprints(skill):
    rows=list(v2_fingerprints(skill))
    for key,path in (("inference_v3_implementation",Path(__file__)),("contextual_decoder",Path(__file__).parents[1]/"providers/structured.py")):
        rows.append(ComponentFingerprint(component_id=key,source="app.evaluation.golden_inference_audit_v3:"+key,sha256=hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()))
    return tuple(rows)
