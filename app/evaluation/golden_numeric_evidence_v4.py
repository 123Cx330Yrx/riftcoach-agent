"""Explicitly labelled mixed-source arithmetic, without mixing role cohorts."""
from decimal import Decimal, ROUND_HALF_UP
import math
from app.evaluation.golden_numeric_evidence_v3 import numeric_support as previous, METRICS


def numeric_support(claim, pack):
    ledger = previous(claim, pack)
    if "混合" not in claim.quote or "facts:recent_aggregate" not in claim.evidence_refs:
        return ledger
    comparison = pack["facts"].get("facts:recent_aggregate", {}).get("win_loss_comparison", {})
    candidates = []
    for metric in METRICS:
        left = comparison.get("wins", {}).get(metric)
        right = comparison.get("losses", {}).get(metric)
        if not all(type(n) in (int, float) and math.isfinite(n) and 0 <= n < 1e15 for n in (left, right)):
            continue
        refs = [("facts:recent_aggregate", f"/win_loss_comparison/{group}/{metric}") for group in ("wins", "losses")]
        candidates.append((Decimal(str(left))-Decimal(str(right)), refs))
    for item in ledger:
        if item["supported"]:
            continue
        token = item["token"]
        places = len(token.split(".")[1]) if "." in token else 0
        if places > 6 or len(token) > 20:
            continue
        matches = [{"op": "source_reported_mixed_difference", "operands": refs} for n, refs in candidates
                   if n.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP) == Decimal(token)]
        item.update(supported=bool(matches), candidates=matches[:8], omitted_candidates=max(0, len(matches)-8))
    return ledger
