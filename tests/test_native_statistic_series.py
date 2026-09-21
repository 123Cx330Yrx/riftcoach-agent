"""Lossless statistic navigation and source binding, not model quality tests."""
from copy import deepcopy

import pytest

from app.evaluation import golden_semantic_sources as sources
from app.evaluation.golden_computed_evidence import build
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_review_source_catalog import SourceEntry, build_catalog
from tests.test_golden_comparison_reassessment import inputs_for
from tests.test_golden_fact_candidate import summary


SERIES = ("win_mean", "loss_mean", "all_pairs", "cohort_mean", "cohort_median", "missing_refs")
COLUMNS = ["metric_index", "win_mean", "loss_mean", "all_pairs", "mean", "median", "missing_refs"]


def restore_rows(evidence):
    restored = deepcopy(evidence)
    assert restored.pop("series_order") == "metrics"
    restored["columns"] = COLUMNS.copy()
    for group in restored["cohorts"].values():
        series = [group.pop(field) for field in SERIES]
        assert all(len(values) == len(restored["metrics"]) for values in series)
        group["rows"] = [[index, *values] for index, values in enumerate(zip(*series), 1)]
    return restored


def vision_inputs():
    rows = [dict(match_id=f"SERIES_{index}", included_in_aggregate=True,
                 role="MIDDLE", win=win, vision_score=vision, gold_per_min=0)
            for index, (win, vision) in enumerate(((True, 32), (False, 30), (False, 38), (True, 35)))]
    rows.append(dict(match_id="SERIES_SUPPORT", included_in_aggregate=True,
                     role="UTILITY", win=False, vision_score=90, gold_per_min=0))
    return inputs_for(rows)


@pytest.mark.parametrize("include_role_contrasts", [False, True])
@pytest.mark.parametrize("fixture", ["ordinary", "distinct_statistics", "incomplete"])
def test_all_rows_and_metadata_reconstruct_exactly(fixture, include_role_contrasts):
    if fixture == "ordinary":
        inputs = inputs_for()
    elif fixture == "distinct_statistics":
        inputs = vision_inputs()
    else:
        inputs = inputs_for([dict(summary()["matches"][0], match_id=f"CAP_{index}", win=index % 2 == 0)
                             for index in range(11)])
    before = deepcopy(inputs)
    original = build(inputs, include_role_contrasts=include_role_contrasts)
    projected = sources.request_data(inputs, include_role_contrasts=include_role_contrasts,
                                     computed_layout="statistic_series")["computed_evidence"]
    assert restore_rows(projected) == original
    assert inputs == before
    assert "columns" not in projected
    assert all("rows" not in group for group in projected["cohorts"].values())
    if fixture == "incomplete":
        assert not projected["complete_source_rows"]
        assert all(not group["complete"] for group in projected["cohorts"].values())
    if include_role_contrasts:
        assert projected["role_contrasts"] == original["role_contrasts"]


def test_outcome_means_whole_mean_median_zero_and_null_keep_their_own_fields():
    evidence = sources.request_data(vision_inputs(), computed_layout="statistic_series")["computed_evidence"]
    middle, support = (evidence["cohorts"][name] for name in ("MIDDLE", "UTILITY"))
    vision = evidence["metrics"].index("vision_score")
    assert [middle[field][vision] for field in SERIES] == ["33.50", "34.00", "overlap", "33.75", "33.5", []]
    assert [support[field][vision] for field in SERIES] == [None, None, None, "90", "90", []]
    gold = evidence["metrics"].index("gold_per_min")
    assert middle["win_mean"][gold] == middle["loss_mean"][gold] == "0.00"
    assert middle["cohort_mean"][gold] == middle["cohort_median"][gold] == "0"
    missing = evidence["metrics"].index("cs_per_min")
    assert [middle[field][missing] for field in SERIES[:-1]] == [None] * 5
    assert set(middle["missing_refs"][missing]) == set(middle["wins"] + middle["losses"])


@pytest.mark.parametrize("include_role_contrasts", [False, True])
def test_request_selected_value_and_catalog_hash_bind_the_same_projection(include_role_contrasts):
    inputs = vision_inputs()
    options = dict(include_role_contrasts=include_role_contrasts)
    rows_catalog = sources.source_catalog(inputs, **options)
    rows_data = sources.request_data(inputs, **options)
    series_options = dict(**options, computed_layout="statistic_series")
    series_catalog = sources.source_catalog(inputs, **series_options)
    data = sources.request_data(inputs, **series_options)
    number = next(number for number, entry in series_catalog.items() if entry.key == sources.COMPUTED_KEY)
    selected = sources.resolve_refs(inputs, [number], **series_options)[0]
    original = sources.resolve_refs(inputs, [number], **options)[0]
    assert selected["value"] == data["computed_evidence"]
    assert compact(selected["value"]) == series_catalog[number].value_json
    assert selected["value_sha256"] == digest(compact(data["computed_evidence"]))
    assert selected["catalog_sha256"] == data["source_roots"]["catalog_sha256"]
    assert selected["catalog_sha256"] != original["catalog_sha256"]
    assert selected["value_sha256"] != original["value_sha256"]
    assert selected["input_sha256"] == original["input_sha256"] == digest(inputs.data_json)
    assert selected["value"]["source_digest"] == original["value"]["source_digest"]
    assert not selected["semantic_approval"]
    assert list(series_catalog) == list(rows_catalog)
    assert {key: value for key, value in series_catalog.items() if key != number} == {
        key: value for key, value in rows_catalog.items() if key != number}
    assert data["source_roots"]["additional"] == rows_data["source_roots"]["additional"]
    assert {key: value for key, value in data.items() if key not in ("source_roots", "computed_evidence")} == {
        key: value for key, value in rows_data.items() if key not in ("source_roots", "computed_evidence")}
    selected["value"]["cohorts"].clear()
    assert sources.resolve_refs(inputs, [number], **series_options)[0]["value"] == data["computed_evidence"]


@pytest.mark.parametrize("include_role_contrasts", [False, True])
def test_default_retains_legacy_values_numbering_and_catalog_identity(include_role_contrasts):
    inputs = vision_inputs()
    options = dict(include_role_contrasts=include_role_contrasts)
    original = build_catalog(inputs)
    calculated = build(inputs, **options)
    expected_entries = [*original.entries, SourceEntry(sources.COMPUTED_KEY, "computed_evidence",
                        ("computed_evidence",), compact(calculated))]
    expected_hash = digest(compact(dict(version=sources.ROOTS_VERSION, input_sha256=original.input_sha256,
                                      entries=[entry.metadata() for entry in expected_entries])))
    catalog = sources.source_catalog(inputs, **options)
    data = sources.request_data(inputs, **options)
    assert list(catalog.values()) == expected_entries
    assert data["computed_evidence"] == calculated
    assert data["source_roots"]["catalog_sha256"] == expected_hash
    assert sources.source_catalog(inputs, computed_layout="rows", **options) == catalog
    assert sources.request_data(inputs, computed_layout="rows", **options) == data
    assert sources.resolve_refs(inputs, list(catalog), computed_layout="rows", **options) == sources.resolve_refs(
        inputs, list(catalog), **options)
    assert strict_json(catalog[len(catalog)].value_json) == calculated


def test_unknown_layout_is_rejected_by_every_entrypoint():
    inputs = inputs_for()
    for operation in (sources.request_data, sources.source_catalog,
                      lambda current, **options: sources.resolve_refs(current, [], **options)):
        with pytest.raises(ValueError, match="semantic_computed_layout_unknown"):
            operation(inputs, computed_layout="unknown")


@pytest.mark.parametrize("mutation", ["column_order", "metric_order", "missing_row", "extra_cell", "field_collision"])
def test_changed_upstream_shape_cannot_silently_drop_or_mislabel_values(monkeypatch, mutation):
    inputs = inputs_for()
    evidence = build(inputs)
    group = evidence["cohorts"]["MIDDLE"]
    if mutation == "column_order":
        evidence["columns"][1:3] = reversed(evidence["columns"][1:3])
    elif mutation == "metric_order":
        group["rows"].reverse()
    elif mutation == "missing_row":
        group["rows"].pop()
    elif mutation == "extra_cell":
        group["rows"][0].append("unmapped")
    else:
        group["cohort_mean"] = "unmapped"
    monkeypatch.setattr(sources, "computed_evidence", lambda *args, **kwargs: evidence)
    with pytest.raises(ValueError, match="semantic_computed_"):
        sources.request_data(inputs, computed_layout="statistic_series")
