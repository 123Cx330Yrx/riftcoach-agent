"""Local continuation contracts; no services or model requests."""
from datetime import datetime, timezone, timedelta

import pytest

from app.evaluation import sol_review_contract
from app.evaluation.sol_natural_session import CandidateSession
from app.agent.memory_context import MemoryAwareContextBuilder
from app.agent.context import ContextBuilderV1
from app.memory.context_manifest_store import FileMemoryContextManifestStore
from app.memory.context_models import MemoryContextSnapshot, MemoryContextRecordKind
from app.tasks.continuation import WORKER_SOL_PROFILE
from app.workers.sol_continuation import FrozenMemoryRepository, FrozenMemoryManifestStore
from app.workers.composition import load_worker_composition_settings, WorkerCompositionError
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_MODEL, ZHIPU_STANDARD_BASE_URL
from tests.test_memory_aware_context_builder import binding, record, execution, FakeRepository
from tests.test_worker_composition import valid_environment


def test_memory_and_manifest_are_original_across_restart(tmp_path):
    bound = binding()
    repo = FakeRepository(MemoryContextSnapshot(binding=bound, records=(
        record(kind=MemoryContextRecordKind.OWNER_PREFERENCE, suffix=1, priority=650),)))
    pins, manifests, contexts = [], [], []
    for segment in (1, 2):
        session = CandidateSession(tmp_path / "session", binding=dict(
                worker_profile=WORKER_SOL_PROFILE, task_id="worker-task", candidate_contract=sol_review_contract.VERSION),
            transport_root=tmp_path / "transport", journal_root=tmp_path / "journal",
            contract_module=sol_review_contract, worker_development=True,
            guard_sha=pins[-1]["guard_sha256"] if pins else None,
            checkpoint_sha=pins[-1]["checkpoint_sha256"] if pins else None,
            checkpoint_sink=pins.append)
        root = tmp_path / f"segment-{segment}"
        with session:
            builder = MemoryAwareContextBuilder(delegate=ContextBuilderV1(),
                repository=FrozenMemoryRepository(repo, session),
                manifest_store=FrozenMemoryManifestStore(FileMemoryContextManifestStore(root), session),
                clock=lambda: datetime(2026, 10, 30, tzinfo=timezone.utc) + timedelta(hours=segment))
            contexts.append(builder.build(execution(), memory_context_binding=bound))
        manifests.append((root / bound.run_id / "memory_context_manifest.json").read_bytes())
        repo.snapshot = MemoryContextSnapshot(binding=bound, records=())
    assert repo.calls == [bound]
    assert manifests[0] == manifests[1]
    assert contexts[0] == contexts[1]


def test_worker_development_cannot_bypass_diagnostic_gate_without_binding(tmp_path):
    with pytest.raises(ValueError, match="worker_development_binding"):
        CandidateSession(tmp_path / "session", binding={"candidate_contract": sol_review_contract.VERSION},
            transport_root=tmp_path / "transport", journal_root=tmp_path / "journal",
            contract_module=sol_review_contract, worker_development=True)


def test_candidate_route_is_explicit_and_requires_separate_credential(tmp_path):
    env = valid_environment(tmp_path)
    assert load_worker_composition_settings(env).execution_profile == "legacy"
    env["RIFTCOACH_WORKER_EXECUTION_PROFILE"] = WORKER_SOL_PROFILE
    with pytest.raises(WorkerCompositionError):
        load_worker_composition_settings(env)
    env.update(LLM_MODEL=ZHIPU_GLM53_FLASH_MODEL, LLM_BASE_URL=ZHIPU_STANDARD_BASE_URL)
    with pytest.raises(WorkerCompositionError):
        load_worker_composition_settings(env)
    env["RIFTCOACH_SOL_REVIEW_API_KEY"] = "OFFLINE_SENTINEL"
    assert load_worker_composition_settings(env).execution_profile == WORKER_SOL_PROFILE
