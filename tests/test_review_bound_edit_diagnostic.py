"""Three-stage runner with explicitly synthetic Provider and host observations."""
from copy import deepcopy
from functools import lru_cache
import json
from types import SimpleNamespace

import pytest

from app.evaluation import review_bound_editor as editor
from scripts import run_coarse_edit_diagnostic as base
from scripts import run_review_bound_edit_diagnostic as runner
from tests import test_coarse_edit_diagnostic as old


@lru_cache
def prepared():
    return runner.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent')


def factory(monkeypatch, fault):
    original = old.ToolCall
    def call(**kwargs):
        if kwargs['name'] == 'submit_source_edits':
            kwargs['name'] = editor.TOOL
            kwargs['arguments'] = deepcopy(kwargs['arguments'])
            for op in kwargs['arguments']['edits']:
                op.pop('source_ids', None)
                if fault == 'missing_reason': op.pop('reason')
        return original(**kwargs)
    # This adapts only the test's host-authored synthetic operations, never any
    # historical model response, production module or runtime adapter.
    monkeypatch.setattr(old, 'ToolCall', call)
    return old.scripted(monkeypatch, fault)


def test_plan_accounts_for_closed_attempts_and_preserves_complete_context():
    plan = prepared()
    assert plan['adapter'] == editor.VERSION and plan['budget']['max_calls'] == 3
    assert plan['budget']['estimated_uncached_cny'] == '1.7154048'
    assert plan['cumulative_with_closed'] == dict(max_calls=5, max_tokens=312989,
        max_active_seconds=936, estimated_uncached_cny='1.7353548')
    assert not plan['execution_authorized'] and not plan['original15_qualified']
    for row, inputs, accepted, request in base.controls(revision_adapter=editor):
        assert request.messages[1:] == base.Current.make_request(inputs, accepted=accepted).messages[1:]


@pytest.mark.parametrize('fault,calls', [(None,3),('missing_reason',1),('policy',1),
    ('host_reject',1),('host_unavailable',1),('missing_report',1),
    ('fresh_failed',2),('keep_changed',3),('transport',1),('budget',0)])
def test_three_stage_control_stops_at_first_failure_and_preserves_actual_receipts(tmp_path,monkeypatch,fault,calls):
    plan = deepcopy(prepared())
    if fault == 'budget': plan['budget']['max_tokens'] = 1
    host = old.Host(plan, fault)
    result = base.observe(factory(monkeypatch, fault), tmp_path, plan, event_source=host,
                          adjudicate=host.adjudicate, revision_adapter=editor)
    assert result['calls'] == calls, result
    assert result['diagnostic_accepted'] == (fault is None), result
    assert not result['product_admitted'] and not result['original15_qualified']
    assert json.loads((tmp_path/'result.json').read_bytes()) == json.loads(json.dumps(result))
    if fault == 'transport': assert result['unknown_reserved_tokens'] > 0
    else: assert result['unknown_reserved_tokens'] == 0
    if calls < 2: assert not (tmp_path/'conditional-fresh').exists()
    if fault is None:
        assert [x['name'] for x in result['stages']] == ['necessary-edit','conditional-fresh','correct-keep']
        stage=json.loads((tmp_path/'necessary-edit/stage.json').read_bytes())
        context=stage['journal']['review_source_context']
        assert not context['proves_edit_support'] and not context['editor_selected_sources']
        assert result['timing']['completed_host_waits'] == 3


def test_adapter_identity_mismatch_is_rejected_before_io(tmp_path):
    plan = deepcopy(prepared()); plan['adapter']='another'
    def forbidden(*args): pytest.fail('bad plan touched Provider')
    with pytest.raises(ValueError, match='adapter_plan'):
        base.observe(forbidden,tmp_path,plan,event_source=old.Host(plan,None),revision_adapter=editor)


def test_frozen_plan_ci_and_existing_directory_precede_credentials(tmp_path,monkeypatch):
    plan=prepared()
    monkeypatch.setattr(runner,'prepare',lambda **kwargs: plan)
    monkeypatch.setattr(base,'ROOT',tmp_path)
    frozen=tmp_path/'preparation.json'; frozen.write_text(json.dumps(plan),encoding='utf-8')
    args=SimpleNamespace(root_thread_id='synthetic-root',independent_thread_id='synthetic-independent',
        execute=True,preparation=frozen,env_file=tmp_path/'absent.env',codex_executable=tmp_path/'absent.exe',
        plan_sha=base.canonical_sha(plan),ci_run='synthetic')
    def forbidden(*args): pytest.fail('credentials read before valid execution prerequisites')
    monkeypatch.setattr(base,'load_role_settings',forbidden)
    def bad_ci(*args): raise ValueError('synthetic_ci_failure')
    monkeypatch.setattr(base,'verify_public_ci',bad_ci)
    with pytest.raises(ValueError,match='synthetic_ci_failure'): runner.run(args)
    frozen.write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='preparation_required'): runner.run(args)
    (tmp_path/'data/runs/model_comparison'/runner.EXPERIMENT).mkdir(parents=True)
    with pytest.raises(ValueError,match='closed_or_exists'): runner.run(args)


def test_prior_seal_tampering_is_not_ignored(monkeypatch):
    monkeypatch.setattr(base,'sha',lambda _: '0'*64)
    with pytest.raises(ValueError,match='prior_seal'):
        runner.prepare(root_thread_id='synthetic-root',independent_thread_id='synthetic-independent')
