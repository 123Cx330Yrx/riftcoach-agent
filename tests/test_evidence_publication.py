"""Strict, body-free publication identity and materialized-source contracts."""
from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.evidence.publication import (
    EvidencePublicationContext, EvidencePublicationSources, canonical_bytes, sha256_bytes,
)


def context(run_id="publication"):
    return EvidencePublicationContext(owner_id="owner@example|test+1",
        task_id=UUID("30000000-0000-0000-0000-000000000001"),
        run_id=run_id, request_fingerprint="a" * 64)


def sources(**kwargs):
    return EvidencePublicationSources(now=datetime(2026, 9, 7, tzinfo=timezone.utc), **kwargs)


@pytest.mark.parametrize("field,value", [
    ("owner_id", "../owner"), ("task_id", "not-uuid"), ("run_id", "../run"),
    ("run_id", " run "), ("run_id", "CON"), ("request_fingerprint", "bad"),
    ("mode", "legacy"), ("unexpected", True),
])
def test_strict_context(field, value):
    with pytest.raises(ValidationError):
        EvidencePublicationContext.model_validate({**context().model_dump(), field: value})


def test_identity_is_frozen_and_json_round_trips():
    value = context()
    assert EvidencePublicationContext.model_validate_json(value.model_dump_json()) == value
    with pytest.raises(ValidationError):
        value.owner_id = "other"
    with pytest.raises(ValidationError):
        EvidencePublicationContext.model_validate(value.model_copy(update={"run_id": "../escape"}))


def test_canonical_digest_is_complete_and_order_independent():
    assert canonical_bytes({"b": 2, "a": 1}) == canonical_bytes({"a": 1, "b": 2})
    assert sha256_bytes(canonical_bytes({"a": 1})) != sha256_bytes(canonical_bytes({"a": 2}))
    with pytest.raises(ValueError):
        canonical_bytes({"bad": float("nan")})
