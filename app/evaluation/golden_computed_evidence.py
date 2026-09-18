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


def build(inputs):
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
        for name, group in comparisons["cohorts"].items():
            members = [ref for ref, row in raw.items()
                       if name == "selected" or row.get("role") == name]
            unclassified = [ref for ref in members if type(raw[ref].get("win")) is not bool]
            rows = []
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
            cohorts[name] = dict(wins=group["wins"], losses=group["losses"],
                                 unclassified_refs=unclassified, complete=group["complete"], rows=rows)

    return dict(source_digest=inputs.source.source_digest,
                complete_source_rows=comparisons["complete_source_rows"],
                metrics=list(comparison.METRICS), columns=list(COLUMNS),
                numeric_format=dict(values="decimal_strings", mean_median_precision=28,
                                    mean_median_rounding="ROUND_HALF_EVEN", win_loss_places=2,
                                    win_loss_rounding="ROUND_HALF_UP", ratios="0..1"),
                cohorts=cohorts)
