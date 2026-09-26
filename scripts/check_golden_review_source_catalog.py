"""Offline full-report source matrix, labelled as an analyst-authored audit.

Uses frozen contextual_01 only. No model, no relabeling, no changed receipts;
the matrix/expected interpretation must never be included in a model request.
"""
import argparse
from collections import Counter
from dataclasses import replace
import hashlib
from pathlib import Path

from app.evaluation.golden_comparison_reassessment import catalog as comparisons
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_source_catalog import build_catalog
from app.evaluation.golden_review_experiment import compact, digest
from scripts.check_golden_reassessment_feasibility import measured
from scripts.run_golden_source_first_probe import prepare, BASELINE

REPORT_SHA = "84e4b38931255f7a3b7e5ce322987eb997302c7f46d922a7aa8ab4682479b219"


def check(args):
    state, request, _ = prepare(args)
    inputs = state.inputs
    if digest(inputs.source.report) != REPORT_SHA:
        raise ValueError("source_matrix_frozen_report_changed")
    sources = build_catalog(inputs)
    for row in sources.entries:
        assert compact(sources.resolve(inputs, row.key, kind=row.kind)) == row.value_json
    legacy = lambda n: "legacy/" + inputs.source.evidence_keys[n - 1]
    matches = [legacy(n) for n in (7, 8, 9, 10, 11)]
    mid = [legacy(n) for n in (7, 9, 10, 11)]
    boundary = [legacy(26), "source/deterministic"]
    k = lambda n: "knowledge/K" + str(n)
    goals = ["source/position"]
    opgg = [legacy(n) for n in (2, 3, 5)]
    # This reviewed mapping is evidence for addressability, not generated labels
    # or an executable rule choosing the meaning of arbitrary report text.
    obligations = {
        3: (matches + [legacy(6), legacy(12), k(1)], "Counts, actual queue, distinct mixed/MIDDLE arithmetic, sample scope", []),
        5: (mid + [k(1)], "Role mean and single-game fact; deny inference to ability", []),
        6: ([legacy(6), legacy(7), legacy(11)], "Two individual wins versus whole-sample mean, not win/loss groups", []),
        7: ([legacy(8)] + boundary, "Single support vision value and denial of ability inference", []),
        10: (mid + boundary, "Cross-paragraph four-MIDDLE scope, not selected-five arithmetic", [3]),
        11: ([legacy(8), legacy(10)] + boundary, "Individual outliers do not establish champion strength", []),
        13: (matches + [legacy(6)], "Explicit mixed sample table; verify arithmetic and original precision", [14]),
        14: (matches + [legacy(6), k(1), k(3)], "Mixed and MIDDLE groups stay distinct; one-game hypothesis", [3, 13]),
        16: ([legacy(10), legacy(11)], "Explicit two-game subset, not complete win/loss comparison", []),
        17: (mid + [k(3)], "Question about possible causes, not a causal assertion", [3, 14]),
        18: (opgg[:2] + goals + ["source/external_bundle"], "Dated mid snapshots and conditional action; observed player is not reader", [20, 27]),
        20: (goals, "Explicit unspecified goal and empty training positions", []),
        21: (mid + goals + [k(2)] + opgg[:2], "Median CS and whole-MIDDLE death mean; conditional practice option", [18, 20]),
        22: ([legacy(8), legacy(5)] + goals, "Single support game and dated support snapshot; conditional option", [20, 27]),
        23: (goals + boundary, "Training intent must not relabel history or establish long-term role", []),
        25: (matches + [legacy(12), legacy(13), "source/data_dragon"], "Supplied data-source/version identity and actual sample limits", []),
        26: ([k(1), k(2), k(3)], "Exact knowledge source IDs/titles/content, not match-count metadata", []),
        27: (opgg + ["source/official_patch", "source/external_bundle"] + boundary,
             "Separate OP.GG scope from official patch identity/date; no supplied balance text", []),
        28: (boundary, "Declared statistics/video limitation; generic indexed scope already existed", []),
    }
    matrix = []
    for number, (_, text) in enumerate(inputs.source.blocks, 1):
        if text.startswith("#"):
            row = dict(block=number, report_kind="navigation", sources=[], meaning="Heading with no independent factual assertion", context_blocks=[])
        else:
            keys, meaning, contexts = obligations[number]
            row = dict(block=number, report_kind="review_obligation", sources=list(dict.fromkeys(keys)),
                       meaning=meaning, context_blocks=contexts)
            for key in row["sources"]:
                sources.get(key)
        row["quote_sha256"] = digest(text)
        matrix.append(row)
    literal_checks = []
    for key, kind, path, expected in (
        ("source/position", "position_context", ("goal_source",), "unspecified"),
        ("source/position", "position_context", ("training_positions",), []),
        ("knowledge/K1", "knowledge", ("source_id",), "01_metric_interpretation.md"),
        ("knowledge/K2", "knowledge", ("title",), "避免伪精确目标"),
        ("knowledge/K3", "knowledge", ("title",), "补刀与经济"),
        ("source/official_patch", "official_patch", ("patch_version",), "16.17"),
        ("source/official_patch", "official_patch", ("published_at",), "2026-08-25T18:00:00Z"),
        ("source/data_dragon", "static_catalog", ("version",), "16.17.1")):
        literal_checks.append(sources.check_literal(inputs, key, kind=kind, path=path, expected=expected))
    # Compare only envelope size of naively appending the address manifest.
    # This is NOT the proposed final request or full workflow qualification.
    manifest = sources.manifest()
    messages = list(request.messages)
    messages[1] = replace(messages[1], content=messages[1].content + "\n" + compact(manifest))
    size_projection = measured(replace(request, messages=tuple(messages)))
    messages[1] = replace(request.messages[1], content=request.messages[1].content + "\n" + compact(sources.prompt_index()))
    compact_projection = measured(replace(request, messages=tuple(messages)))
    evidence = comparisons(inputs)
    raw_paths = [BASELINE / name for name in ("input.json", "response-001.json", "response-002.json", "result.json")]
    new_dir = Path("data/runs/inference_development/source-first-probe-e23c90d-v1")
    raw_paths += [new_dir / name for name in ("plan.json", "request.json", "response.json", "result.json")]
    hashes = {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in raw_paths}
    # Check the latest raw receipts against the pre-existing audit, not only
    # against hashes newly calculated by this script.
    old_audit = strict_json(Path("data/evaluation/results/golden_source_first_result_e23c90d.json").read_text(encoding="utf-8"))
    for path, expected in old_audit["source_hashes"].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError("source_matrix_receipt_changed")
    return dict(provider_calls=0, matrix_kind="analyst_authored_source_addressability_audit",
        labels_sent_to_model=False, old_results_changed=False, semantic_approval=False,
        live_qualified=False, report_sha256=REPORT_SHA, manifest=manifest,
        counts=dict(entries=len(sources.entries), blocks=len(matrix),
                    by_kind=dict(Counter(e.kind for e in sources.entries))),
        report_source_matrix=matrix, literal_checks=literal_checks,
        generic_boundary_was_already_indexed=dict(legacy_ref=26, wrong_model_ref=12,
            old_statement_correction="Not every source error is missing evidence; scope:limits already declares no video decision evidence."),
        same_direction_different_scope=dict(MIDDLE=evidence["cohorts"]["MIDDLE"],
            selected=evidence["cohorts"]["selected"], scope_selection_solved=False),
        sizing_only=dict(baseline_second=measured(request), appended_manifest_second=size_projection,
            compact_address_index_second=compact_projection,
            input_limit=63936, final_request=False, full_workflow_measured=False),
        source_hashes=hashes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-run", "base-report", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = check(args)
    write_new_json(args.output, result)
    print(compact({key: result[key] for key in ("counts", "sizing_only", "semantic_approval")}))


if __name__ == "__main__":
    main()
