import json
from copy import deepcopy

import pytest

from scripts import run_full15_resumption_candidate as runner
from scripts.diagnose_role_context import canonical_sha


def test_full15_runner_prepares_all_cases_without_provider_io():
    plan = runner.prepare(root_thread_id='root', independent_thread_id='independent')
    assert len(plan['cells']) == 15
    assert plan['sequence'] == [cell['key'] for cell in plan['cells']]
    assert plan['budget']['role_calls'] == {'glm-5.3': 30, 'glm-5.3-flash': 15}
    assert plan['budget']['max_calls'] == 45
    assert plan['execution_authorized'] is False
    assert plan['paid_plan_frozen'] is False
    assert plan['new_qualification'] == 0
    assert canonical_sha(plan) == canonical_sha(json.loads(json.dumps(plan)))


def test_runner_controls_keep_candidate_baseline_byte_contract():
    rows, variants = runner.controls()
    assert len(rows) == len(variants) == 15
    for row, (_, _, _, request) in zip(rows, variants):
        assert row['candidate_request_sha256']
        assert runner.candidate.request_identity(request) == ('zhipu', 'glm-5.3')


def test_focused_plan_binds_fixed_scope_exact_budget_and_separate_run():
    plan = runner.prepare(root_thread_id='root', independent_thread_id='independent',
                          selection='diagnostic10')
    assert plan['sequence'] == list(runner.DIAGNOSTIC)
    assert [cell['key'] for cell in plan['cells']] == plan['sequence']
    assert plan['run_id'] != runner.RUN_ID
    assert plan['budget']['role_calls'] == {'glm-5.3': 19, 'glm-5.3-flash': 9}
    assert plan['budget']['max_calls'] == 28
    assert plan['budget']['max_tokens'] == 2709504
    assert plan['budget']['max_active_seconds'] == 8400
    assert plan['budget']['estimated_uncached_cny'] == '28.4471296'
    assert not plan['execution_authorized'] and not plan['original15_qualified']
    for row, (_, _, _, request) in zip(plan['cells'], runner.selected_controls('diagnostic10')[1], strict=True):
        raw = runner.validate_request(request, transport_id=runner.REVIEW_MODEL_TRANSPORT_ID)
        assert row['candidate_request_sha256'] == runner._bytes_sha(raw)
    with pytest.raises(ValueError, match='selection_unknown'):
        runner.prepare(root_thread_id='root', independent_thread_id='independent', selection='arbitrary')


@pytest.mark.parametrize('change', ['order', 'budget', 'run_id'])
def test_changed_scope_or_budget_is_rejected_before_factory(tmp_path, monkeypatch, change):
    plan = runner.prepare(root_thread_id='root', independent_thread_id='independent',
                          selection='diagnostic10')
    changed = deepcopy(plan)
    if change == 'order':
        changed['sequence'].reverse()
    elif change == 'budget':
        changed['budget']['max_calls'] += 1
    else:
        changed['run_id'] = runner.RUN_ID
    monkeypatch.setattr(runner, 'require_execution_event_source', lambda *args: None)
    def forbidden_factory(*args):
        raise AssertionError('Changed plan reached a provider factory')
    with pytest.raises(ValueError, match='controls_changed'):
        runner.observe(forbidden_factory, tmp_path, changed, event_source=None, adjudicate=None)
    assert not list(tmp_path.iterdir())
