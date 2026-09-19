"""Offline product plumbing; scripted opinions do not establish model quality."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket

import pytest

from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.product.native_coach_composition import build_native_coach_application, ASSETS
from app.product.run_receipts import FileRunReceiptStore
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.coach_contract import NATIVE_COACH_CONTRACT, BATCH_COACH_CONTRACT
from app.runtime.store import RuntimeTraceStore
from tests.test_coach_application_composition import SummaryBuilder, product_request
from tests.test_coach_contract_repair import GroundedProvider


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('native product replay must stay offline')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


class Provider(GroundedProvider):
    last_exchange = None
    def chat(self, request):
        if request.response_contract:
            self.requests.append(request)
            response = self._text('invalid response' if getattr(self, 'reject', False) else
                json.dumps(dict(score=95, verdict='pass', issues=[], issue_resolutions=[])))
        else:
            response = super().chat(request)
        response = replace(response, finish_reason='tool_calls' if response.tool_calls else 'stop')
        self.last_exchange = Exchange(request, response,
            hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
        return response


class Factory:
    descriptor = Provider(provider_name='zhipu', model_name='glm-5.3-flash')
    def __init__(self, reject=False): self.providers, self.reject = {}, reject
    def __call__(self, run_id):
        self.providers[run_id] = Provider(provider_name='zhipu', model_name='glm-5.3-flash')
        self.providers[run_id].reject = self.reject
        return self.providers[run_id]


def test_native_application_roundtrips_report_receipt_and_distinct_contract(tmp_path):
    factory = Factory()
    service = build_native_coach_application(summary_builder=SummaryBuilder(),
        provider_factory=factory, knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path/'runs')
    assert not (tmp_path/'runs').exists() and not factory.providers
    for run_id in ('first', 'second'):
        result = service.review(product_request(), run_id=run_id)
        assert result.publication_status.value == 'published', result
        trace = RuntimeTraceStore(tmp_path/'runs',run_id).read_trace(result.trace_reference)
        receipt = FileRunReceiptStore(tmp_path/'runs').read_receipt(run_id)
        assert trace.identity.coach_contract == trace.policy.coach_contract == NATIVE_COACH_CONTRACT.snapshot()
        assert trace.identity.skill_version == '0.6.0' and trace.identity.prompt_profile_version == '3.0.4'
        assert receipt.trace_reference == result.trace_reference and receipt.report_available
        assert len(factory.providers[run_id].requests) == 3
        assert factory.providers[run_id].requests[-1].response_contract.version == '3.1.0'
        report = next(row for row in trace.artifacts if row.kind == 'final_report')
        content = (tmp_path/'runs'/run_id/report.relative_path).read_bytes()
        assert hashlib.sha256(content).hexdigest() == report.sha256
    assert factory.providers['first'] is not factory.providers['second']
    assert BATCH_COACH_CONTRACT.snapshot().sha256 == 'f8fb878e1d94b4251a990db337d0adaf6a354417890ac296dcd9a83e04fd0e66'


def test_native_assets_cannot_resolve_as_legacy_program():
    from app.runtime.composition import RuntimeCompositionRoot
    with pytest.raises(ValueError):
        RuntimeCompositionRoot.from_directories(skills_root=ASSETS/'skills', prompt_programs_root=ASSETS/'prompt_programs')


@pytest.mark.parametrize('reject', [False, True])
def test_native_observed_task_publishes_verified_evidence_and_never_failed_report(tmp_path, reject):
    from app.evidence.publication_store import FileEvidencePublicationStore
    from app.memory.context_models import MemoryContextSnapshot
    from app.players.models import RelationshipRole
    from app.product.recent_review import ConversationRecentReviewRequest
    from tests.test_evidence_publication import context, sources
    from tests.test_memory_aware_context_builder import FakeRepository, FakeManifestStore, binding
    summary = SummaryBuilder()
    summary.summary['metadata']['matches_requested'] = summary.summary['request']['count'] = 5
    for row in summary.summary['matches']:
        row.update(champion_id=75, queue_id=420, game_version='16.16.804.9184')
    ctx = context('native_observed')
    memory = binding(ctx.run_id).model_copy(update={'owner_id':ctx.owner_id, 'relationship_role':RelationshipRole.OBSERVED})
    repo = FakeRepository(MemoryContextSnapshot(binding=memory, records=()))
    factory, store = Factory(reject=reject), FileEvidencePublicationStore(tmp_path)
    app = build_native_coach_application(summary_builder=summary, provider_factory=factory,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')), runs_root=tmp_path,
        memory_repository=repo, memory_manifest_store=FakeManifestStore(),
        publication_sources=sources(), publication_writer=store)
    result = app.review_by_puuid(ConversationRecentReviewRequest(count=5,queue=420),
        puuid='private', routing_region='asia', game_name='RiftCoachDemo',tag_line='TEST',
        run_id=ctx.run_id, memory_context_binding=memory, publication_context=ctx)
    manifest = store.read(ctx)
    assert result.publication_status.value == ('rejected' if reject else 'published')
    assert (manifest.report is None) is reject
    pending = store.read_pending_snapshot(ctx)
    assert pending.owner_id == ctx.owner_id and pending.task_id == ctx.task_id and pending.run_id == ctx.run_id
    assert repo.calls == [memory]
    assert '不是阅读者本人' in ''.join(m.content or '' for m in factory.providers[ctx.run_id].requests[0].messages)
    assert '不是阅读者本人' in ''.join(m.content or '' for m in factory.providers[ctx.run_id].requests[-1].messages)
    assert len(factory.providers[ctx.run_id].requests) == 3


@pytest.mark.parametrize('outcome', ['published', 'rejected', 'ownership_lost'])
def test_native_observed_worker_requires_atomic_evidence_before_conversation_turn(tmp_path, outcome):
    from types import SimpleNamespace
    from app.evidence.publication_store import FileEvidencePublicationStore
    from app.memory.context_manifest_store import FileMemoryContextManifestStore
    from app.memory.context_models import MemoryContextSnapshot
    from app.players.models import RelationshipRole, RoutingRegion
    from app.product.recent_review import ConversationRecentReviewRequest
    from app.product.run_query import RunQueryService
    from app.tasks.fingerprint import compute_conversation_review_task_fingerprint
    from app.tasks.models import ConversationReviewExecutionTarget, ConversationReviewTaskBinding, TaskPublicationMode
    from app.tasks.recent_review_executor import RecentReviewTaskExecutor
    from app.tasks.reconciliation import RecentReviewTerminalEvidenceVerifier
    from app.tasks.reliable_runtime import TaskHeartbeatDisposition, TaskLeasePolicy
    from app.workers.review_worker import ReviewWorker
    from tests.test_evidence_publication import sources
    from tests.test_memory_aware_context_builder import FakeRepository, binding
    from tests.test_reliable_review_worker import Repository, NOW

    disposition = TaskHeartbeatDisposition.LOST if outcome == 'ownership_lost' else TaskHeartbeatDisposition.ACTIVE
    repository = Repository(dispositions=[disposition])
    original = repository.claim
    memory = binding(original.run_id).model_copy(update={
        'owner_id': original.owner_id, 'relationship_role': RelationshipRole.OBSERVED})
    task_binding = ConversationReviewTaskBinding(**memory.model_dump(exclude={'run_id', 'owner_id'}))
    payload = ConversationRecentReviewRequest(count=5, queue=420).model_dump(mode='json')
    repository.claim = original.model_copy(update={
        'schema_version': '2.0', 'publication_mode': TaskPublicationMode.EVIDENCE_BOUND_V1,
        'request_payload': payload, 'conversation_binding': task_binding,
        'request_fingerprint': compute_conversation_review_task_fingerprint(
            owner_id=original.owner_id, binding=task_binding, request_payload=payload),
        'execution_target': ConversationReviewExecutionTarget(puuid='private-observed-player',
            routing_region=RoutingRegion.ASIA, game_name='RiftCoachDemo', tag_line='TEST')})
    summary = SummaryBuilder()
    summary.summary['metadata']['matches_requested'] = summary.summary['request']['count'] = 5
    for row in summary.summary['matches']:
        row.update(champion_id=75, queue_id=420, game_version='16.16.804.9184')
    factory = Factory(reject=outcome == 'rejected')
    for row in summary.summary['matches']:
        row.setdefault('objective_events', [])  # The older report-only fixture omits this collection.
    application = build_native_coach_application(summary_builder=summary, provider_factory=factory,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path, memory_repository=FakeRepository(MemoryContextSnapshot(binding=memory, records=())),
        memory_manifest_store=FileMemoryContextManifestStore(tmp_path), publication_sources=sources(),
        publication_writer=FileEvidencePublicationStore(tmp_path))
    executor = RecentReviewTaskExecutor(application_service=application,
        evidence_verifier=RecentReviewTerminalEvidenceVerifier(tmp_path), runs_root=tmp_path)
    turns = []

    def write_turn(turn):
        assert len(repository.succeed_with_evidence_calls) == 1
        assert not repository.succeed_calls
        turns.append(turn)
        return SimpleNamespace(message_id='native-terminal-message')

    result = ReviewWorker(repository=repository, executor=executor, worker_id=original.worker_id,
        clock=lambda: NOW, lease_policy=TaskLeasePolicy(lease_seconds=360, heartbeat_seconds=60),
        terminal_turn_writer=SimpleNamespace(write=write_turn)).run_once()
    assert not repository.succeed_calls and not repository.fail_calls
    assert len(factory.providers[original.run_id].requests) == 3
    if outcome == 'ownership_lost':
        assert result.status.value == 'ownership_lost'
        assert not repository.succeed_with_evidence_calls and not turns
        return
    assert result.status.value == 'succeeded'
    committed = repository.succeed_with_evidence_calls[0]
    terminal = committed['terminal']
    assert terminal.publication_status.value == outcome
    assert committed['pending_snapshot'].owner_id == original.owner_id
    assert committed['pending_snapshot'].task_id == original.task_id
    assert committed['pending_snapshot'].run_id == original.run_id
    assert committed['publication_reference']['summary_digest'] == committed['summary_digest']
    assert terminal.report_available is (outcome == 'published')
    if outcome == 'published':
        assert len(turns) == 1 and turns[0].binding == memory
        query = RunQueryService(tmp_path)
        report = query.get_report(original.run_id)
        assert turns[0].assistant_content == report.strip()  # Existing typed text normalization.
        assert turns[0].artifact_reference == terminal.artifact_reference
        assert hashlib.sha256(report.encode()).hexdigest() == terminal.artifact_reference.sha256
        assert query.get_recent_summary(original.run_id).skill_version == '0.6.0'
        assert query.get_timeline(original.run_id).run_id == original.run_id
    else:
        assert not turns and terminal.artifact_reference is None


@pytest.mark.parametrize('expired', [False, True])
def test_publication_sources_reach_generation_review_and_saved_evidence(tmp_path, expired):
    from datetime import datetime, timedelta, timezone
    from app.evidence.publication import EvidencePublicationSources
    from app.evidence.publication_store import FileEvidencePublicationStore
    from app.evaluation.golden_contextual_sources import MARKER
    from tests.test_evidence_fusion_vertical import _meta, _patch, _static
    from tests.test_evidence_publication import context

    summary = SummaryBuilder()
    summary.summary['metadata']['matches_requested'] = summary.summary['request']['count'] = 5
    summary.summary['request'].update(data_dragon_version='15.16.1', data_dragon_language='zh_CN')
    for i, row in enumerate(summary.summary['matches']):
        row.update(champion_id=i+1, queue_id=420, game_version='15.16.100.1')
    retrieved = datetime(2026, 9, 7, tzinfo=timezone.utc)
    meta = replace(_meta(), position='mid', retrieved_at=retrieved,
        expires_at=retrieved+timedelta(minutes=15), facts=tuple(
            replace(_meta().facts[0], champion=row['champion_name_en'], rank=i+1)
            for i, row in enumerate(summary.summary['matches'])))
    src = EvidencePublicationSources(now=retrieved+timedelta(hours=1) if expired else retrieved,
        data_dragon=_static(), official_patch=_patch(), meta_evidence=(meta,))
    ctx = context('native_sources')
    factory, store = Factory(), FileEvidencePublicationStore(tmp_path)
    app = build_native_coach_application(summary_builder=summary, provider_factory=factory,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path, publication_sources=src, publication_writer=store)
    result = app.review(product_request(), run_id=ctx.run_id, publication_context=ctx)
    assert result.publication_status.value == 'published'
    manifest = store.read(ctx)
    saved = (tmp_path/ctx.run_id/'inputs/deterministic_report.md').read_text(encoding='utf-8')
    line, = [row[len(MARKER):] for row in saved.splitlines() if row.startswith(MARKER)]
    external = json.loads(line)
    assert external['bundle_digest'] == manifest.bundle.bundle_digest
    assert external['official_patch']['source_digest'] == _patch().source_digest
    assert external['data_dragon']['catalog_digest'] == _static().catalog_digest
    assert bool(external['opgg']) is not expired
    assert bool(external['omitted_opgg']) is expired
    requests = factory.providers[ctx.run_id].requests
    for request in requests:
        content = ''.join(m.content or '' for m in request.messages)
        assert manifest.bundle.bundle_digest in content
        assert _patch().source_digest in content and _static().catalog_digest in content
        assert meta.digest in content
    evaluation_source = requests[-1].messages[-1].content
    assert line in evaluation_source
    assert result.evidence_projection.bundle.digest == manifest.bundle.bundle_digest


def test_native_source_renderer_rejects_different_summary_without_model_io():
    from copy import deepcopy
    from app.product.native_coach_composition import render_native_publication_context
    from tests.test_golden_source_context import projection
    from tests.test_evidence_summary_bridge import summary
    value = summary()
    changed = deepcopy(value)
    changed['matches'][0]['win'] = False
    with pytest.raises(ValueError, match='native_publication_summary_mismatch'):
        render_native_publication_context('report', changed, projection(value))


def test_product_live_run_is_blocked_before_input_or_credentials(monkeypatch):
    from types import SimpleNamespace
    from scripts import run_native_coach_product as runner
    monkeypatch.setattr(runner, 'prepare', lambda *_: pytest.fail('must not prepare or call'))
    with pytest.raises(ValueError, match='native_product_semantic_qualification_required'):
        runner.run(SimpleNamespace(execute=True))
