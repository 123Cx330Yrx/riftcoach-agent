"""Execution hold and necessary repairability checks for the failed candidate.

An empty blocker list is NOT a proof of repairability or semantic quality.
The real entry remains offline-only until a replacement contract is qualified.
"""
from collections import defaultdict

from app.evaluation.golden_contextual_patch_wire import PatchWire
from app.evaluation.golden_inference_scope_v5 import strict_json


LIVE_STATUS = "offline_only"
LIVE_BLOCK_REASON = "contextual_candidate_requires_offline_qualification"


def require_live_qualification():
    # Deliberate retirement of the currently failed candidate, not a missing
    # user permission. No CLI override and no implicit retry/fallback exist.
    raise ValueError(LIVE_BLOCK_REASON)


def correction_blockers(state):
    source = state.inputs.source
    duplicates = defaultdict(list)
    for key, row in state.entries().items():
        if row["type"] != "claim":
            continue
        ref = row["value"]["quote_ref"]
        quote = source.resolve(ref)
        if quote == source.blocks[ref["block"]-1][1]:
            duplicates[(row["audit_index"], ref["block"])].append(key)
    blockers = [dict(code="full_block_duplicates_cannot_be_reassigned_or_shrunk", targets=keys)
        for keys in duplicates.values() if len(keys) > 1]
    # These codes require a claim change. Issue/score/heading edits alone
    # cannot make an unchanged invalid claim pass the final validator.
    claim_change_required = {"direct_result_number_not_in_evidence",
        "direct_result_value_source_required", "scope_anchor_invalid",
        "context_anchor_invalid_requires_reassessment", "direct_result_scope_must_be_null",
        "table_scope_antecedent_missing"}
    required = set()
    for diagnostic in strict_json(state.diagnostics_json).get("errors", []):
        if "per_target_validation_errors" not in diagnostic.get("codes", []):
            continue
        codebook = diagnostic["codebook"]
        for target, codes in diagnostic["targets"]:
            if target.startswith("c") and any(codebook[n-1] in claim_change_required for n in codes):
                required.add(target)
    limit = PatchWire.model_json_schema()["properties"]["claim_updates"]["maxItems"]
    if len(required) > limit:
        blockers.append(dict(code="required_claim_updates_exceed_patch_capacity",
            targets=sorted(required), limit=limit))
    return blockers


def require_correction_reachability(state):
    if correction_blockers(state):
        raise ValueError("contextual_correction_known_unreachable")
