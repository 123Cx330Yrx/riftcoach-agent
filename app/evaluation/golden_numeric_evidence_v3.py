"""Cited, included, same-role aggregates and contextual queue identifiers.

Computability remains separate from semantic approval. Never rewrite claims.
"""
from decimal import Decimal, ROUND_HALF_UP
import math
import re

from app.evaluation.golden_fact_candidate import NUMBER
from app.evaluation.golden_numeric_evidence_v2 import numeric_support as previous

METRICS = ("kills", "deaths", "assists", "kda", "cs_per_min", "gold_per_min",
           "damage_per_min", "vision_score", "deaths_before_10", "deaths_before_15")
QUEUE = re.compile(r"队列(?:编号|ID)?\s*[:：]?\s*([0-9]+)", re.IGNORECASE)


def numeric_support(claim, pack):
    ledger = previous(claim, pack)
    roles = {}
    queues = {}
    for ref in dict.fromkeys(claim.evidence_refs):
        if not ref.startswith("facts:recent_match:") or ref not in pack["provenance"]:
            continue
        row = pack["facts"][ref]
        queue = row.get("queue_id")
        if type(queue) is int and queue >= 0:
            queues.setdefault(str(queue), []).append((ref, "/queue_id"))
        if row.get("included_in_aggregate") is True and row.get("role"):
            roles.setdefault(row["role"], []).append((ref, row))
    candidates = []
    for rows in roles.values():
        candidates.append((Decimal(len(rows)), "cited_role_count", [(ref, "/included_in_aggregate") for ref, _ in rows]))
        for metric in METRICS:
            values = [(Decimal(str(row[metric])), (ref, "/" + metric)) for ref, row in rows
                      if type(row.get(metric)) in (int, float) and math.isfinite(row[metric])
                      and 0 <= row[metric] < 1e15]
            if not values:
                continue
            numbers = sorted(n for n, _ in values)
            refs = [ref for _, ref in values]
            middle = len(numbers) // 2
            median = numbers[middle] if len(numbers) % 2 else (numbers[middle - 1] + numbers[middle]) / 2
            candidates.extend(((sum(numbers) / len(numbers), "cited_role_mean", refs),
                               (median, "cited_role_median", refs)))
    queue_spans = {(m.start(1), m.end(1)) for m in QUEUE.finditer(claim.quote)}
    for item in ledger:
        token = item["token"]
        occurrences = [m for m in NUMBER.finditer(claim.quote) if m.group() == token]
        queue_occurrences = [m for m in occurrences if m.span() in queue_spans]
        # An identifier must match an actual cited identifier, never a coincidental metric.
        if queue_occurrences:
            queue_supported = token in queues
            has_metric_occurrence = len(queue_occurrences) != len(occurrences)
            if not has_metric_occurrence:
                item.update(supported=queue_supported, candidates=([{"op": "queue_id", "operands": queues[token]}] if queue_supported else []), omitted_candidates=0)
                continue
            if not queue_supported:
                item.update(supported=False, candidates=[], omitted_candidates=0)
                continue
        if item["supported"]:
            continue
        places = len(token.split(".")[1]) if "." in token else 0
        if places > 6 or len(token) > 20:
            continue
        matches = [{"op": op, "operands": refs} for number, op, refs in candidates
                   if (op != "cited_role_count" or re.search(r"(?<![0-9.])" + re.escape(token) + r"\s*[局场]", claim.quote))
                   and number.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP) == Decimal(token)]
        item.update(supported=bool(matches), candidates=matches[:8], omitted_candidates=max(0, len(matches)-8))
    return ledger
