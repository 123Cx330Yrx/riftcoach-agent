"""Independent inventory and claim diagnostics; never an acceptance path."""
from copy import deepcopy
import json

from app.evaluation.golden_evidence_diagnostics_v6 import collect_diagnostics as duplicate_diagnostics
from app.evaluation.golden_evidence_diagnostics_v7 import collect_diagnostics as previous
from app.evaluation.golden_evidence_scope_v5 import normalize_json, SAMPLE_ANCHOR
from app.evaluation.golden_evidence_scope_v8 import heading_errors
from app.evaluation.golden_inference_coverage import report_blocks
from app.evaluation.golden_inference_scope_v5 import strict_json


def collect_diagnostics(raw, report, pack):
    try:
        value = strict_json(normalize_json(raw))
        if not isinstance(value, dict):
            raise ValueError("object_required")
    except (ValueError, TypeError):
        return duplicate_diagnostics(raw, report, pack)
    rows = heading_errors(value, report)
    inventory = [b["block_id"] for b in report_blocks(report)]
    actual = value.get("reviewed_blocks")
    if actual != inventory:
        actual = actual if isinstance(actual, list) else []
        differences = [{"index": i, "expected": want, "actual": actual[i] if i < len(actual) else None}
                       for i, want in enumerate(inventory) if i >= len(actual) or actual[i] != want]
        rows.append({"codes": ["reviewed_block_inventory_mismatch"], "expected_count": len(inventory),
                     "actual_count": len(actual), "differences": differences[:6]})
    # Diagnose local fields independently even when the model copied an ID
    # incorrectly. This private projection is never returned as model output
    # or used for acceptance; the untouched original still fails validation.
    diagnostic = deepcopy(value)
    diagnostic.pop("heading_reviews", None)
    diagnostic["reviewed_blocks"] = inventory
    local = previous(json.dumps(diagnostic), report, pack)
    for row in local:
        if "audit_index" not in row or "claim_index" not in row:
            continue
        claim = diagnostic["audits"][row["audit_index"]]["claims"][row["claim_index"]]
        codes = row["codes"]
        if "inference_literal_scope_required" in codes or "selected_sample_anchor_missing" in codes:
            row["scope"] = claim.get("scope")
            row["invalid_anchor"] = claim.get("scope_anchor")
            if claim.get("scope") == "ambiguous":
                row["repair_rule"] = "ambiguous仍须非空原文锚点：引用造成含混的词，不是不存在的样本范围；保留other澄清。"
            else:
                row["local_range_candidates"] = list(dict.fromkeys(m.group() for m in SAMPLE_ANCHOR.finditer(claim["quote"])))[:4]
                row["repair_rule"] = "候选仅为本句范围词导航，不证明语义成立。无有效局部范围不得借邻段定义；重审scope，不能编造锚点。"
        if "direct_result_scope_must_be_null" in codes:
            row["repair_rule"] = "先按语义确定类型：直接数值或算术的scope/anchor均null；推断两者均非空。"
    return rows + local
