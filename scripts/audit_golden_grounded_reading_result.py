"""Read-only audit of grounded first-reading failures; no response repair."""
import argparse
import hashlib
from pathlib import Path
import re

from pydantic import ValidationError

from app.evaluation.golden_grounded_reading_review import ReportReading
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import SourceIndex, compact


def audit(directory):
    files = sorted(p for p in directory.rglob("*") if p.is_file())
    hashes = {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    receipt = strict_json((directory / "receipt.json").read_text(encoding="utf-8"))
    cases = []
    for case in receipt["cases"]:
        path = directory / case["id"]
        response = strict_json((path / "response-001.json").read_text(encoding="utf-8"))
        raw = response["content"]
        value = strict_json(raw)
        source = SourceIndex.build(strict_json((path / "input.json").read_text(encoding="utf-8"))["report"], {"facts": {}})
        errors = []
        try:
            ReportReading.model_validate(value, strict=True)
        except ValidationError as error:
            errors = [dict(location=list(e["loc"]), code=e["type"], original_value=e.get("input"))
                for e in error.errors(include_context=False)]
        primary = sorted({r["quote_ref"]["block"] for r in value["readings"]})
        body = [i for i, (_, text) in enumerate(source.blocks, 1) if not re.match(r"^#{1,6}\s", text)]
        cases.append(dict(case_id=case["id"], first_raw_sha256=hashlib.sha256(raw.encode()).hexdigest(),
            strict_json_valid=True, schema_errors=errors, readings=len(value["readings"]), issues=len(value["issues"]),
            primary_blocks=primary, omitted_body_blocks=sorted(set(body)-set(primary)),
            final_review_executed=(path / "response-002.json").exists()))
    for p in files:
        if hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(directory))]:
            raise ValueError("grounded_audit_source_changed")
    return dict(run_id=directory.name, head_sha=receipt["head_sha"], ci_run=receipt["ci_run"],
        new_provider_calls=0, actual_run_calls=receipt["reserved_calls"],
        actual_input_tokens=receipt["input_tokens"], actual_output_tokens=receipt["output_tokens"],
        unknown_usage_calls=receipt["unknown_usage_calls"], cases=cases, source_hashes=hashes,
        original_bytes_preserved=True, semantic_approval=False, historical_result_remains_failed=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.run.resolve()):
        raise ValueError("grounded_audit_output_inside_source_run")
    result = audit(args.run)
    write_new_json(args.output, result)
    print(compact({k: v for k, v in result.items() if k != "source_hashes"}))


if __name__ == "__main__": main()
