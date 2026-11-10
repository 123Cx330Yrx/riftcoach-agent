"""Offline compact coverage candidate; no runtime registration or model calls."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, TypeAdapter

from app.evaluation.golden_inference_scope_v2 import (
    EvaluationResponseModelV17, validate_scope_v2,
)

COMPACT_COVERAGE_ID = "golden-compact-coverage-v1"
BlockId = Annotated[str, Field(pattern=r"^b[0-9]{2}-[0-9a-f]{8}$")]
Code = Literal["N", "S", "U"]
Rows = Annotated[list[tuple[BlockId, Code, Code, bool]], Field(min_length=1, max_length=64)]
ROWS = TypeAdapter(Rows)
STATUS = {"N": "not_applicable", "S": "supported", "U": "unsupported"}
CODE = {value: key for key, value in STATUS.items()}


def encode_coverage(coverage):
    """Encode validated canonical records without dropping IDs or decisions."""
    return [[row.block_id, CODE[row.metric_to_ability],
             CODE[row.cohort_comparison], row.scope_ambiguous] for row in coverage]


def expand_response(raw_json: str, report: str, facts: dict):
    """Expand only coverage, then run the existing complete semantic-boundary checks.

    Explicit JSON parsing rejects duplicate keys and non-finite constants before
    expansion. No response, status, issue, anchor or missing row is repaired here.
    """
    import json

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("compact_duplicate_key")
            result[key] = value
        return result

    def nonfinite(_):
        raise ValueError("compact_nonfinite_number")

    value = json.loads(raw_json, object_pairs_hook=unique, parse_constant=nonfinite)
    if not isinstance(value, dict) or "coverage" not in value:
        raise ValueError("compact_coverage_missing")
    # JSON strict mode accepts JSON arrays as tuples but never coerces booleans
    # from integers/strings. Preserve all other fields verbatim for validation.
    rows = ROWS.validate_json(json.dumps(value["coverage"]), strict=True)
    value["coverage"] = [dict(block_id=b, metric_to_ability=STATUS[m],
                              cohort_comparison=STATUS[c], scope_ambiguous=a)
                         for b, m, c, a in rows]
    payload = EvaluationResponseModelV17.model_validate(value, strict=True)
    validate_scope_v2(payload, report, facts)
    return payload
