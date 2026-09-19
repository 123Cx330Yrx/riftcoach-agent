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
        assert trace.identity.skill_version == '0.6.0' and trace.identity.prompt_profile_version == '3.0.0'
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
