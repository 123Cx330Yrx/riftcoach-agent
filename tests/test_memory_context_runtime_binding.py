from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from app.memory.context_models import MemoryContextBinding
from app.players.models import RelationshipRole
from app.runtime.models import RuntimeRunRequest
from tests.test_runtime_models import execution_request, policy


def binding(run_id: str = "runtime_contract_demo") -> MemoryContextBinding:
    return MemoryContextBinding(
        run_id=run_id,
        owner_id="owner-runtime",
        conversation_id=UUID("40000000-0000-0000-0000-000000000001"),
        relationship_id=UUID("40000000-0000-0000-0000-000000000002"),
        player_subject_id=UUID("40000000-0000-0000-0000-000000000003"),
        relationship_role=RelationshipRole.SELF,
    )


def test_runtime_request_accepts_matching_private_memory_context_binding() -> None:
    request = RuntimeRunRequest(
        execution_request=execution_request(),
        policy=policy(),
        memory_context_binding=binding(),
    )

    assert request.memory_context_binding == binding()


def test_runtime_request_rejects_context_run_identity_drift() -> None:
    with pytest.raises(ValidationError, match="run_id"):
        RuntimeRunRequest(
            execution_request=execution_request(),
            policy=policy(),
            memory_context_binding=binding("other_run"),
        )
