"""Explicit Flash/Sol execution through the ordinary Worker.

Each lease gets a new derived Runtime directory. Successful source, tool and
model operations replay from the original session; its budget is cumulative.
The final segment is copied byte-for-byte to the existing query boundary.
"""
import json
from pathlib import Path

from app.evaluation import sol_review_contract as default_contract
from app.evaluation.sol_natural_session import CandidateSession, SessionBlocked, SessionPaused
from app.product.session_usage import session_accounting
from app.product.natural_duty_candidate import build_natural_duty_candidate
from app.runtime.dispatch_control import require_dispatch_allowed
from app.tasks.continuation import (ContinuationError,
                                    TaskExecutionPause, WORKER_SOL_PROFILE, WORKER_SOL_PRODUCT_PROFILE, contract_for_worker_profile)
from app.tasks.recent_review_executor import RecentReviewTaskExecutor
from app.tasks.reconciliation import RecentReviewTerminalEvidenceVerifier


class FrozenSummaryBuilder:
    def __init__(self, delegate, session):
        self.delegate, self.session = delegate, session

    def _build(self, name, kwargs):
        require_dispatch_allowed()
        value, _ = self.session.operation("source", dict(method=name, arguments=kwargs),
            lambda: getattr(self.delegate, name)(**kwargs))
        return value

    def build(self, **kwargs):
        return self._build("build", kwargs)

    def build_by_puuid(self, **kwargs):
        return self._build("build_by_puuid", kwargs)


class FrozenMemoryRepository:
    def __init__(self, delegate, session):
        self.delegate, self.session = delegate, session

    def load(self, binding):
        from app.memory.context_models import MemoryContextSnapshot
        value, _ = self.session.operation("memory", binding.model_dump(mode="json"),
            lambda: self.delegate.load(binding).model_dump(mode="json"))
        return MemoryContextSnapshot.model_validate_json(json.dumps(value))


class FrozenMemoryManifestStore:
    def __init__(self, delegate, session):
        self.delegate, self.session = delegate, session

    def write(self, manifest):
        from app.memory.context_models import MemoryContextManifest
        value, _ = self.session.operation("memory-manifest",
            manifest.model_dump(mode="json", exclude={"created_at"}),
            lambda: manifest.model_dump(mode="json"))
        return self.delegate.write(MemoryContextManifest.model_validate_json(json.dumps(value)))


def frozen_publication_sources(delegate, session):
    """Retain the actual first Evidence projection across leases.

    Re-projecting at a new wall-clock time changes the bundle digest embedded
    in the model input, even when every materialized source is unchanged.
    A resumed task consumes the original projection and its original times.
    """
    from pydantic import TypeAdapter
    from app.evidence.publication import EvidencePublicationSources, canonical_bytes, sha256_bytes
    from app.evidence.summary_bridge import SummaryEvidenceProjection

    projection_type = TypeAdapter(SummaryEvidenceProjection)

    class FrozenSources(EvidencePublicationSources):
        def project(self, summary, *, routing_region):
            value, _ = session.operation("publication-source", {
                "summary_sha256": sha256_bytes(canonical_bytes(summary)),
                "routing_region": routing_region,
            }, lambda: projection_type.dump_python(
                delegate.project(summary, routing_region=routing_region), mode="json"))
            return projection_type.validate_json(json.dumps(value))

    return FrozenSources(now=delegate.now)


def promote_segment(source, target):
    """Create-only publication of real files, never synthetic replay events."""
    source, target = Path(source), Path(target)
    if source.resolve() != source.absolute() or target.resolve() != target.absolute():
        raise SessionBlocked("session_projection_path_unsafe")
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise SessionBlocked("session_segment_symlink")
        if not path.is_file():
            continue
        destination = target / path.relative_to(source)
        if destination.is_symlink() or destination.resolve() != destination.absolute():
            raise SessionBlocked("session_projection_changed")
        data = path.read_bytes()
        if destination.exists():
            if destination.read_bytes() != data:
                raise SessionBlocked("session_projection_changed")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(data)


class SolContinuationExecutor:
    def __init__(self, *, store, runs_root, summary_builder, provider_factory_builder,
                 knowledge_provider, memory_repository=None, publication_sources=None,
                 max_new_models=None, contract_module=default_contract, manual_retry_grant=None):
        self.store, self.root = store, Path(runs_root).resolve()
        self.summary_builder, self.factories = summary_builder, provider_factory_builder
        self.knowledge = knowledge_provider
        self.memory = memory_repository
        self.publication_sources = publication_sources
        self.max_new_models = max_new_models
        self.manual_retry_grant = manual_retry_grant
        self.contract = contract_module
        self.profile = (WORKER_SOL_PROFILE if contract_module is default_contract else WORKER_SOL_PRODUCT_PROFILE)
        if contract_for_worker_profile(self.profile) is not contract_module:
            raise ValueError("worker_contract_binding")

    def execute(self, task):
        contract = self.contract
        binding = dict(worker_profile=self.profile,
            adapter_version=2 if task.publication_mode.value == "evidence_bound_v1" else 1,
            candidate_contract=contract.VERSION, task_id=str(task.task_id),
            run_id=task.run_id, owner_id=task.owner_id,
            request_fingerprint=task.request_fingerprint,
            publication_mode=task.publication_mode.value)
        try:
            saved = self.store.begin(task, binding)
        except ContinuationError as exc:
            return TaskExecutionPause(task.run_id, exc.code)
        # Inside the existing owner/run deletion boundary, including raw source
        # and Memory snapshots; deleting a task must not orphan private inputs.
        private = self.root / task.run_id / ".continuation"
        if private.resolve() != private:
            return TaskExecutionPause(task.run_id, "session_path_unsafe")
        derived = private / "segments" / str(task.lease_generation)
        transport = private / "transport"
        session = CandidateSession(private / "session", binding=binding,
            transport_root=transport / task.run_id, journal_root=private / "journal",
            guard_sha=saved["guard_sha256"], checkpoint_sha=saved["checkpoint_sha256"],
            contract_module=contract, worker_development=self.profile == WORKER_SOL_PROFILE,
            worker_product=self.profile == WORKER_SOL_PRODUCT_PROFILE,
            manual_retry=saved["manual_retry"], before_new_model=require_dispatch_allowed,
            manual_retry_grant=self.manual_retry_grant,
            max_new_models=self.max_new_models,
            checkpoint_sink=lambda value: self.store.pin(task,
                {**value, "checkpoint": Path(value["checkpoint"]).name}, session_accounting(session)))
        try:
            with session:
                closed = session.root / "terminal.json"
                if closed.exists():
                    original = json.loads(closed.read_bytes())["value"]
                    prior = private / "segments" / str(original["segment"])
                    promote_segment(prior / task.run_id, self.root / task.run_id)
                    return RecentReviewTerminalEvidenceVerifier(self.root).terminal_for(task)
                from app.evidence.publication_store import FileEvidencePublicationStore
                from app.memory.context_manifest_store import FileMemoryContextManifestStore
                from app.tasks.models import TaskPublicationMode
                sources = (self.publication_sources if task.publication_mode is
                           TaskPublicationMode.EVIDENCE_BOUND_V1 else None)
                if sources is not None:
                    sources = frozen_publication_sources(sources, session)
                app = build_natural_duty_candidate(
                    summary_builder=FrozenSummaryBuilder(self.summary_builder, session),
                    provider_factory=self.factories(transport), knowledge_provider=self.knowledge,
                    runs_root=derived, candidate=contract, execution_session=session,
                    memory_repository=FrozenMemoryRepository(self.memory, session) if self.memory else None,
                    memory_manifest_store=FrozenMemoryManifestStore(FileMemoryContextManifestStore(derived), session) if self.memory else None,
                    publication_sources=sources,
                    publication_writer=FileEvidencePublicationStore(derived) if sources else None)
                executor = RecentReviewTaskExecutor(application_service=app,
                    evidence_verifier=RecentReviewTerminalEvidenceVerifier(derived), runs_root=derived)
                try:
                    terminal = executor.execute(task)
                except Exception:
                    # Cancellation/ordinary failure can leave a real receipt.
                    # Copy it once; a projection conflict itself pauses below.
                    if (derived / task.run_id / "api_run_receipt.json").exists():
                        promote_segment(derived / task.run_id, self.root / task.run_id)
                    raise
                session.close(dict(run_id=task.run_id, segment=task.lease_generation,
                    terminal_reason=terminal.terminal_reason))
                promote_segment(derived / task.run_id, self.root / task.run_id)
                return terminal
        except (SessionPaused, SessionBlocked) as exc:
            return TaskExecutionPause(task.run_id, str(exc))
        except (OSError, ValueError):
            return TaskExecutionPause(task.run_id, "session_integrity_required")
class ContinuationRoutingExecutor:
    """An old-profile Worker may not accidentally restart an adopted task."""
    def __init__(self, store, legacy, candidate=None):
        self.store, self.legacy, self.candidate = store, legacy, candidate

    def execute(self, task):
        saved = self.store.load(owner_id=task.owner_id, task_id=task.task_id)
        if self.candidate is not None:
            return self.candidate.execute(task)
        if saved is not None:
            return TaskExecutionPause(task.run_id, "continuation_profile_unavailable")
        return self.legacy.execute(task)
