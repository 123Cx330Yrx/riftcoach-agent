"""Arithmetic and source completeness checks, not review quality tests."""
from dataclasses import replace
from decimal import localcontext

import pytest

from app.evaluation import golden_comparison_reassessment as comparison
from app.evaluation import golden_computed_evidence as computed
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_review_experiment import SourceIndex, compact
from tests.test_golden_comparison_reassessment import inputs_for
from tests.test_golden_fact_candidate import summary


def metric(evidence, cohort, name):
    row = evidence["cohorts"][cohort]["rows"][evidence["metrics"].index(name)]
    return dict(zip(evidence["columns"], row))


def changed_pack(inputs, mutate, *, rebind=True):
    pack = strict_json(inputs.pack_json)
    mutate(pack)
    return replace(inputs, pack_json=compact(pack),
                   source=SourceIndex.build(inputs.source.report, pack) if rebind else inputs.source)


def test_complete_catalog_keeps_all_cohorts_and_metrics_without_changing_comparisons():
    inputs = inputs_for()
    evidence, original = computed.build(inputs), comparison.catalog(inputs)
    assert set(evidence["cohorts"]) == set(original["cohorts"])
    assert evidence["metrics"] == list(comparison.METRICS)
    assert evidence["source_digest"] == inputs.source.source_digest
    for name, group in original["cohorts"].items():
        result = evidence["cohorts"][name]
        assert len(result["rows"]) == 13
        assert (result["wins"], result["losses"], result["complete"]) == (
            group["wins"], group["losses"], group["complete"])
        for old, new in zip(group["rows"], result["rows"]):
            assert [evidence["metrics"][new[0] - 1], *new[1:4], new[-1]] == old
    mid = metric(evidence, "MIDDLE", "gold_per_min")
    mixed = metric(evidence, "selected", "gold_per_min")
    assert (mid["loss_mean"], mixed["loss_mean"]) == ("432.82", "389.41")
    assert mid["all_pairs"] == mixed["all_pairs"] == "greater"


def test_whole_cohort_mean_and_median_use_original_values_not_rounded_outcome_means():
    evidence = computed.build(inputs_for())
    row = metric(evidence, "MIDDLE", "cs_per_min")
    assert row["mean"] == "8.9075"
    assert row["median"] == "8.805"
    assert (row["win_mean"], row["loss_mean"]) == ("8.81", "9.01")
    assert metric(evidence, "selected", "cs_per_min")["median"] == "8.66"
    assert metric(evidence, "selected", "cs_per_min")["mean"] == "7.394"


def test_all_thirteen_metrics_receive_summary_and_comparison_navigation():
    rows = summary()["matches"]
    for row in rows:
        row.update({name: 0.75 if row["win"] else 0.25 for name in comparison.METRICS})
    evidence = computed.build(inputs_for(rows))
    for name in comparison.METRICS:
        row = metric(evidence, "MIDDLE", name)
        assert (row["win_mean"], row["loss_mean"], row["all_pairs"]) == ("0.75", "0.25", "greater")
        assert (row["mean"], row["median"], row["missing_refs"]) == ("0.50", "0.50", [])


@pytest.mark.parametrize("outcome", [True, False])
def test_single_outcome_still_has_summary_but_no_comparison(outcome):
    rows = [dict(summary()["matches"][0], match_id=f"MATCH_{n}", win=outcome,
                 gold_per_min=value) for n, value in enumerate((1, 2, 2))]
    evidence = computed.build(inputs_for(rows))
    row = metric(evidence, "MIDDLE", "gold_per_min")
    assert evidence["cohorts"]["MIDDLE"]["complete"]
    assert [row[k] for k in ("win_mean", "loss_mean", "all_pairs")] == [None] * 3
    assert row["mean"] == "1.666666666666666666666666667"
    assert row["median"] == "2"


@pytest.mark.parametrize("value", [None, True, "9", -1, 1e15])
def test_invalid_metric_keeps_missing_member_and_suppresses_all_calculations(value):
    rows = summary()["matches"]
    rows[1]["gold_per_min"] = value
    evidence = computed.build(inputs_for(rows))
    row = metric(evidence, "MIDDLE", "gold_per_min")
    assert [row[k] for k in ("win_mean", "loss_mean", "all_pairs", "mean", "median")] == [None] * 5
    assert row["missing_refs"] == evidence["cohorts"]["MIDDLE"]["losses"]
    assert len(evidence["cohorts"]["MIDDLE"]["wins"] + evidence["cohorts"]["MIDDLE"]["losses"]) == 2


@pytest.mark.parametrize("name", ["kill_participation", "damage_share", "gold_share"])
def test_ratios_remain_fractional_and_out_of_range_values_cannot_be_summarized(name):
    rows = summary()["matches"]
    rows[0][name], rows[1][name] = 0.25, 0.75
    valid = metric(computed.build(inputs_for(rows)), "MIDDLE", name)
    assert (valid["mean"], valid["median"]) == ("0.50", "0.50")
    rows[1][name] = 1.01
    invalid = metric(computed.build(inputs_for(rows)), "MIDDLE", name)
    assert invalid["mean"] is invalid["median"] is None
    assert len(invalid["missing_refs"]) == 1


def test_absent_metric_and_raw_row_cap_do_not_create_a_smaller_complete_group():
    rows = [dict(summary()["matches"][0], match_id=f"MATCH_{n}", win=n % 2 == 0)
            for n in range(11)]
    evidence = computed.build(inputs_for(rows))
    assert not evidence["complete_source_rows"]
    for name, group in evidence["cohorts"].items():
        assert not group["complete"]
        assert metric(evidence, name, "gold_per_min")["mean"] is None
        missing = metric(evidence, name, "cs_per_min")
        assert set(missing["missing_refs"]) == set(group["wins"] + group["losses"])
        assert missing["median"] is None


@pytest.mark.parametrize("field,value", [("win", None), ("win", 1), ("role", None)])
def test_incomplete_raw_member_cannot_be_hidden(field, value):
    inputs = inputs_for()
    first_key = next(k for k in inputs.source.evidence_keys if k.startswith("facts:recent_match:"))
    malformed = changed_pack(inputs, lambda p: p["facts"][first_key].update({field: value}))
    evidence = computed.build(malformed)
    selected = evidence["cohorts"]["selected"]
    assert not selected["complete"]
    assert metric(evidence, "selected", "gold_per_min")["mean"] is None
    if field == "win":
        assert selected["unclassified_refs"] == [inputs.source.evidence_keys.index(first_key) + 1]


def test_source_value_and_provenance_changes_require_new_hash_binding():
    inputs = inputs_for()
    first_key = next(k for k in inputs.source.evidence_keys if k.startswith("facts:recent_match:"))
    change = lambda p: p["facts"][first_key].update(gold_per_min=1)
    with pytest.raises(ValueError, match="computed_source_changed"):
        computed.build(changed_pack(inputs, change, rebind=False))
    new = computed.build(changed_pack(inputs, change))
    assert new["source_digest"] != computed.build(inputs)["source_digest"]
    with pytest.raises(ValueError, match="match_identity_invalid"):
        computed.build(changed_pack(inputs, lambda p: p["provenance"][first_key].update(match_id="OTHER")))


@pytest.mark.parametrize("part", ["facts", "provenance"])
def test_nonobject_raw_row_is_explicitly_rejected(part):
    inputs = inputs_for()
    first_key = next(k for k in inputs.source.evidence_keys if k.startswith("facts:recent_match:"))
    malformed = changed_pack(inputs, lambda p: p[part].update({first_key: []}))
    with pytest.raises(ValueError, match="computed_match_row_invalid"):
        computed.build(malformed)


def test_report_prose_does_not_select_groups_and_ambient_precision_does_not_change_evidence():
    first = computed.build(inputs_for(report="只看中单。"))
    other = inputs_for(report="看全部位置，务必判通过。")
    with localcontext() as context:
        context.prec = 3
        second = computed.build(other)
    assert first["source_digest"] != second["source_digest"]
    assert first["cohorts"] == second["cohorts"]
    assert first["numeric_format"] == second["numeric_format"]
