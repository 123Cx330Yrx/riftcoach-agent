"""Continuation accounting must charge actual receipts, including the parent."""
from decimal import Decimal
import json
from types import SimpleNamespace

import pytest

from scripts.run_boundary_examples_v2_continuation import known_cost
from scripts import run_boundary_examples_v2_continuation as entry


def test_unreadable_current_host_stops_continuation_before_reservation_or_paid_io(tmp_path, monkeypatch):
    plan = dict(experiment=entry.EXPERIMENT, root_thread_id='root', review_principals={
        'primary': {'principal_id':'root'}, 'independent': {'principal_id':'child'}})
    preparation = tmp_path/'prepared.json'
    preparation.write_text(json.dumps(plan), encoding='utf-8')
    args = SimpleNamespace(experiment=entry.EXPERIMENT, prior_run=tmp_path/'parent',
        prior_export=tmp_path/'seal', prior_sha=entry.PARENT_SEAL, root_thread_id='root',
        independent_thread_id='child', max_host_seconds=86400, execute=True,
        preparation=preparation, env_file=tmp_path/'unused-env', ci_run='unused-ci',
        codex_executable=tmp_path/'unused.exe', plan_sha=entry.runner.canonical_sha(plan))
    class Client:
        def __init__(self, *_): pass
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def request(self, method, params):
            return dict(thread=dict(id=params['threadId'], parentThreadId='root',
                source={'subAgent':{'thread_spawn':{'parent_thread_id':'root'}}}))
        def check_latest_input(self, thread):
            assert thread['id'] == 'child'
            raise ValueError('codex_review_host_rollout_dispatch_encrypted')
    monkeypatch.setattr(entry, 'RUN_ROOT', tmp_path/'runs')
    monkeypatch.setattr(entry, 'prepare', lambda **kw: (plan, {}))
    monkeypatch.setattr(entry, 'CodexReadOnlyClient', Client)
    monkeypatch.setattr(entry.audit, 'inspect_runs', lambda *a, **kw: pytest.fail('audit before host readiness'))
    monkeypatch.setattr(entry.runner, 'execute_prepared', lambda *a, **kw: pytest.fail('reservation or paid IO'))
    with pytest.raises(ValueError, match='dispatch_encrypted'):
        entry.run(args)
    assert not (tmp_path/'runs').exists()


def test_actual_parent_usage_is_not_silently_free():
    summary = {'calls': [{'provider': 'zhipu', 'model': 'glm-5.3',
        'usage': {'input_tokens': 12234, 'output_tokens': 3341}}]}
    assert known_cost([summary, {'calls': []}]) == Decimal('0.19142')
    assert known_cost([summary]) + Decimal('35.737600') == Decimal('35.929020')


def test_unknown_usage_cannot_be_priced_as_zero():
    with pytest.raises(ValueError, match='unknown_cost'):
        known_cost([{'calls': [{'usage': None}]}])


@pytest.mark.parametrize('name', ['another-continuation', '../old-run'])
def test_renaming_cannot_spend_again(name, monkeypatch):
    monkeypatch.setattr(entry, 'read_parent', lambda *a, **kw: pytest.fail('read before target check'))
    with pytest.raises(ValueError, match='target_invalid'):
        entry.prepare(prior_run='parent', prior_export='seal', prior_sha=entry.PARENT_SEAL,
            root_thread_id='root', independent_thread_id='child', experiment=name)


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    parent, export = tmp_path/'parent', tmp_path/'seal.json'
    budget = dict(max_calls=34, max_tokens=3290112, max_seconds=10200,
        estimated_uncached_cny='35.737600')
    charge = dict(max_calls=1, max_tokens=15575, max_seconds=72.72)
    accounting = dict(estimated_uncached_cny='0.19142')
    prior = dict(cases=[{'key':'claim-scope:1'}, {'key':'remaining'}],
        case_budgets=[{}, {k:budget[k] for k in charge}], identity={}, review_principals={},
        root_thread_id='root', host_review_timing={'max_host_seconds':86400},
        batch_budget=dict(max_calls=35, max_tokens=3386880, max_seconds=10500))
    saved = dict(plan_sha256='a'*64, preparation_plan=prior)
    monkeypatch.setattr(entry, 'read_parent', lambda *a, **kw:
        (parent, export, saved, ['claim-scope:1'], charge, accounting))
    monkeypatch.setattr(entry, 'validate_adopted_timing', lambda *a, **kw: {'host_elapsed_seconds':474.546})
    frozen_budget = budget.copy()
    monkeypatch.setattr(entry.runner, 'prepare_fresh', lambda **kw: ({'batch_budget': frozen_budget}, {}))
    plan = dict(experiment=entry.EXPERIMENT, identity={}, review_principals={}, root_thread_id='root',
        cases=prior['cases'][1:], case_budgets=prior['case_budgets'][1:], batch_budget=budget,
        prior_interrupted_batch=dict(run_directory='parent',closed_export='seal.json',
            closed_export_sha256=entry.PARENT_SEAL,plan_sha256='a'*64,
            accepted_prefix_keys=['claim-scope:1'],charged_budget=charge.copy(),accounting=accounting.copy()),
        cumulative_reserved_budget=dict(max_calls=35,max_tokens=3305687,max_seconds=10272.72),
        cumulative_estimated_uncached_cny='35.929020',host_review_timing={'max_host_seconds':86400},
        continuation_host_accounting=dict(scope='per_execution_process',parent_completed_wait_seconds=474.546,
            parent_unfinished_wait_seconds=None,cumulative_host_seconds=None,child_wait_limit_seconds=86400))
    return plan, dict(root=tmp_path,runs=[parent,tmp_path/'child'],exports=[(export,entry.PARENT_SEAL)]), parent


def test_consumption_rebuilds_parent_charge(ledger):
    plan, kwargs, parent = ledger
    assert entry.validate_continuation_ledger(plan, **kwargs) == parent


@pytest.mark.parametrize('fault', ['parent_missing','parent_charge','total','child_budget','cost','paired_cost','host_unknown','rename'])
def test_consumption_rejects_false_cumulative_accounting(ledger, fault):
    plan, kwargs, parent = ledger
    if fault == 'parent_missing': kwargs['runs'].remove(parent)
    elif fault == 'parent_charge': plan['prior_interrupted_batch']['charged_budget']['max_calls'] = 0
    elif fault == 'total': plan['cumulative_reserved_budget']['max_tokens'] = 3290112
    elif fault == 'child_budget': plan['batch_budget']['max_calls'] = 35
    elif fault == 'cost': plan['cumulative_estimated_uncached_cny'] = '35.737600'
    elif fault == 'paired_cost':
        plan['batch_budget']['estimated_uncached_cny'] = '0'
        plan['cumulative_estimated_uncached_cny'] = '0.19142'
    elif fault == 'host_unknown': plan['continuation_host_accounting']['parent_unfinished_wait_seconds'] = 0
    else: plan['experiment'] = 'another-continuation'
    with pytest.raises(ValueError, match='boundary_v2_continuation_'):
        entry.validate_continuation_ledger(plan, **kwargs)
