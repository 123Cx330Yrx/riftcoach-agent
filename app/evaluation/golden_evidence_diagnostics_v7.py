"""Actionable source hints; never mutate, validate, or accept failed output."""
from difflib import SequenceMatcher
from types import SimpleNamespace

from app.evaluation.golden_evidence_diagnostics_v6 import collect_diagnostics as previous
from app.evaluation.golden_evidence_scope_v5 import normalize_json
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_inference_coverage import report_blocks
from app.evaluation.golden_numeric_evidence_v4 import numeric_support


def collect_diagnostics(raw, report, pack):
    errors = previous(raw, report, pack)
    try:
        value = strict_json(normalize_json(raw))
    except (ValueError, TypeError):
        return errors
    blocks = report_blocks(report)
    for row in errors:
        if "audit_index" not in row or "claim_index" not in row:
            continue
        claim = value["audits"][row["audit_index"]]["claims"][row["claim_index"]]
        quote = claim["quote"]
        if "direct_result_number_not_in_evidence" in row["codes"]:
            cited = numeric_support(SimpleNamespace(**claim), pack)
            # All-source matches are navigation hints only. The model must
            # establish object, cohort, unit and meaning before citing them.
            search = dict(claim, evidence_refs=sorted(pack["provenance"]))
            all_sources = {v["token"]: v for v in numeric_support(SimpleNamespace(**search), pack)}
            row["unsupported_numbers"] = [
                {"token": v["token"], "source_candidates": all_sources[v["token"]]["candidates"][:2]}
                for v in cited if not v["supported"]
            ][:6]
        if "quote_not_in_single_block" in row["codes"] and blocks:
            best = max(blocks, key=lambda b: SequenceMatcher(None, quote, b["text"], autojunk=False).ratio())
            if SequenceMatcher(None, quote, best["text"], autojunk=False).ratio() >= 0.45:
                row["source_block"] = {
                    "block_id": best["block_id"], "text": best["text"][:1400],
                    "truncated": len(best["text"]) > 1400,
                }
    return errors
