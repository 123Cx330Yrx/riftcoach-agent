"""Actual application plumbing with scripted model IO, not live quality."""
from dataclasses import replace
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.golden_role_correction_scope import RoleCorrectionScopeReviewWorkflow as Workflow, RULE, review_policy
from app.evaluation.golden_role_coarse import RoleCoarseReviewWorkflow as OldWorkflow
from app.evaluation.golden_coarse_source_projection import VERSION
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.role_qualification import frozen_cases
from app.product.native_coach_composition import build_correction_scope_coach_application
from app.runtime.coach_contract import CORRECTION_SCOPE_COACH_CONTRACT as CONTRACT, COARSE_ROLE_COACH_CONTRACT
from app.runtime.models import RuntimeTrace
from app.runtime.reviewer_roles import RoleRoutedProvider
from app.runtime.store import RuntimeTraceStore
from tests.test_native_editor_product_budget import offline
from tests.test_reviewer_role_proposal import providers
from tests.test_role_coach_application import run
from tests.test_role_review_notes import request_data


def test_all_inputs_use_exact_tested_policy_and_unmodified_editor():
    from scripts.prepare_correction_scope_diagnostic import variant, RULE as tested_rule
    assert RULE == tested_rule
    for _, source in frozen_cases()[0]:
        inputs = Workflow.build_inputs(source)
        actual = Workflow.make_request(inputs)
        assert actual == variant(inputs)[1]
        prior = compact(dict(score=96, verdict='pass', issues=[], issue_resolutions=[], advisories=[]))
        recheck = Workflow.make_request(inputs, previous_raw=prior, diagnostics={'reason': 'test'})
        old = OldWorkflow.make_request(inputs, previous_raw=prior, diagnostics={'reason': 'test'})
        assert replace(recheck, messages=old.messages) == old
        assert recheck.messages[1:] == old.messages[1:]
        assert recheck.messages[0].content == old.messages[0].content + '\n' + RULE
        assert recheck.messages[0].content == review_policy(prior)
        _, accepted, journal = Workflow.validate_review(prior, inputs)
        assert journal['policy_sha256'] == digest(actual.messages[0].content)
        assert Workflow.make_request(inputs, accepted=accepted) == OldWorkflow.make_request(inputs, accepted=accepted)


def test_old_snapshot_stays_fixed_and_new_trace_cannot_borrow_old_program(monkeypatch):
    from tests import test_role_runtime_trace as fixtures
    assert COARSE_ROLE_COACH_CONTRACT.snapshot().sha256 == 'c40398b96be3c187976b96089a18d7967c20a51cdf84f9a46abd3d6d410a3e59'
    monkeypatch.setattr(fixtures, 'ROLE_COACH_CONTRACT', COARSE_ROLE_COACH_CONTRACT)
    raw = fixtures.role_trace().model_dump(mode='json')
    for key in ('identity', 'policy'):
        raw[key]['coach_contract'] = CONTRACT.snapshot().model_dump()
    with pytest.raises(ValidationError, match='program identity'):
        RuntimeTrace.model_validate(raw)
    monkeypatch.setattr(fixtures, 'ROLE_COACH_CONTRACT', CONTRACT)
    trace = fixtures.role_trace()
    assert RuntimeTrace.model_validate_json(trace.model_dump_json()) == trace


@pytest.fixture
def coarse_script_sources(monkeypatch):
    from tests import test_native_editor_product_budget as fixtures
    def source(data):
        roots = data['source_roots']
        rows = [dict(zip(roots['columns'], row)) for row in roots['roots']]
        return next(r['source_id'] for r in rows if r['key'] == 'derived/computed_evidence')
    monkeypatch.setattr(fixtures, '_computed_source', source)


@pytest.mark.parametrize('recover', [False, True])
def test_application_uses_same_policy_through_tools_edit_fresh_and_bounded_reassessment(tmp_path, coarse_script_sources, recover):
    from app.rag.hybrid import LocalHybridKnowledgeProvider
    from tests.test_native_editor_product_budget import SummaryBuilder

    class Factory:
        def __init__(self):
            self.descriptor = RoleRoutedProvider(*providers(), source_projection=VERSION)
            self.created = {}

        def __call__(self, run_id):
            self.created[run_id] = RoleRoutedProvider(*providers(recover=recover), source_projection=VERSION)
            return self.created[run_id]

    factory = Factory()
    app = build_correction_scope_coach_application(
        summary_builder=SummaryBuilder(factory.descriptor.generator.req.player_summary),
        provider_factory=factory, knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path)
    result = run(app, 'scope_application')
    assert result.publication_status.value == ('rejected' if recover else 'published'), result
    trace = RuntimeTraceStore(tmp_path, 'scope_application').read_trace(result.trace_reference)
    assert trace.identity.coach_contract == trace.policy.coach_contract == CONTRACT.snapshot()
    assert trace.identity.prompt_profile_version == '3.3.0'
    delegate = factory.created['scope_application']
    expected = ['generation', 'generation', 'review', 'review', 'revision'] if recover else [
        'generation', 'generation', 'review', 'revision', 'review']
    assert [r['role'] for r in delegate.attempts] == expected
    assert trace.usage.provider_calls_attempted == 5
    assert any(m.role.value == 'tool' for m in delegate.generator.requests[1].messages)
    reviews = delegate.reviewer.requests
    assert all(r.messages[0].content.endswith('\n' + RULE) for r in reviews)
    assert all(r.messages[0].content.count(RULE) == 1 for r in reviews)
    if recover:
        assert request_data(reviews[1])['previous_review']['score'] == '70'
        assert reviews[1].messages[0].content == review_policy('prior')
        assert result.output.report is None  # Recovery consumes the shared fifth-call allowance.
    else:
        assert not {'previous_review', 'previous_issues', 'accepted_review'} & request_data(reviews[-1]).keys()
        assert request_data(delegate.generator.requests[-1])['accepted_review']['issues']


def test_explicit_natural_development_preview_uses_new_profile(tmp_path, monkeypatch):
    from copy import deepcopy
    from types import SimpleNamespace
    from scripts import native_coach_preparation as common, run_role_coach_development as runner
    from tests.test_role_coach_development import arguments
    generator, _ = providers()
    monkeypatch.setattr(common, 'load_frozen_sources', lambda: (deepcopy(generator.req.player_summary),
        SimpleNamespace(data_dragon=None, official_patch=None, meta_evidence=())))
    args = arguments(tmp_path, profile='correction-scope')
    first = runner.run(args)
    assert first == runner.run(args)
    assert first['candidate_identity']['contract'] == CONTRACT.snapshot().model_dump()
    assert first['shared_budget']['max_calls'] == 5
    assert first['provider_requests'] == 0 and not tmp_path.joinpath('runs').exists()
    with pytest.raises(ValueError, match='profile_unsupported'):
        runner.run(arguments(tmp_path, profile='typo'))


@pytest.mark.parametrize('scenario', ['normal', 'recover', 'failed'])
def test_natural_entry_receipts_follow_selected_contract(tmp_path, monkeypatch, coarse_script_sources, scenario):
    from copy import deepcopy
    from types import SimpleNamespace
    from app.providers.config import ZhipuSettings
    from scripts import native_coach_preparation as common, run_role_coach_development as runner
    from tests.test_role_coach_development import arguments, scripted_child
    generator, _ = providers()
    monkeypatch.setattr(common, 'load_frozen_sources', lambda: (deepcopy(generator.req.player_summary),
        SimpleNamespace(data_dragon=None, official_patch=None, meta_evidence=())))
    monkeypatch.setattr(runner, 'verify_public_ci', lambda _: 'a' * 40)
    monkeypatch.setattr(runner, 'require_unchanged_checkout', lambda _: None)
    monkeypatch.setattr(runner, 'load_role_settings', lambda _: tuple(
        ZhipuSettings(api_key='test-secret', base_url='https://open.bigmodel.cn/api/paas/v4', model=model)
        for model in ('glm-5.3-flash', 'glm-5.3')))
    sent = scripted_child(monkeypatch, scenario=scenario)
    args = arguments(tmp_path, profile='correction-scope')
    preview = runner.run(args)
    args.execute, args.approval_plan_sha = True, preview['preparation_plan_sha256']
    result = runner.run(args)
    assert result['status'] == ('published' if scenario == 'normal' else 'rejected'), result
    assert result['reserved_calls'] == len(sent) <= 5
    assert result['unknown_usage_calls'] == (1 if scenario == 'failed' else 0)
    assert result['first_request_matched']
    for request, model, _ in sent:
        if model == 'glm-5.3':
            assert request.messages[0].content.endswith('\n' + RULE)
    assert not result['original_15_qualified'] and not result['actual_product_task_qualified']
