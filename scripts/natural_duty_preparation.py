"""Frozen public source -> actual application -> first-send boundary, offline.

Temporary runtime artifacts are removed after capture. No old report, opinion,
label or selected knowledge is loaded; the future Agent chooses its own tools.
"""
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import NAMESPACE_URL, uuid5

from app.evaluation.natural_duty_contract import CONTRACT, ROOT, NaturalDutyProvider, request_bytes
from app.evidence.publication import EvidencePublicationContext, EvidencePublicationSources
from app.evidence.publication_store import FileEvidencePublicationStore
from app.evidence.storage import bundle_from_storage_projection
from app.harness.run_ids import normalize_run_id
from app.memory.context_manifest_store import FileMemoryContextManifestStore
from app.memory.context_models import MemoryContextBinding, MemoryContextSnapshot
from app.players.models import RelationshipRole
from app.product.natural_duty_candidate import ASSETS, build_natural_duty_candidate
from app.product.recent_review import ConversationRecentReviewRequest
from app.providers.zhipu import ZhipuProvider
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.reviewer_roles import profile_for_role

SOURCES = ROOT/'data/evaluation/fixtures/natural_duty_observed_source_20261015'
SOURCE_SHA = {
    'evidence_bundle.json': '6d5ab97ba85f92cf650f05740956b8033e0b8a5093f846268f71ae3c5243dab8',
    'player_summary.json': '13cb231e905c5a7fd2e4edbaa7a6a18be6fb47fbbc6ea7601d7b4d9519ed2132',
}
SOURCE_NOW = '2026-09-10T12:15:28.980990+00:00'
LIMITS = dict(max_calls=6, total_tokens=401920, execution_timeout_s=900, request_timeout_s=300,
              max_input_tokens=64000, max_output_tokens=32768, sdk_retries=0)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def inventory(paths, *, root=ROOT):
    return {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in sorted(paths) if p.is_file()}


def load_sources():
    values = {}
    for name, expected in SOURCE_SHA.items():
        raw = (SOURCES/name).read_bytes()
        if sha(raw) != expected:
            raise ValueError('natural_source_changed')
        values[name] = json.loads(raw)
    return values['player_summary.json'], bundle_from_storage_projection(values['evidence_bundle.json'])


class EmptyObservedMemory:
    def load(self, binding):
        return MemoryContextSnapshot(binding=binding, records=())


@dataclass(frozen=True)
class PreparedApplication:
    app: object
    request: ConversationRecentReviewRequest
    memory: MemoryContextBinding
    context: EvidencePublicationContext

    def run(self):
        return self.app.review_by_puuid(self.request, puuid='frozen-public-observation', routing_region='asia',
            game_name='DK ShowMaker', tag_line='KR1', run_id=self.context.run_id,
            memory_context_binding=self.memory, publication_context=self.context)


def build_application(*, provider_factory, output_root, run_id, candidate=None, execution_session=None):
    if normalize_run_id(run_id) != run_id:
        raise ValueError('natural_run_id')
    summary, bundle = load_sources()
    output_root = Path(output_root)
    context = EvidencePublicationContext(owner_id='natural-duty-development',
        task_id=uuid5(NAMESPACE_URL, 'natural-duty:'+run_id), run_id=run_id,
        request_fingerprint=sha(canonical(dict(count=5, queue=420, focus='overall', role='observed'))))
    memory = MemoryContextBinding(run_id=run_id, owner_id=context.owner_id,
        conversation_id=uuid5(NAMESPACE_URL, run_id+':conversation'),
        relationship_id=uuid5(NAMESPACE_URL, run_id+':relationship'),
        player_subject_id=uuid5(NAMESPACE_URL, 'riftcoach:ShowMaker'), relationship_role=RelationshipRole.OBSERVED)

    class Summary:
        def build(self, **kwargs):
            return deepcopy(summary)

        def build_by_puuid(self, **kwargs):
            return deepcopy(summary)

    app = build_natural_duty_candidate(summary_builder=Summary(), provider_factory=provider_factory,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(ROOT/'data/rag_docs'),
        runs_root=output_root/'reports', memory_repository=EmptyObservedMemory(),
        memory_manifest_store=FileMemoryContextManifestStore(output_root/'reports'),
        publication_sources=EvidencePublicationSources(now=datetime.fromisoformat(SOURCE_NOW),
            data_dragon=bundle.data_dragon, official_patch=bundle.official_patch, meta_evidence=bundle.meta_evidence),
        publication_writer=FileEvidencePublicationStore(output_root/'reports'), candidate=candidate,
        execution_session=execution_session)
    return PreparedApplication(app, ConversationRecentReviewRequest(count=5, queue=420, focus='overall'), memory, context)


class _Captured(BaseException):
    pass


class CaptureFactory:
    """No network implementation, credential loader or synthetic response."""
    def __init__(self):
        self.first = self.compiled = None
        self.descriptor = self.make()

    def make(self):
        outer = self

        class Capture:
            provider_name, sdk_max_retries, runtime_profile = 'zhipu', 0, None
            capabilities = ZhipuProvider.capabilities

            def __init__(self, role):
                profile = profile_for_role(role)
                self.model_name, self.thinking_profile_id = profile.model, profile.profile_id

            def chat(self, request):
                if outer.first is not None:
                    raise AssertionError('offline capture attempted another request')
                request_bytes(request)
                outer.first = request
                raise _Captured()

        return NaturalDutyProvider(Capture('generation'), Capture('review'))

    def __call__(self, run_id):
        return self.make()


def cost_envelope():
    prices = CONTRACT.pricing_profiles
    flash, glm = [prices['zhipu', model] for model in ('glm-5.3-flash', 'glm-5.3')]
    # >=1 generation, <=4 reviews; maximize costly categories under ONE budget.
    remaining, cost = LIMITS['total_tokens'], Decimal(0)
    for cap, rate in ((4*32768, glm.output_cost_per_million), (4*64000, glm.input_cost_per_million),
                     (2*32768, flash.output_cost_per_million), (2*64000, flash.input_cost_per_million)):
        n = min(remaining, cap)
        cost += Decimal(n)*rate/1_000_000
        remaining -= n
    return dict(estimated_uncached_cny=str(cost), price_snapshot='ADR0108/2026-09-22', hard_billing_cap=False,
        scope='Conservative shared-token reservation, not a bill or current-price guarantee.',
        max_glm_reviews=4, shared_generation_and_review_calls=6)


def prepare(run_id):
    descriptor = CONTRACT.descriptor()
    if any(descriptor[k] != v for k, v in LIMITS.items() if k != 'sdk_retries'):
        raise ValueError('natural_limits_changed')
    factory = CaptureFactory()
    with TemporaryDirectory(prefix='riftcoach-natural-preview-') as directory:
        prepared = build_application(provider_factory=factory, output_root=directory, run_id=run_id)
        compiler = prepared.app._compiler

        class CaptureCompiler:
            def compile(self, *args, **kwargs):
                factory.compiled = compiler.compile(*args, **kwargs)
                return factory.compiled

        prepared.app._compiler = CaptureCompiler()
        try:
            prepared.run()
        except _Captured:
            pass
        if factory.first is None or factory.compiled is None:
            raise ValueError('natural_first_request_not_reached')
    first = factory.first
    raw = request_bytes(first)
    manifest = json.loads((ASSETS/'prompt_programs/recent-form-review/manifest.json').read_bytes())
    # Local source/config identity, including runtime dependencies and retrieval corpus.
    paths = [p for group in ('app', 'scripts', 'skills', 'examples/runtime_profiles/natural_duty_v1', 'data/rag_docs')
             for p in (ROOT/group).rglob('*') if p.suffix in ('.py', '.md', '.json', '.yaml', '.yml', '.toml')]
    paths += [ROOT/'pyproject.toml', *SOURCES.glob('*.json')]
    files = inventory(paths)
    plan = dict(version='natural-duty-development-preparation-v1', run_id=run_id,
        source_scope='frozen_public_ShowMaker_observation_development_not_current_fetch_or_holdout',
        source_projection_time=SOURCE_NOW, sources=SOURCE_SHA,
        typed_request=dict(count=5, queue=420, focus='overall'),
        actual_compiled_task=factory.compiled.execution_request.user_utterance,
        relationship='observed', memory_records=0, preselected_knowledge=False,
        contract=CONTRACT.snapshot().model_dump(mode='json'), program_sha256=manifest['program_sha256'],
        first_request_sha256=sha(raw), first_request_normalization='Only timeout may decrease at real dispatch.',
        component_files=files, component_inventory_sha256=sha(canonical(files)), limits=LIMITS,
        reservation_estimate=cost_envelope(), provider_requests=0, production_admitted=False,
        original_15_qualified=False, semantic_approval=False, execution_authorized=False,
        offline_scope='Actual application to first send; no model response, knowledge selection or paid run.')
    plan['preparation_plan_sha256'] = sha(canonical(plan))
    return first, plan
