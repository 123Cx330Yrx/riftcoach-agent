"""Read saved responses and measure the offline review protocol. No Provider I/O."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import statistics

from app.evaluation.golden_evidence_scope_v5 import expand_evidence as validate_v7, normalize_json
from app.evaluation.golden_evidence_scope_v8 import expand_evidence as validate_v8
from app.evaluation.golden_fact_candidate import fact_pack
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import (
    SourceIndex, compact, digest, index_review, restore_review,
    plan_anchor_repair, validate_indexed_review,
    anchor_patch_request,
)


def _accepted(validator, raw, report, pack):
    try:
        return validator(raw, report, pack).model_dump(mode="json"), None
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return None, str(exc).splitlines()[0][:120]


def measure_run(directory: Path, pack, *, source_assets=None):
    plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
    version = plan["contract"]["version"]
    validator = {"1.3.25": validate_v7, "1.3.26": validate_v8}[version]
    samples, inputs, finalized = [], [], []
    for pair in sorted(directory.glob("pair-*")):
        case_inputs = []
        for path in sorted(pair.glob("*-input.json")):
            case = json.loads(path.read_text(encoding="utf-8"))
            if digest(case["report"]) != case["report_sha256"]:
                raise ValueError("saved_report_identity_changed")
            case_inputs.append((case["first_call"], path.stem.removesuffix("-input"), case["report"]))
        case_inputs.sort()
        inputs.extend(case_id for _, case_id, _ in case_inputs)
        finalized.extend(p.stem.removesuffix("-result") for p in pair.glob("*-result.json"))
        for path in sorted(pair.glob("response-*.json")):
            ordinal = int(path.stem.split("-")[-1])
            prior = [row for row in case_inputs if row[0] <= ordinal]
            if not prior:
                raise ValueError("response_has_no_case_input")
            _, case_id, report = prior[-1]
            response = json.loads(path.read_text(encoding="utf-8"))
            raw = response["content"]
            source = SourceIndex.build(report, pack)
            original, error = _accepted(validator, raw, report, pack)
            sample = {"response": path.relative_to(directory).as_posix(), "case_id": case_id,
                      "raw_sha256": digest(raw), "report_sha256": digest(report),
                      "original_valid": original is not None, "original_error": error,
                      "visible_chars": len(raw), "report_chars": len(report)}
            # Prefix extraction is for counts only. It is never sent to indexing
            # or the acceptance/patch functions; suffixes and duplicate keys fail.
            try:
                prefix, end = json.JSONDecoder().raw_decode(raw.lstrip())
                if not isinstance(prefix, dict):
                    raise ValueError("object_required")
                claims = [c for a in prefix["audits"] for c in a["claims"]]
                quotes = [c["quote"] for c in claims]
                sample.update(claims=len(quotes), whole_block_quotes=sum(q == b for q in quotes for _, b in source.blocks),
                    sentence_unit_quotes=sum(any(q == s for _, b in source.blocks for s in re.split(r"(?<=[。！？])", b) if s) for q in quotes),
                    copied_quote_chars=sum(map(len, quotes)) + sum(len(i["quote"]) for i in prefix["issues"]),
                    copied_id_chars=sum(len(i) for i in prefix["reviewed_blocks"]) + sum(len(h["block_id"]) for h in prefix.get("heading_reviews", [])),
                    nonwhitespace_suffix=bool(raw.lstrip()[end:].strip()), prefix_for_measurement_only=True)
            except (ValueError, KeyError, TypeError):
                sample["prefix_for_measurement_only"] = False
            try:
                indexed = index_review(raw, source)
                restored = restore_review(indexed, source)
                if restored != strict_json(normalize_json(raw)):
                    raise AssertionError("projection_changed_information")
                restored_result, restored_error = _accepted(validator, compact(restored), report, pack)
                if (restored_result, restored_error) != (original, error):
                    raise AssertionError("projection_changed_acceptance")
                if original is not None:
                    assert validate_indexed_review(indexed, source, pack, validator=validator).model_dump(mode="json") == original
                sample.update(projectable=True, original_compact_chars=len(compact(restored)),
                              indexed_compact_chars=len(compact(indexed)), identical_roundtrip=True,
                              identical_acceptance=True)
            except (ValueError, KeyError, TypeError) as exc:
                sample.update(projectable=False, projection_error=str(exc).splitlines()[0][:120])
            if version == "1.3.26":
                try:
                    repair = plan_anchor_repair(raw, report, pack)
                    sample.update(reference_patch_eligible=True, patch_targets=list(repair.targets))
                    if source_assets is not None:
                        from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
                        from app.evaluation.golden_evidence_requests_v8 import evaluation_request
                        from app.evaluation.golden_evidence_diagnostics_v8 import collect_diagnostics
                        summary, deterministic, knowledge = source_assets
                        utterance = "复核ShowMaker观摩报告的事实、推断和建议；这是观摩对象，不是阅读者本人。"
                        local = anchor_patch_request(raw, summary, deterministic, knowledge, report, utterance)
                        whole = evaluation_request(summary, deterministic, knowledge, report, utterance,
                                                   diagnostics=collect_diagnostics(raw, report, pack))
                        sample["input_ceiling_comparison"] = dict(reference_patch=estimate_runtime_request_input_ceiling(local),
                            whole_reevaluation=estimate_runtime_request_input_ceiling(whole), max_input=64000,
                            max_output=32768, request_timeout_s=300, runtime_registered=False)
                except (ValueError, KeyError, TypeError) as exc:
                    sample["reference_patch_eligible"] = False
                    sample["reference_patch_error"] = str(exc).splitlines()[0][:120]
            samples.append(sample)
    projected = [s for s in samples if s["projectable"]]
    counted = [s for s in samples if s["prefix_for_measurement_only"]]
    selected = plan["selected_case_ids"]
    if len(set(inputs)) != len(inputs) or not set(finalized) <= set(inputs) <= set(selected):
        raise ValueError("case_progress_identity_invalid")
    return {"run": directory.name, "version": version,
            "original_implementation_sha": plan["head_sha"],
            "started": len(inputs), "finalized": len(finalized),
            "interrupted": len(set(inputs) - set(finalized)), "not_started": len(set(selected) - set(inputs)),
            "responses": len(samples), "original_valid_responses": sum(s["original_valid"] for s in samples),
            "projectable_responses": len(projected),
            "original_compact_chars": sum(s["original_compact_chars"] for s in projected),
            "indexed_compact_chars": sum(s["indexed_compact_chars"] for s in projected),
            "median_visible_chars": statistics.median(s["visible_chars"] for s in samples) if samples else None,
            "copied_quote_and_id_fraction": round(sum(s["copied_quote_chars"] + s["copied_id_chars"] for s in counted) / sum(s["visible_chars"] for s in counted), 4) if counted else None,
            "claim_count": sum(s["claims"] for s in counted),
            "whole_block_quotes": sum(s["whole_block_quotes"] for s in counted),
            "sentence_unit_quotes": sum(s["sentence_unit_quotes"] for s in counted),
            "patch_eligible_responses": sum(s.get("reference_patch_eligible", False) for s in samples),
            "patch_request_measurements": [s["input_ceiling_comparison"] for s in samples if "input_ceiling_comparison" in s],
            "projection_failures": dict(Counter(s["projection_error"] for s in samples if not s["projectable"])),
            "samples": samples}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--runs", type=Path, nargs="+", required=True)
    parser.add_argument("--source-run", type=Path, help="Saved deterministic report and retrieval evidence for request measurements")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--public-output", type=Path, help="Create-only counts and hashes; no response bodies")
    args = parser.parse_args()
    source_summary = json.loads(args.summary.read_text(encoding="utf-8"))
    pack = fact_pack(source_summary)
    source_assets = None
    if args.source_run:
        from app.harness.steps import KnowledgeEvidence, KnowledgeCitation
        if json.loads((args.source_run / "inputs/player_summary.json").read_text(encoding="utf-8")) != source_summary:
            raise ValueError("request_measurement_source_mismatch")
        raw = json.loads((args.source_run / "knowledge/retrieval_evidence.json").read_text(encoding="utf-8"))
        knowledge = KnowledgeEvidence(context=raw["context"], source_ids=tuple(raw["source_ids"]),
            citations=tuple(KnowledgeCitation(**c) for c in raw["citations"]), abstained=raw.get("abstained", False))
        source_assets = (source_summary, (args.source_run / "inputs/deterministic_report.md").read_text(encoding="utf-8"), knowledge)
    runs = [measure_run(path, pack, source_assets=source_assets) for path in args.runs]
    result = {"schema_version": "offline-review-workflow-measurement-v1", "model_evaluated": False,
              "semantic_fix_verified": False, "runtime_registered": False,
              "source_summary_sha256": digest(compact(pack)), "runs": runs,
              "experiment_files_sha256": {
                  "app/evaluation/golden_review_experiment.py": digest(Path(__file__).resolve().parents[1].joinpath("app/evaluation/golden_review_experiment.py").read_text(encoding="utf-8")),
                  "scripts/check_golden_review_workflow.py": digest(Path(__file__).read_text(encoding="utf-8")),
              }}
    summary = {**{k: v for k, v in result.items() if k != "runs"},
               "runs": [{k: v for k, v in run.items() if k != "samples"} for run in runs]}
    destinations = [p.resolve() for p in (args.output, args.public_output) if p is not None]
    if len(set(destinations)) != len(destinations) or any(p.exists() for p in destinations):
        raise ValueError("measurement_output_must_be_new")
    if args.output:
        write_new_json(args.output, result)
    if args.public_output:
        write_new_json(args.public_output, summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
