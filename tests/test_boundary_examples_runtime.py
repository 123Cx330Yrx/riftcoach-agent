"""Real application wiring and version isolation with scripted network IO."""
from dataclasses import replace
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.golden_role_boundary_examples import RoleBoundaryExamplesReviewWorkflow as Workflow, EXAMPLES, review_policy
from app.evaluation.golden_role_correction_scope import RoleCorrectionScopeReviewWorkflow as Baseline
from app.evaluation.golden_coarse_source_projection import VERSION
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.role_qualification import frozen_cases
from app.product.native_coach_composition import build_boundary_examples_coach_application
from app.runtime.coach_contract import BOUNDARY_EXAMPLES_COACH_CONTRACT as CONTRACT, CORRECTION_SCOPE_COACH_CONTRACT
from app.runtime.models import RuntimeTrace
from app.runtime.reviewer_roles import RoleRoutedProvider
from app.runtime.store import RuntimeTraceStore
from tests.test_correction_scope_runtime import coarse_script_sources
from tests.test_native_editor_product_budget import offline, SummaryBuilder
from tests.test_reviewer_role_proposal import providers
from tests.test_role_coach_application import run
from tests.test_role_review_notes import request_data


def test_all15_and_all_phases_match_tested_diagnostic():
    from scripts.review_boundary_examples import request_for, EXAMPLES as tested
    assert EXAMPLES == tested
    prior = compact(dict(score=96, verdict='pass', issues=[], issue_resolutions=[], advisories=[]))
    for _, source in frozen_cases()[0]:
        inputs = Workflow.build_inputs(source)
        for kwargs in ({}, {'previous_raw': prior, 'diagnostics': {'reason': 'offline'}}):
            actual = Workflow.make_request(inputs, **kwargs)
            assert actual == request_for(inputs, **kwargs)
            assert actual.messages[0].content == review_policy(kwargs.get('previous_raw'))
        _, accepted, journal = Workflow.validate_review(prior, inputs)
        assert journal['policy_sha256'] == digest(Workflow.make_request(inputs).messages[0].content)
        assert Workflow.make_request(inputs, accepted=accepted) == Baseline.make_request(inputs, accepted=accepted)


def test_new_trace_rejects_borrowed_old_program(monkeypatch):
    from tests import test_role_runtime_trace as fixtures
    monkeypatch.setattr(fixtures, 'ROLE_COACH_CONTRACT', CORRECTION_SCOPE_COACH_CONTRACT)
    raw = fixtures.role_trace().model_dump(mode='json')
    for key in ('identity', 'policy'):
        raw[key]['coach_contract'] = CONTRACT.snapshot().model_dump()
    with pytest.raises(ValidationError, match='program identity'):
        RuntimeTrace.model_validate(raw)
    monkeypatch.setattr(fixtures, 'ROLE_COACH_CONTRACT', CONTRACT)
    trace = fixtures.role_trace()
    assert RuntimeTrace.model_validate_json(trace.model_dump_json()) == trace


@pytest.mark.parametrize('recover,ceiling', [(False,False),(False,True),(True,False)])
def test_actual_application_same_policy_shared_budget(tmp_path, coarse_script_sources, recover, ceiling):
    from app.rag.hybrid import LocalHybridKnowledgeProvider
    class Factory:
        def __init__(self):
            self.descriptor = RoleRoutedProvider(*providers(), source_projection=VERSION)
            self.created = {}
        def __call__(self, run_id):
            self.created[run_id] = RoleRoutedProvider(*providers(recover=recover, charge_ceiling=ceiling), source_projection=VERSION)
            return self.created[run_id]
    factory = Factory()
    app = build_boundary_examples_coach_application(
        summary_builder=SummaryBuilder(factory.descriptor.generator.req.player_summary), provider_factory=factory,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')), runs_root=tmp_path)
    result = run(app, 'boundary_application')
    assert result.publication_status.value == ('rejected' if recover else 'published'), result
    trace = RuntimeTraceStore(tmp_path, 'boundary_application').read_trace(result.trace_reference)
    assert trace.identity.coach_contract == trace.policy.coach_contract == CONTRACT.snapshot()
    assert trace.identity.prompt_profile_version == '3.4.0'
    delegate = factory.created['boundary_application']
    assert [r['role'] for r in delegate.attempts] == (['generation','generation','review','review','revision'] if recover else ['generation','generation','review','revision','review'])
    assert trace.usage.provider_calls_attempted == 5
    assert any(m.role.value == 'tool' for m in delegate.generator.requests[1].messages)
    assert all(r.messages[0].content.endswith('\n'+EXAMPLES) for r in delegate.reviewer.requests)
    assert all(EXAMPLES not in r.messages[0].content for r in delegate.generator.requests)
    if recover:
        assert request_data(delegate.reviewer.requests[1])['previous_review']['score'] == '70'
        assert result.output.report is None
    else:
        assert not {'previous_review','previous_issues','accepted_review'} & request_data(delegate.reviewer.requests[-1]).keys()
        assert request_data(delegate.generator.requests[-1])['accepted_review']['issues']


def test_application_rejects_editor_policy_echo_without_fresh_call(
        tmp_path, coarse_script_sources, monkeypatch):
    from app.rag.hybrid import LocalHybridKnowledgeProvider
    generator, reviewer = providers()
    original_chat = generator.chat
    captured = []

    def echoing_editor(request):
        response = original_chat(request)
        if request.metadata.get('harness_step') == 'revise':
            response = replace(response,
                content=request.messages[0].content[:420] + '\n\n' + response.content)
            generator.last_exchange = replace(generator.last_exchange, response=response)
            captured.append(response)
        return response

    monkeypatch.setattr(generator, 'chat', echoing_editor)
    delegate = RoleRoutedProvider(generator, reviewer, source_projection=VERSION)

    class Factory:
        descriptor = RoleRoutedProvider(*providers(), source_projection=VERSION)

        def __call__(self, run_id):
            return delegate

    app = build_boundary_examples_coach_application(
        summary_builder=SummaryBuilder(generator.req.player_summary), provider_factory=Factory(),
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path)
    result = run(app, 'boundary_echo_rejected')
    assert result.publication_status.value == 'rejected'
    assert result.output.report is None
    assert len(captured) == 1
    assert [row['role'] for row in delegate.attempts] == [
        'generation', 'generation', 'review', 'revision']
    assert delegate.attempts[-1]['status'] == 'completed'
    assert len(reviewer.requests) == 1


@pytest.mark.parametrize('scenario', ['normal','recover','failed'])
def test_natural_entry_routes_and_receipts(tmp_path, monkeypatch, coarse_script_sources, scenario):
    from copy import deepcopy
    from types import SimpleNamespace
    from app.providers.config import ZhipuSettings
    from scripts import native_coach_preparation as common, run_role_coach_development as runner
    from tests.test_role_coach_development import arguments, scripted_child
    generator, _ = providers()
    monkeypatch.setattr(common, 'load_frozen_sources', lambda: (deepcopy(generator.req.player_summary), SimpleNamespace(data_dragon=None, official_patch=None, meta_evidence=())))
    monkeypatch.setattr(runner, 'verify_public_ci', lambda _: 'a'*40)
    monkeypatch.setattr(runner, 'require_unchanged_checkout', lambda _: None)
    monkeypatch.setattr(runner, 'load_role_settings', lambda _: tuple(ZhipuSettings(api_key='test-secret',base_url='https://open.bigmodel.cn/api/paas/v4',model=m) for m in ('glm-5.3-flash','glm-5.3')))
    sent = scripted_child(monkeypatch, scenario=scenario)
    args = arguments(tmp_path, profile='boundary-examples')
    preview = runner.run(args)
    assert preview['candidate_identity']['contract'] == CONTRACT.snapshot().model_dump()
    args.execute, args.approval_plan_sha = True, preview['preparation_plan_sha256']
    result = runner.run(args)
    assert result['status'] == ('published' if scenario == 'normal' else 'rejected'), result
    assert result['reserved_calls'] == len(sent) <= 5
    assert result['unknown_usage_calls'] == (1 if scenario == 'failed' else 0)
    assert result['first_request_matched']
    for request, model, _ in sent:
        if model == 'glm-5.3': assert request.messages[0].content.endswith('\n'+EXAMPLES)
    assert not result['original_15_qualified'] and not result['actual_product_task_qualified']
