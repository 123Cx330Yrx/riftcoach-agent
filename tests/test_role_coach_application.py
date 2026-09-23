"""Actual adopted composition with scripted replies: plumbing, not live quality."""
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from app.evaluation.golden_role_review import RoleReviewWorkflow
from app.product.native_coach_composition import build_role_coach_application, ROLE_ASSETS, ASSETS
from app.product.recent_review import RecentReviewProductRequest
from app.product.run_receipts import FileRunReceiptStore
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.coach_contract import ROLE_COACH_CONTRACT, NATIVE_COACH_CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.reviewer_roles import RoleRoutedProvider, ROLE_COMPOSITION_ID
from app.runtime.store import RuntimeTraceStore
from scripts.native_contract_options import body
from tests.test_native_editor_product_budget import SummaryBuilder, offline
from tests.test_reviewer_role_proposal import providers


class Factory:
    def __init__(self, *, recover=False, charge_ceiling=False, reviewer_fault=None):
        self.recover, self.charge_ceiling = recover, charge_ceiling
        self.reviewer_fault = reviewer_fault
        self.descriptor = RoleRoutedProvider(*providers())
        self.providers = {}

    def __call__(self, run_id):
        generator, reviewer = providers(recover=self.recover, charge_ceiling=self.charge_ceiling)
        if self.reviewer_fault:
            original = reviewer.chat
            def fault(request):
                if self.reviewer_fault == 'transport':
                    from app.providers.errors import ProviderResponseError
                    raise ProviderResponseError(provider='zhipu', code='scripted_transport_failure')
                response = original(request)
                if self.reviewer_fault == 'receipt':
                    reviewer.last_exchange = None
                    return response
                return replace(response, model='glm-5.3-flash')
            reviewer.chat = fault
        self.providers[run_id] = RoleRoutedProvider(generator, reviewer)
        return self.providers[run_id]


def application(tmp_path, *, recover=False, charge_ceiling=False, reviewer_fault=None):
    factory = Factory(recover=recover, charge_ceiling=charge_ceiling, reviewer_fault=reviewer_fault)
    app = build_role_coach_application(summary_builder=SummaryBuilder(factory.descriptor.generator.req.player_summary),
        provider_factory=factory, knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path)
    flows = []
    actual_factory = app._runtime._execution_factory._review_workflow_factory
    def capture(runtime, provider):
        flow = actual_factory(runtime, provider)
        assert type(flow) is RoleReviewWorkflow
        flows.append(flow)
        return flow
    app._runtime._execution_factory._review_workflow_factory = capture
    return app, factory, flows


def run(app, run_id):
    return app.review(RecentReviewProductRequest(riot_id='DK ShowMaker#KR1', routing_region='asia',
        count=5, queue=420), run_id=run_id)


@pytest.mark.parametrize('recover', [False, True])
def test_role_application_uses_real_budget_observation_and_publication(tmp_path, recover):
    app, factory, flows = application(tmp_path, recover=recover)
    assert not tmp_path.joinpath('role_full').exists() and not factory.providers
    result = run(app, 'role_full')
    assert result.publication_status.value == ('rejected' if recover else 'published'), result
    trace = RuntimeTraceStore(tmp_path, 'role_full').read_trace(result.trace_reference)
    receipt = FileRunReceiptStore(tmp_path).read_receipt('role_full')
    delegate, flow = factory.providers['role_full'], flows[0]
    expected_roles = ['generation', 'generation', 'review', 'review', 'revision'] if recover else ['generation', 'generation', 'review', 'revision', 'review']
    assert [row['role'] for row in delegate.attempts] == expected_roles
    assert [row['ordinal'] for row in delegate.attempts] == list(range(1, 6))
    assert flow.send.provider.calls == 5 and flow.send.provider.tokens == 100
    assert flow.send.provider.provider._delegate is delegate
    assert trace.identity.provider_model == ROLE_COMPOSITION_ID
    assert trace.identity.coach_contract == trace.policy.coach_contract == ROLE_COACH_CONTRACT.snapshot()
    assert trace.identity.skill_version == '0.6.1' and trace.identity.prompt_profile_version == '3.1.0'
    calls = [e.signal for e in trace.events if e.signal.kind == 'provider_call_started']
    assert [c.ordinal for c in calls] == list(range(1, 6))
    assert [c.model for c in calls] == ['glm-5.3' if role == 'review' else 'glm-5.3-flash' for role in expected_roles]
    assert trace.usage.provider_calls_attempted == trace.usage.provider_responses_observed == 5
    assert trace.usage.input_tokens == trace.usage.output_tokens == 50
    assert trace.usage.cost == Decimal('0.000828')
    assert trace.usage.currency == 'CNY'
    assert delegate.reviewer.knowledge_count == 5
    assert any(m.role.value == 'tool' for m in delegate.generator.requests[1].messages)
    assert receipt.report_available is (not recover)
    if recover:
        assert flow.stopped and flow.send.provider.stopped and result.output.report is None
        assert flow.send.provider.last_exchange is None
    else:
        assert flow._expected_recheck.source.report == delegate.generator.edit['report']
        assert body(delegate.reviewer.requests[-1]) != body(delegate.reviewer.requests[0])
        assert flow.last_journal['source_projection'] == 'native-explicit-source-projection-v1'
        assert flow.last_journal['policy_sha256'] != flow.last_journal['validator_policy_sha256']
        assert result.output.report is not None


@pytest.mark.parametrize('fault,observed', [('receipt',3),('transport',2),('model',2)])
def test_role_application_failure_preserves_usage_and_never_publishes(tmp_path, fault, observed):
    app, factory, flows = application(tmp_path, reviewer_fault=fault)
    result = run(app, 'role_failure')
    assert result.publication_status.value == 'rejected', result
    assert result.output is None or result.output.report is None
    trace = RuntimeTraceStore(tmp_path, 'role_failure').read_trace(result.trace_reference)
    assert trace.usage.provider_calls_attempted == 3
    assert trace.usage.provider_responses_observed == observed
    assert trace.usage.observed_input_tokens == trace.usage.observed_output_tokens == observed * 10
    if fault == 'receipt':
        assert trace.usage.cost == Decimal('0.000432')
        assert flows[0].send.provider.tokens == 60
    else:
        assert trace.usage.input_tokens is None and trace.usage.cost is None
        assert flows[0].send.provider.reserved_tokens > 0
    assert len(factory.providers['role_failure'].attempts) == 3


def test_role_candidate_asset_and_contract_cannot_be_mixed():
    root = RuntimeCompositionRoot.from_directories(skills_root=ROLE_ASSETS/'skills',
        prompt_programs_root=ROLE_ASSETS/'prompt_programs', coach_contract=ROLE_COACH_CONTRACT)
    assert len(root.prompt_program_resolver.verify_all()) == 1
    for assets, contract in ((ROLE_ASSETS,NATIVE_COACH_CONTRACT),(ASSETS,ROLE_COACH_CONTRACT)):
        with pytest.raises(ValueError):
            RuntimeCompositionRoot.from_directories(skills_root=assets/'skills',
                prompt_programs_root=assets/'prompt_programs', coach_contract=contract)


def test_role_full_output_reservations_fit_single_existing_task_budget(tmp_path):
    app, factory, flows = application(tmp_path, charge_ceiling=True)
    result = run(app, 'role_full_reserve')
    assert result.publication_status.value == 'published', result
    budget = flows[0].send.provider
    assert budget.calls == 5 and 0 < budget.tokens <= 401920
    assert budget.reserved_tokens == 0
    trace = RuntimeTraceStore(tmp_path, 'role_full_reserve').read_trace(result.trace_reference)
    assert trace.usage.input_tokens + trace.usage.output_tokens == budget.tokens


def test_role_observed_task_preserves_memory_identity_and_evidence_store(tmp_path):
    import json
    from datetime import datetime, timezone
    from app.evidence.publication_store import FileEvidencePublicationStore
    from app.memory.context_models import MemoryContextSnapshot
    from app.players.models import RelationshipRole
    from app.product.recent_review import ConversationRecentReviewRequest
    from tests.test_evidence_publication import context, sources
    from tests.test_memory_aware_context_builder import FakeRepository, FakeManifestStore, binding
    factory = Factory()
    summary = SummaryBuilder(factory.descriptor.generator.req.player_summary)
    for row in summary.summary['matches']:
        row.update(champion_id=75, queue_id=420, game_version='16.16.804.9184')
    ctx = context('role_observed')
    memory = binding(ctx.run_id).model_copy(update={
        'owner_id':ctx.owner_id, 'relationship_role':RelationshipRole.OBSERVED})
    repo = FakeRepository(MemoryContextSnapshot(binding=memory, records=()))
    store = FileEvidencePublicationStore(tmp_path)
    app = build_role_coach_application(summary_builder=summary, provider_factory=factory,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path, memory_repository=repo, memory_manifest_store=FakeManifestStore(),
        publication_sources=replace(sources(), now=datetime(2026, 9, 23, tzinfo=timezone.utc)),
        publication_writer=store)
    result = app.review_by_puuid(ConversationRecentReviewRequest(count=5, queue=420), puuid='private',
        routing_region='asia', game_name='DK ShowMaker', tag_line='KR1', run_id=ctx.run_id,
        memory_context_binding=memory, publication_context=ctx)
    assert result.publication_status.value == 'published', result
    manifest = store.read(ctx)
    assert manifest.report is not None and repo.calls == [memory]
    pending = store.read_pending_snapshot(ctx)
    assert pending.owner_id == ctx.owner_id and pending.task_id == ctx.task_id and pending.run_id == ctx.run_id
    provider = factory.providers[ctx.run_id]
    payloads = [json.loads(m.content)["data"] for m in provider.generator.requests[1].messages
        if m.role.value == "tool"]
    assert len(payloads) == 5 and all(p["retrieved_at"].endswith("Z") for p in payloads)
    for review_request in (provider.reviewer.requests[0], provider.generator.requests[-1], provider.reviewer.requests[-1]):
        knowledge = body(review_request)["knowledge"]
        assert [r["retrieved_at"] for r in knowledge["retrievals"]] == [p["retrieved_at"] for p in payloads]
        assert [r["chunk_ids"] for r in knowledge["retrievals"]] == [[c["chunk_id"] for c in p["chunks"]] for p in payloads]
    stored = json.loads(next(tmp_path.rglob("retrieval_evidence.json")).read_text(encoding="utf-8"))
    assert stored["retrievals"] == knowledge["retrievals"]
    for request in (provider.generator.requests[0], provider.reviewer.requests[-1]):
        assert '不是阅读者本人' in ''.join(m.content or '' for m in request.messages)
    trace = RuntimeTraceStore(tmp_path, ctx.run_id).read_trace(result.trace_reference)
    assert trace.usage.provider_calls_attempted == 5

@pytest.mark.parametrize("source", ["app/providers/zhipu_profiles.py", "app/runtime/coach_contract.py",
    "app/tools/adapters/knowledge.py", "app/harness/knowledge.py", "app/harness/adapters.py", "app/harness/runtime.py"])
def test_role_manifest_rejects_execution_source_drift_with_unchanged_labels(monkeypatch, source):
    target = (Path(__file__).resolve().parents[1] / source).resolve()
    original = Path.read_text
    def changed(path, *args, **kwargs):
        text = original(path, *args, **kwargs)
        if path.resolve() == target:
            before, after = (('reasoning_effort="high"', 'reasoning_effort="low"')
                if source.endswith("zhipu_profiles.py") else ("def require_provider(self, provider):",
                    "def require_provider(self, provider):\n        return None") if source.endswith("coach_contract.py")
                else ("from __future__ import annotations", "from __future__ import annotations\n# drift probe"))
            assert before in text
            return text.replace(before, after)
        return text
    monkeypatch.setattr(Path, "read_text", changed)
    with pytest.raises(ValueError, match="fingerprint|drift|component"):
        RuntimeCompositionRoot.from_directories(skills_root=ROLE_ASSETS/"skills",
            prompt_programs_root=ROLE_ASSETS/"prompt_programs", coach_contract=ROLE_COACH_CONTRACT)
