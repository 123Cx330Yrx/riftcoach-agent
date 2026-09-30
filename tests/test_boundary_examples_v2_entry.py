"""The v2 entry preserves controls and fails before paid IO on stale identity."""
import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from scripts import run_boundary_examples_v2 as entry
from scripts.review_independence_contract import MODE_V2


def arguments(tmp_path, **changes):
    values = dict(root_thread_id='offline-root', independent_thread_id='offline-child',
        experiment='offline-v2', max_host_seconds=86400, execute=False, output=None,
        preparation=tmp_path/'preparation.json', plan_sha=None, env_file=None, ci_run=None,
        codex_executable=None)
    values.update(changes)
    return NS(**values)

def freeze(args):
    plan, requests = entry.prepare(root_thread_id=args.root_thread_id,
        independent_thread_id=args.independent_thread_id, experiment=args.experiment,
        max_host_seconds=args.max_host_seconds)
    args.preparation.write_text(json.dumps(plan), encoding='utf-8')
    args.plan_sha = entry.runner.canonical_sha(plan)
    return plan, requests


def test_preview_freezes_all15_exact_requests_without_host_or_provider(tmp_path, monkeypatch):
    args = arguments(tmp_path, output=tmp_path/'preview.json')
    monkeypatch.setattr(entry, 'RUN_ROOT', tmp_path/'runs')
    monkeypatch.setattr(entry, 'CodexReadOnlyClient', lambda *_: pytest.fail('host IO during preview'))
    monkeypatch.setattr(entry.runner, 'load_role_settings', lambda *_: pytest.fail('credentials during preview'))
    result = entry.run(args)
    plan = json.loads(args.output.read_bytes())
    reference, requests = entry.runner.prepare_fresh(experiment=args.experiment)
    assert result['cases'] == 15 and result['provider_requests'] == 0
    assert not result['execution_enabled'] and not (tmp_path/'runs').exists()
    assert plan['cases'] == reference['cases']
    assert plan['identity'] == reference['identity']
    assert plan['batch_budget'] == reference['batch_budget']
    assert plan['batch_budget']['max_calls'] == 35
    assert plan['host_review_submission_mode'] == MODE_V2
    assert plan['host_review_timing']['adopted'] is True
    assert plan['host_review_timing']['process_restart_allowed'] is False
    assert plan['inherited_completed_cases'] == plan['inherited_provider_calls'] == 0
    assert plan['offline_initial_injections'] == plan['sdk_retries'] == 0
    for row in plan['cases']:
        assert hashlib.sha256(requests[row['key']]).hexdigest() == row['request_sha256']
    for path, sha in plan['source_sha256'].items():
        assert sha == entry.digest((entry.runner.ROOT/path).read_text(encoding='utf-8'))


@pytest.mark.parametrize('fault', ['sha', 'preparation', 'ci', 'env', 'executable', 'principal'])
def test_stale_or_missing_binding_stops_before_host_and_paid_io(tmp_path, monkeypatch, fault):
    args = arguments(tmp_path, execute=True, env_file=tmp_path/'env', ci_run='ci',
        codex_executable=tmp_path/'codex.exe')
    freeze(args)
    if fault == 'sha':
        args.plan_sha = '0'*64
    elif fault == 'preparation':
        data = json.loads(args.preparation.read_bytes())
        data['batch_budget']['max_calls'] += 1
        args.preparation.write_text(json.dumps(data))
    elif fault == 'principal':
        args.independent_thread_id = 'different-child'
    else:
        setattr(args, {'ci':'ci_run', 'env':'env_file', 'executable':'codex_executable'}[fault], None)
    monkeypatch.setattr(entry, 'RUN_ROOT', tmp_path/'runs')
    monkeypatch.setattr(entry, 'CodexReadOnlyClient', lambda *_: pytest.fail('host before binding'))
    monkeypatch.setattr(entry.runner, 'execute_prepared', lambda *a, **kw: pytest.fail('execution before binding'))
    with pytest.raises(ValueError, match='frozen_preparation_required'):
        entry.run(args)
    assert not (tmp_path/'runs').exists()


@pytest.mark.parametrize('execute', [False, True])
def test_existing_run_cannot_be_reopened(tmp_path, monkeypatch, execute):
    args = arguments(tmp_path, execute=execute)
    monkeypatch.setattr(entry, 'RUN_ROOT', tmp_path)
    (tmp_path/args.experiment).mkdir()
    with pytest.raises(ValueError, match='run_already_exists'):
        entry.run(args)


@pytest.mark.parametrize('experiment', ['../old-run', 'C:/old-run', '', 'a/b'])
def test_run_name_cannot_escape_namespace(experiment):
    with pytest.raises(ValueError, match='experiment_invalid'):
        entry.prepare(root_thread_id='root', independent_thread_id='child', experiment=experiment)


def test_execute_keeps_native_source_alive_and_passes_adopted_clock(tmp_path, monkeypatch):
    args = arguments(tmp_path, execute=True, env_file=tmp_path/'env', ci_run='ci',
        codex_executable=tmp_path/'codex.exe')
    plan, requests = freeze(args)
    seen = []
    class Client:
        def __init__(self, executable):
            assert executable == args.codex_executable
        def __enter__(self):
            seen.append('open')
            return self
        def __exit__(self, *_):
            seen.append('closed')
        def request(self, method, params):
            assert method == 'thread/read' and not params['includeTurns']
            identity = params['threadId']
            return {'thread':dict(id=identity, parentThreadId=args.root_thread_id,
                source={'subAgent':{'thread_spawn':{'parent_thread_id':args.root_thread_id}}})}
    def execute(actual_args, actual_plan, actual_requests, **kwargs):
        assert seen == ['open']
        assert actual_args is args and actual_plan == plan and actual_requests == requests
        assert kwargs['host_timing'] == plan['host_review_timing']
        assert kwargs['preparation'] == args.preparation
        assert isinstance(kwargs['event_source'], entry.CodexHostReviewEventSource)
        assert kwargs['event_source'].independent == args.independent_thread_id
        return {'tasks_observed':True}
    monkeypatch.setattr(entry, 'RUN_ROOT', tmp_path/'runs')
    monkeypatch.setattr(entry, 'CodexReadOnlyClient', Client)
    monkeypatch.setattr(entry.runner, 'execute_prepared', execute)
    assert entry.run(args) == {'tasks_observed':True}
    assert seen == ['open', 'closed']


@pytest.mark.parametrize('fault', ['root', 'child', 'parent', 'spawn', 'no_source'])
def test_native_lineage_must_match_actual_host(fault):
    plan, _ = entry.prepare(root_thread_id='root', independent_thread_id='child')
    def request(method, params):
        identity = params['threadId']
        thread = dict(id=identity, parentThreadId='root',
            source={'subAgent':{'thread_spawn':{'parent_thread_id':'root'}}})
        if fault == 'root' and identity == 'root':
            thread['id'] = 'wrong'
        if identity == 'child':
            if fault == 'child': thread['id'] = 'wrong'
            if fault == 'parent': thread['parentThreadId'] = 'wrong'
            if fault == 'spawn': thread['source']['subAgent']['thread_spawn']['parent_thread_id'] = 'wrong'
            if fault == 'no_source': thread['source'] = None
        return {'thread':thread}
    with pytest.raises(ValueError, match='native_lineage_mismatch'):
        entry.verify_native_principals(NS(request=request), plan)
