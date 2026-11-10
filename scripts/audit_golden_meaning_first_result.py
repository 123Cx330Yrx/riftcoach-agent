"""Read-only forensic audit. Never feed a normalized response to the workflow."""
import argparse
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_meaning_first_review import ReportReading


class Pairs(list):
    pass


def inspect_json(raw):
    """Keep every key occurrence; project only unambiguous identical repeats.

    Projection is for independently checking *other* schema defects. It is not
    returned, saved as a model response, or accepted by the strict runtime.
    """
    duplicates = []
    def walk(value, path=""):
        if isinstance(value, Pairs):
            result = {}
            for key, child in value:
                child_path = path + "/" + key.replace("~", "~0").replace("/", "~1")
                child = walk(child, child_path)
                if key in result:
                    duplicates.append(dict(path=child_path,
                        identical=type(result[key]) is type(child) and result[key] == child))
                else:
                    result[key] = child
            return result
        if isinstance(value, list):
            return [walk(v, path + "/" + str(i)) for i, v in enumerate(value)]
        return value
    projected = walk(json.loads(raw, object_pairs_hook=Pairs))
    try:
        strict_json(raw)
        strict_error = None
    except ValueError as error:
        strict_error = str(error)
    result = dict(strict_error=strict_error, duplicate_keys=duplicates,
        projection_is_live_acceptance=False)
    if any(not d["identical"] for d in duplicates):
        result["projection_skipped"] = "conflicting_duplicate_values"
        return result
    try:
        reading = ReportReading.model_validate(projected, strict=True)
    except ValueError:
        result["projected_schema_valid"] = False
        return result
    result.update(projected_schema_valid=True, readings=len(reading.readings), issues=len(reading.issues),
        report_sha256=reading.report_sha256,
        readings_by_block=[dict(block=r.quote_ref.block,
            context_blocks=[c.block for c in r.context_refs]) for r in reading.readings])
    return result


def audit(directory):
    files = [p for p in sorted(directory.rglob("*")) if p.is_file()]
    hashes = {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    receipt = strict_json((directory / "receipt.json").read_text(encoding="utf-8"))
    cases = []
    for case in receipt["cases"]:
        response = strict_json((directory / case["id"] / "response-001.json").read_text(encoding="utf-8"))
        cases.append(dict(case_id=case["id"], **inspect_json(response["content"])))
    for p in files:
        if hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(directory))]:
            raise ValueError("meaning_audit_source_changed")
    return dict(run_id=directory.name, head_sha=receipt["head_sha"], ci_run=receipt["ci_run"],
        new_provider_calls=0, actual_run_calls=receipt["reserved_calls"],
        actual_input_tokens=receipt["input_tokens"], actual_output_tokens=receipt["output_tokens"],
        unknown_usage_calls=receipt["unknown_usage_calls"], cases=cases, source_hashes=hashes,
        original_bytes_preserved=True, semantic_approval=False, final_evidence_review_executed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Source receipts are immutable even if a caller supplies a mistaken target.
    if args.output.resolve().is_relative_to(args.run.resolve()):
        raise ValueError("meaning_audit_output_inside_source_run")
    result = audit(args.run)
    write_new_json(args.output, result)
    print(json.dumps({k: result[k] for k in ("run_id", "actual_run_calls", "actual_input_tokens",
        "actual_output_tokens", "original_bytes_preserved", "semantic_approval")}))


if __name__ == "__main__":
    main()
