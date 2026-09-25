"""Opt-in identity and actual runtime composition; no live quality claims."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation import coarse_role_qualification as qualification
from app.evaluation import golden_coarse_source_projection as projection
from app.evaluation.golden_role_coarse import RoleCoarseReviewWorkflow as Workflow
from app.evaluation.role_qualification import frozen_cases
from app.runtime.coach_contract import COARSE_ROLE_COACH_CONTRACT as CONTRACT, ROLE_COACH_CONTRACT
from app.runtime.reviewer_roles import RoleRoutedProvider, role_for_request
from app.runtime.models import RuntimeTrace
from tests.test_reviewer_role_proposal import providers


def test_original_15_have_independent_source_bound_identity():
    plan, requests = qualification.prepare_qualification()
    assert len(plan['cases']) == len(requests) == 15
    assert plan['identity']['contract'] == CONTRACT.snapshot().model_dump()
    assert not plan['review_controls_qualified'] and not plan['production_admitted']
    assert ROLE_COACH_CONTRACT.snapshot().sha256 == 'ffc45471455a546a2b75a35ee902e5f5405ebd01b9bfbe3606fac34649fcea4a'
    for row, (frozen, source) in zip(plan['cases'], frozen_cases()[0], strict=True):
        assert all(row[k] == v for k, v in frozen.items())
        inputs = Workflow.build_inputs(source)
        request = Workflow.make_request(inputs)
        assert request.tools[0].input_schema == projection.response_schema(inputs)
        assert row['request_sha256'] == hashlib.sha256(requests[row['key']]).hexdigest()
        assert row['source_catalog_sha256'] == projection.source_catalog(inputs)['catalog_sha256']


def test_projection_routes_are_bidirectionally_isolated():
    source = frozen_cases()[0][0][1]
    request = Workflow.make_request(Workflow.build_inputs(source))
    from app.evaluation.golden_explicit_source_projection import VERSION as old_projection
    from app.evaluation.golden_role_clarity import RoleClarityReviewWorkflow
    old = RoleClarityReviewWorkflow.make_request(Workflow.build_inputs(source))
    assert role_for_request(old) == role_for_request(request, source_projection=projection.VERSION) == 'review'
    with pytest.raises(ValueError, match='projection'):
        ROLE_COACH_CONTRACT.request_identity(request)
    with pytest.raises(ValueError, match='projection'):
        CONTRACT.request_identity(old)
    with pytest.raises(ValueError, match='projection'):
        CONTRACT.require_provider(RoleRoutedProvider(*providers(), source_projection=old_projection))
    with pytest.raises(ValueError, match='projection'):
        ROLE_COACH_CONTRACT.require_provider(RoleRoutedProvider(*providers(), source_projection=projection.VERSION))
    for requested_projection, issued in ((old_projection, request), (projection.VERSION, old)):
        router = RoleRoutedProvider(*providers(), source_projection=requested_projection)
        with pytest.raises(ValueError, match='projection'):
            router.chat(issued)
        assert router.attempts == []
        spoofed = replace(issued, metadata={**issued.metadata, 'source_projection':requested_projection})
        with pytest.raises(ValueError, match='projection_payload'):
            role_for_request(spoofed, source_projection=requested_projection)


def test_new_trace_requires_exact_snapshot(monkeypatch):
    from tests import test_role_runtime_trace as fixtures
    old = fixtures.role_trace().model_dump(mode='json')
    for key in ('identity', 'policy'):
        old[key]['coach_contract'] = CONTRACT.snapshot().model_dump()
    with pytest.raises(ValidationError, match='program identity'):
        RuntimeTrace.model_validate(old)
    monkeypatch.setattr(fixtures, 'ROLE_COACH_CONTRACT', CONTRACT)
    trace = fixtures.role_trace()
    assert RuntimeTrace.model_validate_json(trace.model_dump_json()) == trace
    raw = trace.model_dump(mode='json')
    for key in ('identity', 'policy'):
        raw[key]['coach_contract']['sha256'] = '0' * 64
    with pytest.raises(ValidationError, match='trusted contract'):
        RuntimeTrace.model_validate(raw)


def test_actual_coarse_application_generation_tools_review_publication(tmp_path):
    from app.product.native_coach_composition import build_coarse_role_coach_application
    from app.rag.hybrid import LocalHybridKnowledgeProvider
    from app.runtime.store import RuntimeTraceStore
    from tests.test_native_editor_product_budget import SummaryBuilder
    from tests.test_role_coach_application import run
    from tests.test_role_review_notes import tool_response
    from app.evaluation.golden_integrated_runtime import Exchange
    from app.evaluation.golden_stream_bridge import validate_request, REVIEW_MODEL_TRANSPORT_ID

    class Factory:
        def __init__(self):
            self.descriptor = RoleRoutedProvider(*providers(), source_projection=projection.VERSION)
            self.created = {}

        def __call__(self, run_id):
            generator, reviewer = providers()
            def review(request):
                assert request.metadata['source_projection'] == projection.VERSION
                response = tool_response(dict(score=96, verdict='pass', issues=[], issue_resolutions=[], advisories=[]))
                raw = validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)
                reviewer.last_exchange = Exchange(request, response, hashlib.sha256(raw).hexdigest())
                return response
            reviewer.chat = review
            self.created[run_id] = RoleRoutedProvider(generator, reviewer, source_projection=projection.VERSION)
            return self.created[run_id]

    factory = Factory()
    app = build_coarse_role_coach_application(
        summary_builder=SummaryBuilder(factory.descriptor.generator.req.player_summary),
        provider_factory=factory,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path)
    result = run(app, 'coarse_application')
    assert result.publication_status.value == 'published', result
    trace = RuntimeTraceStore(tmp_path, 'coarse_application').read_trace(result.trace_reference)
    assert trace.identity.coach_contract == trace.policy.coach_contract == CONTRACT.snapshot()
    assert [a['role'] for a in factory.created['coarse_application'].attempts] == ['generation', 'generation', 'review']
