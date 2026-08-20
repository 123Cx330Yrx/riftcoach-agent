from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from types import MappingProxyType
from typing import Literal, TypeAlias
from uuid import UUID, uuid4

from pydantic import TypeAdapter, ValidationError

from app.memory.gate import GateDecision, evaluate_candidate_gate
from app.memory.models import (
    CandidateCreateDisposition,
    CandidateCreateResult,
    CandidateMutationDisposition,
    CandidateMutationResult,
    CandidateStatus,
    CreateMemoryCandidateCommand,
    DecisionActorKind,
    MemoryCandidate,
    MemoryCandidateView,
    PendingMemoryCandidate,
    TargetScope,
    compute_candidate_fingerprint,
)
from app.memory.ports import MaterializerRegistry, MemoryCandidateRepository


MemoryCandidateServiceErrorCode: TypeAlias = Literal[
    "request_invalid",
    "conversation_not_found",
    "candidate_not_found",
    "candidate_idempotency_conflict",
    "candidate_gate_rejected",
    "candidate_terminal_conflict",
    "candidate_expired",
    "memory_target_unavailable",
    "memory_payload_invalid",
    "memory_version_conflict",
    "service_unavailable",
]
_ERROR_CODES = frozenset(
    {
        "request_invalid",
        "conversation_not_found",
        "candidate_not_found",
        "candidate_idempotency_conflict",
        "candidate_gate_rejected",
        "candidate_terminal_conflict",
        "candidate_expired",
        "memory_target_unavailable",
        "memory_payload_invalid",
        "memory_version_conflict",
        "service_unavailable",
    }
)

CandidateIdFactory = Callable[[], UUID]
Clock = Callable[[], datetime]


class MemoryCandidateServiceError(RuntimeError):
    def __init__(self, code: MemoryCandidateServiceErrorCode, *, reason_code: str | None = None) -> None:
        if code not in _ERROR_CODES:
            raise ValueError("unsupported memory candidate service error code")
        self.code = code
        self.reason_code = reason_code
        super().__init__(code)

    def to_public_dict(self) -> dict[str, str]:
        value = {"code": self.code}
        if self.reason_code is not None and self.code == "candidate_gate_rejected":
            value["reason"] = self.reason_code
        return value


class MemoryCandidateService:
    def __init__(
        self,
        *,
        repository: MemoryCandidateRepository,
        materializers: MaterializerRegistry | None = None,
        candidate_id_factory: CandidateIdFactory = uuid4,
        clock: Clock | None = None,
        pending_ttl: timedelta = timedelta(days=30),
    ) -> None:
        for method_name in (
            "get_conversation_identity",
            "create_or_replay_candidate",
            "get_candidate",
            "reject_candidate",
            "expire_candidate",
            "accept_candidate",
        ):
            if not callable(getattr(repository, method_name, None)):
                raise TypeError(f"repository must expose {method_name}()")
        if not callable(candidate_id_factory):
            raise TypeError("candidate_id_factory must be callable")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        if pending_ttl <= timedelta(0):
            raise ValueError("pending_ttl must be positive")
        self._repository = repository
        self._materializers = MappingProxyType(dict(materializers or {}))
        self._candidate_id_factory = candidate_id_factory
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._pending_ttl = pending_ttl

    def create(self, command: CreateMemoryCandidateCommand) -> MemoryCandidateView:
        if not isinstance(command, CreateMemoryCandidateCommand):
            raise TypeError("command must be a CreateMemoryCandidateCommand")
        try:
            identity = self._repository.get_conversation_identity(
                owner_id=command.owner_id,
                conversation_id=command.conversation_id,
            )
        except Exception:
            raise MemoryCandidateServiceError("service_unavailable") from None
        if identity is None:
            raise MemoryCandidateServiceError("conversation_not_found")

        gate = evaluate_candidate_gate(
            target_scope=command.target_scope,
            candidate_kind=command.candidate_kind,
            memory_key=command.memory_key,
            operation=command.operation,
            provenance_kind=command.provenance_kind,
            relationship_role=identity.relationship_role,
            proposal_confidence=command.proposal_confidence,
        )
        if not gate.allowed:
            raise MemoryCandidateServiceError(
                "candidate_gate_rejected",
                reason_code=gate.reason_code,
            )

        try:
            now = self._clock()
            pending = PendingMemoryCandidate(
                candidate_id=self._candidate_id_factory(),
                **command.model_dump(),
                created_at=now,
                expires_at=now + self._pending_ttl,
            )
            result = self._repository.create_or_replay_candidate(
                pending,
                identity=identity,
                requires_confirmation=gate.requires_confirmation,
                gate_policy_version=gate.policy_version,
            )
        except MemoryCandidateServiceError:
            raise
        except Exception:
            raise MemoryCandidateServiceError("service_unavailable") from None
        if not isinstance(result, CandidateCreateResult):
            raise MemoryCandidateServiceError("service_unavailable")
        if result.disposition is CandidateCreateDisposition.IDEMPOTENCY_CONFLICT:
            raise MemoryCandidateServiceError("candidate_idempotency_conflict")
        if result.disposition is CandidateCreateDisposition.IDENTITY_UNAVAILABLE:
            raise MemoryCandidateServiceError("conversation_not_found")
        if result.disposition is CandidateCreateDisposition.SOURCE_INVALID:
            raise MemoryCandidateServiceError("request_invalid")
        if result.disposition not in {CandidateCreateDisposition.CREATED, CandidateCreateDisposition.REPLAYED}:
            raise MemoryCandidateServiceError("service_unavailable")
        if result.candidate is None:
            raise MemoryCandidateServiceError("service_unavailable")
        candidate = result.candidate
        if (
            candidate.owner_id != command.owner_id
            or candidate.conversation_id != command.conversation_id
            or candidate.status is not CandidateStatus.PENDING
        ):
            raise MemoryCandidateServiceError("service_unavailable")
        return MemoryCandidateView.from_candidate(candidate)

    def get(self, *, owner_id: str, candidate_id: UUID) -> MemoryCandidateView:
        try:
            candidate = self._repository.get_candidate(
                owner_id=owner_id,
                candidate_id=candidate_id,
            )
        except Exception:
            raise MemoryCandidateServiceError("service_unavailable") from None
        if candidate is None:
            raise MemoryCandidateServiceError("candidate_not_found")
        if candidate.owner_id != owner_id or candidate.candidate_id != candidate_id:
            raise MemoryCandidateServiceError("service_unavailable")
        return MemoryCandidateView.from_candidate(candidate)

    def reject(self, *, owner_id: str, candidate_id: UUID, actor_id: str) -> MemoryCandidateView:
        try:
            result = self._repository.reject_candidate(
                owner_id=owner_id,
                candidate_id=candidate_id,
                actor_id=actor_id,
                reason_code="user_rejected",
                now=self._clock(),
            )
        except Exception:
            raise MemoryCandidateServiceError("service_unavailable") from None
        return self._mutation_view(result, expected={CandidateMutationDisposition.REJECTED, CandidateMutationDisposition.REPLAYED})

    def expire(self, *, owner_id: str, candidate_id: UUID) -> MemoryCandidateView:
        try:
            result = self._repository.expire_candidate(
                owner_id=owner_id,
                candidate_id=candidate_id,
                now=self._clock(),
            )
        except Exception:
            raise MemoryCandidateServiceError("service_unavailable") from None
        return self._mutation_view(result, expected={CandidateMutationDisposition.EXPIRED, CandidateMutationDisposition.REPLAYED})

    def accept(self, *, owner_id: str, candidate_id: UUID, actor_id: str) -> MemoryCandidateView:
        try:
            result = self._repository.accept_candidate(
                owner_id=owner_id,
                candidate_id=candidate_id,
                actor_id=actor_id,
                actor_kind=DecisionActorKind.USER,
                now=self._clock(),
                materializers=self._materializers,
            )
        except Exception:
            raise MemoryCandidateServiceError("service_unavailable") from None
        return self._mutation_view(result, expected={CandidateMutationDisposition.ACCEPTED, CandidateMutationDisposition.REPLAYED})

    def _mutation_view(
        self,
        result: CandidateMutationResult,
        *,
        expected: set[CandidateMutationDisposition],
    ) -> MemoryCandidateView:
        if not isinstance(result, CandidateMutationResult):
            raise MemoryCandidateServiceError("service_unavailable")
        if result.disposition in expected and result.candidate is not None:
            return MemoryCandidateView.from_candidate(result.candidate)
        if result.disposition is CandidateMutationDisposition.NOT_FOUND:
            raise MemoryCandidateServiceError("candidate_not_found")
        if result.disposition is CandidateMutationDisposition.TARGET_UNAVAILABLE:
            raise MemoryCandidateServiceError("memory_target_unavailable")
        if result.disposition is CandidateMutationDisposition.TARGET_INVALID:
            raise MemoryCandidateServiceError("memory_payload_invalid")
        if result.disposition is CandidateMutationDisposition.VERSION_CONFLICT:
            raise MemoryCandidateServiceError("memory_version_conflict")
        if result.disposition is CandidateMutationDisposition.TERMINAL_CONFLICT:
            raise MemoryCandidateServiceError("candidate_terminal_conflict")
        if result.disposition is CandidateMutationDisposition.EXPIRED:
            raise MemoryCandidateServiceError("candidate_expired")
        raise MemoryCandidateServiceError("service_unavailable")


__all__ = ["MemoryCandidateService", "MemoryCandidateServiceError"]
