"""Program-side numeric support search over cited, allowlisted facts.

This proves computability from cited values, not the prose's semantic meaning.
It never changes quotes or classifies ability/causal assertions.
"""
from decimal import Decimal, ROUND_HALF_UP
import math

from app.evaluation.golden_fact_candidate import NUMBER

_FIELDS = {"games", "wins", "losses", "games_analyzed", "win_rate", "valid", "missing_or_invalid",
           "kills", "deaths", "assists", "kda", "cs_per_min", "gold_per_min", "damage_per_min", "vision_score",
           "kill_participation", "damage_share", "gold_share", "kill_participation_percent", "damage_share_percent",
           "gold_share_percent", "deaths_before_10", "deaths_before_15", "game_duration_seconds"}
_RATIOS = {"kill_participation", "damage_share", "gold_share"}


def _leaves(value, path=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _leaves(item, path + "/" + key)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from _leaves(item, path + "/" + str(i))
    elif type(value) in (int, float) and math.isfinite(value) and 0 <= value < 1e15:
        yield path, Decimal(str(value))


def numeric_support(claim, pack):
    """Return a local ledger; numeric operators need not be emitted by the model."""
    candidates = []
    comparable = []
    for ref in claim.evidence_refs:
        if ref not in pack["provenance"]:
            continue
        value = pack["facts"][ref]
        for path, number in _leaves(value):
            leaf = path.rsplit("/", 1)[-1]
            role_mean = ref.startswith("role:") and path == "/mean"
            if leaf not in _FIELDS and not role_mean:
                continue
            candidates.append((number, "value", [(ref, path)]))
            if ref.startswith("facts:recent_match:"):
                if leaf in _RATIOS and number <= 1:
                    candidates.append((number * 100, "percent", [(ref, path)]))
                if leaf == "game_duration_seconds":
                    candidates.append((number / 60, "minutes", [(ref, path)]))
                if leaf in ("deaths_before_10", "deaths_before_15"):
                    candidates.append((Decimal(leaf.rsplit("_", 1)[1]), "metric_window", [(ref, path)]))
            if role_mean:
                comparable.append((ref.split(":")[1], ref.rsplit(":", 1)[1], number, ref, path))
    for role, metric, left, lref, lpath in comparable:
        for rrole, rmetric, right, rref, rpath in comparable:
            if lref == rref or (role, metric) != (rrole, rmetric):
                continue
            operands = [(lref, lpath), (rref, rpath)]
            candidates.append((left - right, "difference", operands))
            if right != 0:
                candidates.append((left / right * 100, "ratio_percent", operands))
    ledger = []
    for token in dict.fromkeys(NUMBER.findall(claim.quote)):
        places = len(token.split(".")[1]) if "." in token else 0
        matched = []
        if places <= 6 and len(token) <= 20:
            target = Decimal(token)
            matched = [(op, refs) for number, op, refs in candidates
                       if abs(number) < Decimal("1e18") and number.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP) == target]
        ledger.append({"token": token, "supported": bool(matched),
                       "candidates": [{"op": op, "operands": refs} for op, refs in matched[:8]],
                       "omitted_candidates": max(0, len(matched) - 8)})
    return ledger
