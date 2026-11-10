"""Deterministic arithmetic navigation for every supplied complete cohort.

The report contributes only to the source identity. Its prose never chooses a
cohort, metric or operation. A reviewer must choose those bindings and justify
their relevance; arithmetic availability does not establish entailment.
"""
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext

from app.evaluation import golden_comparison_reassessment as comparison
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_review_experiment import SourceIndex


COLUMNS = ("metric_index", "win_mean", "loss_mean", "all_pairs", "mean", "median", "missing_refs")


def build(inputs, *, include_role_contrasts=False):
    """Return one lossless member ledger and arithmetic table per cohort.

    Winning/losing means and pairwise direction retain the existing comparison
    contract. Whole-cohort summaries use the raw decimal values, never the
    rounded winning/losing means. Decimal strings use a fixed 28-significant-
    digit context; the final review's existing validator still checks the
    reviewer-selected operands and rounds to the report's displayed precision.
    """
    pack = strict_json(inputs.pack_json)
    if SourceIndex.build(inputs.source.report, pack) != inputs.source:
        raise ValueError("computed_source_changed")
    facts = pack["facts"]
    raw = {}
    for ref, key in enumerate(inputs.source.evidence_keys, 1):
        if not key.startswith("facts:recent_match:"):
            continue
        row, origin = facts[key], pack["provenance"].get(key, {})
        if not isinstance(row, dict) or not isinstance(origin, dict):
            raise ValueError("computed_match_row_invalid")
        if row.get("included_in_aggregate") is True:
            raw[ref] = row

    # A fixed context prevents callers' ambient decimal settings from changing
    # this derived source evidence. This matches the final validator's normal
    # Decimal precision and preserves its established comparison rendering.
    with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
        comparisons = comparison.catalog(inputs)
        cohorts = {}
        exact_gaps = {}
        for name, group in comparisons["cohorts"].items():
            members = [ref for ref, row in raw.items()
                       if name == "selected" or row.get("role") == name]
            unclassified = [ref for ref in members if type(raw[ref].get("win")) is not bool]
            rows = []
            gaps = []
            for index, existing in enumerate(group["rows"], 1):
                metric, win_mean, loss_mean, relation, missing = existing
                mean = median = None
                if group["complete"] and not missing:
                    values = sorted(Decimal(str(raw[ref][metric])) for ref in members)
                    mean = format(sum(values) / len(values), "f")
                    mid = len(values) // 2
                    median = format(values[mid] if len(values) % 2 else
                                    (values[mid - 1] + values[mid]) / 2, "f")
                rows.append([index, win_mean, loss_mean, relation, mean, median, missing])
                gap = None
                if group["complete"] and not missing and group["wins"] and group["losses"]:
                    w = [Decimal(str(raw[ref][metric])) for ref in group["wins"]]
                    l = [Decimal(str(raw[ref][metric])) for ref in group["losses"]]
                    gap = sum(w) / len(w) - sum(l) / len(l)
                gaps.append(gap)
            cohorts[name] = dict(wins=group["wins"], losses=group["losses"],
                                 unclassified_refs=unclassified, complete=group["complete"], rows=rows)
            exact_gaps[name] = gaps

        contrasts = {}
        if include_role_contrasts:
            for name, gaps in exact_gaps.items():
                if name == "selected":
                    continue
                selected = exact_gaps["selected"]
                contrasts[name] = [
                    [index, format(whole, "f") if whole is not None else None,
                     format(role, "f") if role is not None else None,
                     format(whole - role, "f") if whole is not None and role is not None else None]
                    for index, (whole, role) in enumerate(zip(selected, gaps), 1)]

    result = dict(source_digest=inputs.source.source_digest,
                complete_source_rows=comparisons["complete_source_rows"],
                metrics=list(comparison.METRICS), columns=list(COLUMNS),
                numeric_format=dict(values="decimal_strings", mean_median_precision=28,
                                    mean_median_rounding="ROUND_HALF_EVEN", win_loss_places=2,
                                    win_loss_rounding="ROUND_HALF_UP", ratios="0..1"),
                cohorts=cohorts)
    if include_role_contrasts:
        result["role_contrasts"] = dict(
            columns=["metric_index", "selected_win_minus_loss", "role_win_minus_loss", "selected_gap_minus_role_gap"],
            precision=28, rounding="ROUND_HALF_EVEN", cohorts=contrasts,
            meaning="Descriptive change in win-minus-loss means after retaining one role; not a causal contribution. "
                    "Member refs/completeness/missing values are in cohorts. Null means not computable; zero is a value.")
    return result
