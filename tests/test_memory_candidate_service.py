from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.memory.models import (
    CandidateCreateDisposition,
    CandidateCreateResult,
    CandidateKind,
    CandidateMutationDisposition,
    CandidateMutationResult,
    CandidateStatus,
    CreateMemoryCandidateCommand,
    DecisionActorKind,
    MemoryCandidate,
    MemoryCandidateView,
    MemoryConversationIdentity,
    MemoryOperation,
    PendingMemoryCandidate,
    ProvenanceKind,
    RelationshipRole,
    TargetScope,
    compute_candidate_fingerprint,
    compute_payload_sha256,
)
from app.memory.service import MemoryCandidateService, MemoryCandidateServiceError


NOW = datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc)
OWNER = "service-owner"
CONVERSATION_ID = UUID("72000000-0000-4000-8000-000000000001")
RELATIONSHIP_ID = UUID("72000000-0000-4000-8000-000000000002")
SUBJECT_ID = UUID("72000000-0000-4000-8000-000000000003")
CANDIDATE_ID = UUID("72000000-0000-4000-8000-000000000004")


def command(**overrides: object) -> CreateMemoryCandidateCommand:
    values: dict[str, object] = {
        "owner_id": OWNER,
        "conversation_id": CONVERSATION_ID,
        "idempotency_key": "candidate-1",
        "target_scope": TargetScope.OWNER_GLOBAL,
        "candidate_kind": CandidateKind.OWNER_PREFERENCE,
        "memory_key": "report_language",
        "operation": MemoryOperation.SET,
        "proposal_payload": {"value": "zh-CN"},
        "provenance_kind": ProvenanceKind.USER_STRUCTURED_INPUT,
        "producer_id": "public-api",
        "producer_version": "1.0.0",
        "proposal_confidence": None,
    }
    values.update(overrides)
    return CreateMemoryCandidateCommand(**values)


class FakeRepository:
    def __init__(self, *, identity: MemoryConversationIdentity | None = None) -> None:
        self.identity = identity or MemoryConversationIdentity(
            owner_id=OWNER,
            conversation_id=CONVERSATION_ID,
            relationship_id=RELATIONSHIP_ID,
            player_subject_id=SUBJECT_ID,
            relationship_role=RelationshipRole.SELF,
        )
        self.candidates: list[MemoryCandidate] = []
        self.next_result: CandidateMutationResult | None = None
        self.failure: Exception | None = None
        self.accept_materializers: object | None = None

    def _fail(self) -> None:
        if self.failure is not None:
            raise self.failure

    def get_conversation_identity(self, *, owner_id: str, conversation_id: UUID):
        self._fail()
        if owner_id != self.identity.owner_id or conversation_id != self.identity.conversation_id:
            return None
        return self.identity

    def create_or_replay_candidate(
        self,
        pending: PendingMemoryCandidate,
        *,
        identity: MemoryConversationIdentity,
        requires_confirmation: bool,
        gate_policy_version: str,
    ) -> CandidateCreateResult:
        self._fail()
        fingerprint = compute_candidate_fingerprint(pending)
        existing = next(
            (
                item
                for item in self.candidates
                if item.owner_id == pending.owner_id
                and item.idempotency_key == pending.idempotency_key
            ),
            None,
        )
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise RuntimeError("candidate_idempotency_conflict")
            return CandidateCreateResult(
                disposition=CandidateCreateDisposition.REPLAYED,
                candidate=existing,
            )
        created = MemoryCandidate(
            **pending.model_dump(),
            relationship_id=identity.relationship_id,
            player_subject_id=identity.player_subject_id,
            relationship_role=identity.relationship_role,
            request_fingerprint=fingerprint,
            proposal_payload_sha256=compute_payload_sha256(pending.proposal_payload),
            gate_policy_version=gate_policy_version,
            requires_confirmation=requires_confirmation,
            status=CandidateStatus.PENDING,
            updated_at=pending.created_at,
        )
        self.candidates.append(created)
        return CandidateCreateResult(
            disposition=CandidateCreateDisposition.CREATED,
            candidate=created,
        )

    def get_candidate(self, *, owner_id: str, candidate_id: UUID):
        self._fail()
        return next(
            (
                item
                for item in self.candidates
                if item.owner_id == owner_id and item.candidate_id == candidate_id
            ),
            None,
        )

    def reject_candidate(self, **kwargs):
        self._fail()
        if self.next_result is not None:
            return self.next_result
        item = self.get_candidate(owner_id=kwargs["owner_id"], candidate_id=kwargs["candidate_id"])
        if item is None:
            return CandidateMutationResult(disposition=CandidateMutationDisposition.NOT_FOUND)
        if item.status is CandidateStatus.REJECTED:
            return CandidateMutationResult(
                disposition=CandidateMutationDisposition.REPLAYED,
                candidate=item,
            )
        if item.status is not CandidateStatus.PENDING:
            return CandidateMutationResult(disposition=CandidateMutationDisposition.TERMINAL_CONFLICT)
        updated = item.model_copy(
            update={
                "status": CandidateStatus.REJECTED,
                "decision_actor_kind": DecisionActorKind.USER,
                "decision_actor_id": kwargs["actor_id"],
                "decision_reason_code": kwargs["reason_code"],
                "decided_at": kwargs["now"],
                "updated_at": kwargs["now"],
            }
        )
        self.candidates[0] = MemoryCandidate.model_validate(updated)
        return CandidateMutationResult(
            disposition=CandidateMutationDisposition.REJECTED,
            candidate=self.candidates[0],
        )

    def expire_candidate(self, **kwargs):
        self._fail()
        return CandidateMutationResult(disposition=CandidateMutationDisposition.NOT_FOUND)

    def accept_candidate(self, **kwargs):
        self._fail()
        if self.next_result is not None:
            return self.next_result
        return CandidateMutationResult(disposition=CandidateMutationDisposition.TARGET_UNAVAILABLE)


def make_service(repository: FakeRepository) -> MemoryCandidateService:
    ids = iter((CANDIDATE_ID,))
    return MemoryCandidateService(
        repository=repository,
        candidate_id_factory=lambda: next(ids),
        clock=lambda: NOW,
    )


def test_create_derives_gate_and_returns_body_safe_view() -> None:
    repository = FakeRepository()
    view = make_service(repository).create(command())
    assert isinstance(view, MemoryCandidateView)
    assert view.status is CandidateStatus.PENDING
    assert view.conversation_id == CONVERSATION_ID
    assert "proposal_payload" not in view.model_dump()
    assert repository.candidates[0].relationship_id == RELATIONSHIP_ID


def test_create_rejects_missing_conversation_before_insert() -> None:
    repository = FakeRepository()
    service = make_service(repository)
    with pytest.raises(MemoryCandidateServiceError) as error:
        service.create(command(conversation_id=UUID("72000000-0000-4000-8000-000000000099")))
    assert error.value.code == "conversation_not_found"
    assert repository.candidates == []


def test_model_candidate_is_pending_even_with_confidence_one() -> None:
    repository = FakeRepository()
    view = make_service(repository).create(
        command(
            target_scope=TargetScope.OWNER_PLAYER,
            candidate_kind=CandidateKind.PLAYER_PROFILE,
            memory_key="main_role",
            provenance_kind=ProvenanceKind.MODEL_INFERENCE,
            proposal_confidence=1.0,
        )
    )
    assert view.requires_confirmation is True
    assert repository.candidates[0].status is CandidateStatus.PENDING


def test_gate_rejection_does_not_insert_candidate() -> None:
    repository = FakeRepository(
        identity=MemoryConversationIdentity(
            owner_id=OWNER,
            conversation_id=CONVERSATION_ID,
            relationship_id=RELATIONSHIP_ID,
            player_subject_id=SUBJECT_ID,
            relationship_role=RelationshipRole.OBSERVED,
        )
    )
    with pytest.raises(MemoryCandidateServiceError) as error:
        make_service(repository).create(
            command(
                target_scope=TargetScope.OWNER_PLAYER,
                candidate_kind=CandidateKind.PLAYER_PROFILE,
                memory_key="main_role",
                provenance_kind=ProvenanceKind.MODEL_INFERENCE,
            )
        )
    assert error.value.code == "candidate_gate_rejected"
    assert repository.candidates == []


def test_accept_fails_closed_when_no_typed_materializer_is_registered() -> None:
    repository = FakeRepository()
    service = make_service(repository)
    service.create(command())
    with pytest.raises(MemoryCandidateServiceError) as error:
        service.accept(owner_id=OWNER, candidate_id=CANDIDATE_ID, actor_id=OWNER)
    assert error.value.code == "memory_target_unavailable"
    assert repository.candidates[0].status is CandidateStatus.PENDING


def test_repository_failure_is_not_leaked_as_raw_exception() -> None:
    repository = FakeRepository()
    repository.failure = RuntimeError("database password leaked")
    with pytest.raises(MemoryCandidateServiceError) as error:
        make_service(repository).create(command())
    assert error.value.code == "service_unavailable"
    assert "password" not in str(error.value)
