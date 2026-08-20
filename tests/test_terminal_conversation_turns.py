from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.conversations.turns import TerminalAssistantTurn, TerminalCandidateProposal
from app.memory.context_models import MemoryContextBinding
from app.memory.models import (
    CandidateKind,
    MemoryOperation,
    ProvenanceKind,
    TargetScope,
)
from app.players.models import RelationshipRole
from app.runtime.models import RuntimeArtifactReference
from app.runtime.signals import RuntimePublicationStatus


def turn(**overrides: object) -> TerminalAssistantTurn:
    run_id = "terminal_turn_001"
    values: dict[str, object] = {
        "source_task_id": UUID("50000000-0000-0000-0000-000000000001"),
        "binding": MemoryContextBinding(
            run_id=run_id,
            owner_id="owner-turn",
            conversation_id=UUID("50000000-0000-0000-0000-000000000002"),
            relationship_id=UUID("50000000-0000-0000-0000-000000000003"),
            player_subject_id=UUID("50000000-0000-0000-0000-000000000004"),
            relationship_role=RelationshipRole.SELF,
        ),
        "publication_status": RuntimePublicationStatus.PUBLISHED,
        "artifact_reference": RuntimeArtifactReference(
            kind="final_report",
            schema_version="1.0",
            relative_path="output/final_report.md",
            sha256="a" * 64,
            producer="review-harness",
        ),
        "assistant_content": "# terminal reviewed report",
        "candidate_proposals": (),
        "created_at": datetime(2026, 8, 21, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return TerminalAssistantTurn(**values)


def test_terminal_turn_requires_published_or_degraded_final_report() -> None:
    assert turn().assistant_content_sha256 == turn().assistant_content_sha256
    with pytest.raises(ValidationError):
        turn(publication_status=RuntimePublicationStatus.REJECTED)
    with pytest.raises(ValidationError, match="final_report"):
        turn(
            artifact_reference=turn().artifact_reference.model_copy(
                update={"kind": "coach_draft"}
            )
        )
    with pytest.raises(ValidationError):
        turn(assistant_content="   ")


def test_terminal_candidate_proposal_is_strict_and_never_carries_source_identity() -> None:
    proposal = TerminalCandidateProposal(
        target_scope=TargetScope.OWNER_PLAYER,
        candidate_kind=CandidateKind.REVIEW_MEMORY,
        memory_key="review_summary",
        operation=MemoryOperation.APPEND,
        proposal_payload={"value": "bounded conclusion"},
        provenance_kind=ProvenanceKind.MODEL_INFERENCE,
        producer_id="recent-form-review",
        producer_version="0.2.0",
        proposal_confidence=0.7,
    )

    assert turn(candidate_proposals=(proposal,)).candidate_proposals == (proposal,)
    with pytest.raises(ValidationError):
        TerminalCandidateProposal.model_validate(
            {**proposal.model_dump(mode="python"), "source_run_id": "client-run"}
        )
    with pytest.raises(ValidationError, match="provenance"):
        TerminalCandidateProposal.model_validate(
            {
                **proposal.model_dump(mode="python"),
                "provenance_kind": ProvenanceKind.USER_STRUCTURED_INPUT,
            }
        )
