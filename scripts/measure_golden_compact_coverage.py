"""Measure coverage serialization only; no model calls or semantic grading."""
import argparse
import json
from pathlib import Path

from app.evaluation.golden_compact_coverage import encode_coverage
from app.evaluation.golden_inference_scope import ScopedBlock


def measure(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    rows = [ScopedBlock.model_validate(row, strict=True) for row in value["coverage"]]
    compact = {**value, "coverage": encode_coverage(rows)}
    def size(item):
        return len(json.dumps(item, ensure_ascii=False, separators=(",", ":")))
    return {"scope": "serialization_only_not_token_or_quality_estimate", "external_calls": 0,
            "blocks": len(rows), "coverage_chars_before": size(value["coverage"]),
            "coverage_chars_after": size(compact["coverage"]),
            "response_chars_before": size(value), "response_chars_after": size(compact)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evaluation", type=Path)
    print(json.dumps(measure(parser.parse_args().evaluation)))
