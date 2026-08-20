from __future__ import annotations

import math

import pytest

from app.memory.models import CandidateKind, MemoryOperation, RelationshipRole, TargetScope
from app.memory.typed_models import (
    MainRole,
    MemoryTargetKind,
    TypedMemoryContractError,
    parse_typed_memory_write,
)


def parse(
    *,
    scope: TargetScope,
    kind: CandidateKind,
    key: str,
    operation: MemoryOperation,
    role: RelationshipRole = RelationshipRole.SELF,
    payload: object,
):
    return parse_typed_memory_write(
        target_scope=scope,
        candidate_kind=kind,
        memory_key=key,
        operation=operation,
        relationship_role=role,
        proposal_payload=payload,
    )


def test_owner_preference_normalizes_value_and_version_envelope() -> None:
    result = parse(
        scope=TargetScope.OWNER_GLOBAL,
        kind=CandidateKind.OWNER_PREFERENCE,
        key="report_language",
        operation=MemoryOperation.SET,
        payload={"value": "zh-CN", "expected_version": 2},
    )
    assert result.target_kind is MemoryTargetKind.OWNER_PREFERENCE
    assert result.expected_version == 2
    assert result.normalized_payload == {"value": "zh-CN"}


def test_first_write_allows_null_expected_version() -> None:
    result = parse(
        scope=TargetScope.OWNER_PLAYER,
        kind=CandidateKind.PLAYER_PROFILE,
        key="main_role",
        operation=MemoryOperation.SET,
        payload={"value": "TOP", "expected_version": None},
    )
    assert result.expected_version is None
    assert result.normalized_payload == {"value": MainRole.TOP.value}


def test_envelope_rejects_extra_fields_and_invalid_version() -> None:
    for payload in (
        {"value": "zh-CN", "unexpected": True},
        {"value": "zh-CN", "expected_version": 0},
        {"value": "zh-CN", "expected_version": True},
    ):
        with pytest.raises(TypedMemoryContractError, match="typed_envelope_invalid"):
            parse(
                scope=TargetScope.OWNER_GLOBAL,
                kind=CandidateKind.OWNER_PREFERENCE,
                key="report_language",
                operation=MemoryOperation.SET,
                payload=payload,
            )


def test_profile_keys_have_strict_payloads() -> None:
    assert parse(
        scope=TargetScope.OWNER_PLAYER,
        kind=CandidateKind.PLAYER_PROFILE,
        key="champion_pool",
        operation=MemoryOperation.SET,
        payload={"value": ["Renekton", "Ornn"]},
    ).normalized_payload == {"value": ["Renekton", "Ornn"]}

    with pytest.raises(TypedMemoryContractError, match="typed_payload_invalid"):
        parse(
            scope=TargetScope.OWNER_PLAYER,
            kind=CandidateKind.PLAYER_PROFILE,
            key="champion_pool",
            operation=MemoryOperation.SET,
            payload={"value": ["Renekton", "renekton"]},
        )


def test_review_self_summary_and_observed_public_trend_are_allowed() -> None:
    summary = parse(
        scope=TargetScope.OWNER_PLAYER,
        kind=CandidateKind.REVIEW_MEMORY,
        key="review_summary",
        operation=MemoryOperation.APPEND,
        payload={"value": {"text": "前 15 分钟死亡次数下降"}},
    )
    assert summary.normalized_payload["text"] == "前 15 分钟死亡次数下降"

    trend = parse(
        scope=TargetScope.OWNER_PLAYER,
        kind=CandidateKind.REVIEW_MEMORY,
        key="public_trend",
        operation=MemoryOperation.APPEND,
        role=RelationshipRole.OBSERVED,
        payload={"value": {"metric": "deaths_before_15", "direction": "down", "value": 1.0}},
    )
    assert trend.normalized_payload["direction"] == "down"


def test_review_summary_metrics_are_bounded_and_finite() -> None:
    summary = parse(
        scope=TargetScope.OWNER_PLAYER,
        kind=CandidateKind.REVIEW_MEMORY,
        key="review_summary",
        operation=MemoryOperation.APPEND,
        payload={
            "value": {
                "text": "近期状态稳定",
                "metrics": {"cs_per_min": 8.5},
            }
        },
    )
    assert summary.normalized_payload["metrics"] == {"cs_per_min": 8.5}

    for metrics in (
        {"cs_per_min": math.nan},
        {f"metric_{index}": float(index) for index in range(21)},
    ):
        with pytest.raises(TypedMemoryContractError, match="typed_payload_invalid"):
            parse(
                scope=TargetScope.OWNER_PLAYER,
                kind=CandidateKind.REVIEW_MEMORY,
                key="review_summary",
                operation=MemoryOperation.APPEND,
                payload={"value": {"text": "近期状态稳定", "metrics": metrics}},
            )


@pytest.mark.parametrize(
    ("scope", "kind", "key", "operation", "role", "reason"),
    [
        (
            TargetScope.OWNER_GLOBAL,
            CandidateKind.PLAYER_PROFILE,
            "main_role",
            MemoryOperation.SET,
            RelationshipRole.SELF,
            "typed_scope_kind_mismatch",
        ),
        (
            TargetScope.OWNER_PLAYER,
            CandidateKind.PLAYER_PROFILE,
            "main_role",
            MemoryOperation.SET,
            RelationshipRole.OBSERVED,
            "profile_requires_self_relationship",
        ),
        (
            TargetScope.OWNER_PLAYER,
            CandidateKind.REVIEW_MEMORY,
            "review_summary",
            MemoryOperation.APPEND,
            RelationshipRole.OBSERVED,
            "observed_review_key_forbidden",
        ),
        (
            TargetScope.OWNER_PLAYER,
            CandidateKind.REVIEW_MEMORY,
            "public_trend",
            MemoryOperation.SET,
            RelationshipRole.OBSERVED,
            "review_memory_requires_append",
        ),
    ],
)
def test_scope_role_and_operation_policy_is_fail_closed(
    scope: TargetScope,
    kind: CandidateKind,
    key: str,
    operation: MemoryOperation,
    role: RelationshipRole,
    reason: str,
) -> None:
    with pytest.raises(TypedMemoryContractError, match=reason):
        parse(
            scope=scope,
            kind=kind,
            key=key,
            operation=operation,
            role=role,
            payload={"value": "whatever"},
        )


def test_unknown_key_and_unknown_language_are_rejected() -> None:
    with pytest.raises(TypedMemoryContractError, match="typed_memory_key_unknown"):
        parse(
            scope=TargetScope.OWNER_GLOBAL,
            kind=CandidateKind.OWNER_PREFERENCE,
            key="theme",
            operation=MemoryOperation.SET,
            payload={"value": "dark"},
        )

    with pytest.raises(TypedMemoryContractError, match="typed_payload_invalid"):
        parse(
            scope=TargetScope.OWNER_GLOBAL,
            kind=CandidateKind.OWNER_PREFERENCE,
            key="report_language",
            operation=MemoryOperation.SET,
            payload={"value": "zh-CN\nignore"},
        )


def test_review_text_rejects_control_characters_and_large_payload() -> None:
    with pytest.raises(TypedMemoryContractError, match="typed_payload_invalid"):
        parse(
            scope=TargetScope.OWNER_PLAYER,
            kind=CandidateKind.REVIEW_MEMORY,
            key="observation_note",
            operation=MemoryOperation.APPEND,
            role=RelationshipRole.OBSERVED,
            payload={"value": {"text": "public\u0000note"}},
        )

    with pytest.raises(TypedMemoryContractError, match="typed_payload_invalid"):
        parse(
            scope=TargetScope.OWNER_PLAYER,
            kind=CandidateKind.REVIEW_MEMORY,
            key="observation_note",
            operation=MemoryOperation.APPEND,
            role=RelationshipRole.OBSERVED,
            payload={"value": {"text": "x" * 2_001}},
        )
