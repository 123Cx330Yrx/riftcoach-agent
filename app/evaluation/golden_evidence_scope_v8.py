"""Explicit heading review on top of the unchanged evidence acceptance rules."""
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.evaluation.golden_evidence_scope_v5 import (
    EvidenceWire as PreviousWire, EvidenceEvaluation, normalize_json,
    expand_evidence as previous_expand,
)
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_inference_coverage import report_blocks


class HeadingReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    block_id: str = Field(min_length=1, max_length=80)
    kind: Literal["navigation", "assertion"]


class EvidenceWire(PreviousWire):
    heading_reviews: list[HeadingReview] = Field(max_length=64)


def heading_blocks(report):
    return [b for b in report_blocks(report) if re.match(r"^#{1,6}\s", b["text"])]


def heading_errors(value, report):
    expected = heading_blocks(report)
    reviews = value.get("heading_reviews")
    if not isinstance(reviews, list) or any(not isinstance(r, dict) for r in reviews):
        return [{"codes": ["heading_inventory_mismatch"], "expected_heading_ids": [b["block_id"] for b in expected]}]
    rows = []
    if [r.get("block_id") for r in reviews] != [b["block_id"] for b in expected]:
        rows.append({"codes": ["heading_inventory_mismatch"], "expected_heading_ids": [b["block_id"] for b in expected]})
    lookup = {b["block_id"]: b for b in expected}
    audits = value.get("audits")
    claims = [c for a in audits if isinstance(a, dict) and isinstance(a.get("claims"), list)
              for c in a["claims"] if isinstance(c, dict)] if isinstance(audits, list) else []
    for r in reviews:
        block_id = r.get("block_id")
        b = lookup.get(block_id) if isinstance(block_id, str) else None
        if b is None:
            continue
        found = [c for c in claims if c.get("quote") == b["text"] and c.get("claim_kind") == "inference"]
        if r.get("kind") == "assertion" and not found:
            rows.append({"block_id": b["block_id"], "codes": ["heading_assertion_claim_missing"], "source_heading": b["text"]})
        if r.get("kind") == "navigation" and any(c.get("quote") in b["text"] for c in claims if c.get("quote")):
            rows.append({"block_id": b["block_id"], "codes": ["heading_navigation_claim_conflict"]})
    return rows


def expand_evidence(raw, report, pack):
    value = strict_json(normalize_json(raw))
    EvidenceWire.model_validate_json(json.dumps(value), strict=True)
    errors = heading_errors(value, report)
    if errors:
        raise ValueError(errors[0]["codes"][0])
    # Heading assessments stay in the raw journal; existing canonical claims
    # and coverage retain the assertion and its exact issue for consumers.
    value.pop("heading_reviews")
    return previous_expand(json.dumps(value), report, pack)
