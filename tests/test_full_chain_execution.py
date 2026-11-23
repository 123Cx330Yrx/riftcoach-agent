"""Offline execution boundaries; no paid grant or real Host opinion is created."""
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from scripts import full_chain_execution as execution
from scripts import qualify_full_chain_controls as qualification
from tests import test_full_chain_evidence as chain


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')
    return execution.sha(path)


@pytest.fixture(scope='module')
def prepared(tmp_path_factory):
    root = tmp_path_factory.mktemp('execution-prepared')
    session = execution.ControlledFullChain(directory=root/'run', answers=root/'operator/answers',
        observations=root/'operator/observations')
    return execution.proposal(session)


def test_preparation_and_qualification_share_exact_35_stage_profile(prepared):
    plan, prep = prepared['plan'], prepared['qualification_preparation']
    assert plan['budget']['max_calls'] == 35
    assert plan['budget']['role_calls'] == {'glm-5.3':25, 'glm-5.3-flash':10}
    assert plan['budget']['max_tokens'] == 3386880
    assert len(plan['source_sha256']) == 53
    assert not prepared['execution_authorized']
    assert not Path(plan['evidence_paths']['directory']).exists()
    saved = dict(preparation_plan=plan, plan_sha256=prepared['plan_sha256'], execution_head='a'*40, ci_run='1')
    qualification.require_plan(saved, prep)
    for field, value in [('max_calls',45), ('role_calls', {'glm-5.3':30, 'glm-5.3-flash':15}),
                         ('max_tokens', 9999999), ('per_request_output',65536), ('max_host_seconds',172800)]:
        changed = deepcopy(saved)
        changed['preparation_plan']['budget'][field] = value
        with pytest.raises(ValueError, match='execution_profile'):
            qualification.require_plan(changed, prep)
    with pytest.raises(ValueError, match='execution_profile'):
        qualification.require_plan(saved, qualification.prepare())


@pytest.mark.parametrize('fault', [None,'expired','future','extended','naive','wrong_version',
    'not_authorized','wrong_preparation','mutated_bytes','bad_ci','bad_head','extra_field'])
def test_grant_scope_expiry_and_original_bytes(tmp_path, fault):
    now = datetime.now(timezone.utc)
    grant = dict(kind=execution.AUTH_VERSION, authorized=True, preparation_sha256='b'*64,
        execution_head='a'*40, ci_run='1', issued_at=(now-timedelta(seconds=1)).isoformat(),
        expires_at=(now+timedelta(hours=23)).isoformat())
    if fault == 'expired': grant['expires_at'] = (now-timedelta(milliseconds=1)).isoformat()
    if fault == 'future': grant['issued_at'] = (now+timedelta(seconds=1)).isoformat()
    if fault == 'extended': grant['expires_at'] = (now+timedelta(days=2)).isoformat()
    if fault == 'naive': grant['issued_at'] = now.replace(tzinfo=None).isoformat()
    if fault == 'wrong_version': grant['kind'] = 'document-relation-joint-authorization-v1'
    if fault == 'not_authorized': grant['authorized'] = False
    if fault == 'wrong_preparation': grant['preparation_sha256'] = 'c'*64
    if fault == 'bad_ci': grant['ci_run'] = 'pending'
    if fault == 'bad_head': grant['execution_head'] = 'short'
    if fault == 'extra_field': grant['retry'] = True
    path = tmp_path/'authorization.json'; pin = write(path, grant)
    if fault == 'mutated_bytes': path.write_text(path.read_text()+' ', encoding='utf-8')
    call = lambda:execution.require_authorization(path, pin, 'b'*64, now=now)
    if fault is None: assert call() == grant
    else:
        with pytest.raises(ValueError): call()


@pytest.mark.parametrize('used', ['directory','answers','observations','claim'])
def test_even_empty_previous_attempt_cannot_restart(tmp_path, used):
    session = execution.ControlledFullChain(directory=tmp_path/'run', answers=tmp_path/'operator/answers',
        observations=tmp_path/'operator/obs')
    operator = tmp_path/'operator'
    target = {'directory':session.directory, 'answers':session.workspace.answers,
              'observations':session.observations, 'claim':operator/'execution.json'}[used]
    target.mkdir(parents=True)
    with pytest.raises(ValueError, match='already_started'):
        execution.require_unused(session, operator)


@pytest.mark.parametrize('fault', [None,'authorization','ci','native','startup','dirty','secrets','operator'])
def test_execute_orders_gates_before_secret_access_and_keeps_exclusive_claim(tmp_path, monkeypatch, prepared, fault):
    seen = []
    session = execution.ControlledFullChain(directory=tmp_path/'run', answers=tmp_path/'operator/answers',
        observations=tmp_path/'operator/observations')
    runner = session.runner
    saved = deepcopy(prepared)
    saved['plan']['evidence_paths'] = dict(directory=str(session.directory), answers=str(session.workspace.answers),
        observations=str(session.observations), cwd=str(session.workspace.cwd), python=str(session.workspace.python))
    saved['operator'] = str(tmp_path/'operator')
    prep_path = tmp_path/'preparation.json'; prep_pin = write(prep_path, saved)
    now = datetime.now(timezone.utc)
    grant = dict(kind=execution.AUTH_VERSION, authorized=fault != 'authorization', preparation_sha256=prep_pin,
        execution_head='a'*40, ci_run='1', issued_at=now.isoformat(), expires_at=(now+timedelta(hours=23)).isoformat())
    grant_path = tmp_path/'authorization.json'; grant_pin = write(grant_path, grant)
    monkeypatch.setattr(execution, 'load_proposal', lambda *args:(session, saved))
    monkeypatch.setattr(execution, 'proposal', lambda *args:deepcopy(saved))
    def gate(name):
        seen.append(name)
        if fault == name: raise ValueError('offline_'+name)
    monkeypatch.setattr(runner, 'verify_public_ci', lambda ci:gate('ci') or 'a'*40)
    monkeypatch.setattr(session, 'execution_paths_preflight', lambda:gate('startup') or {})
    monkeypatch.setattr(runner, 'CodexReadOnlyClient', lambda *args:nullcontext(NS()))
    monkeypatch.setattr(runner, 'verify_native_principals', lambda *args:gate('native'))
    monkeypatch.setattr(runner, 'CodexHostReviewEventSource', lambda *args:NS())
    monkeypatch.setattr(runner, 'require_execution_event_source', lambda *args:None)
    monkeypatch.setattr(runner, 'require_unchanged_checkout', lambda *args:gate('dirty'))
    def secrets(*args):
        gate('secrets')
        assert (tmp_path/'operator/execution.json').is_file()
        assert not session.directory.exists()
        return NS(), NS()
    monkeypatch.setattr(runner, 'load_role_settings', secrets)
    monkeypatch.setattr(session, 'factory', lambda **kwargs:gate('factory') or NS())
    monkeypatch.setattr(runner, 'route_environment', lambda route:nullcontext())
    def observe(*args, **kwargs):
        gate('observe'); kwargs['before_send'](); session.authorization_guard()
        # Changing the original grant is caught again at the child/Host guard.
        grant_path.write_text(grant_path.read_text()+' ', encoding='utf-8')
        with pytest.raises(ValueError): session.authorization_guard()
        return dict(scan_completed=False, diagnostic_accepted=False, provider_calls=0)
    monkeypatch.setattr(runner, 'observe', observe)
    call = lambda:execution.execute(preparation=prep_path, preparation_sha=prep_pin,
        authorization=grant_path, authorization_sha=grant_pin,
        operator=tmp_path/('other' if fault == 'operator' else 'operator'), env_file='unused', codex_executable='unused')
    if fault is None:
        assert call()['provider_calls'] == 0
        assert seen.index('ci') < seen.index('native') < seen.index('secrets') < seen.index('factory') < seen.index('observe')
    else:
        with pytest.raises(ValueError): call()
    if fault not in (None, 'secrets'):
        assert 'secrets' not in seen and not session.directory.exists()
        assert not (tmp_path/'operator/execution.json').exists()
    else:
        assert (tmp_path/'operator/execution.json').is_file()
        with pytest.raises(ValueError, match='already_started'): call()


def test_new_profile_actual_author_submit_replay_and_reduced_batch_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(chain, 'FullChainEvidence', execution.ControlledFullChain)
    from scripts.run_full15_resumption_candidate import controls
    selected = [v for v in controls()[1] if v[0]['key'] in ('claim-scope:4', 'claim-scope:1')][::-1]
    session, plan, factory, source, judge, sent = chain.setup(tmp_path, monkeypatch, selected)
    assert plan['execution_profile'] == execution.VERSION and plan['budget']['max_calls'] == 35
    result = session.runner.observe(factory, session.directory, plan, event_source=source, adjudicate=judge)
    assert result['scan_completed'] and len(sent) == 4, result
    before = session.snapshot()
    sealed = session.evidence.replay(session.directory, event_source=source)
    assert before == session.snapshot() and len(sealed['stages']) == 4
    assert [s['stage'] for s in sealed['stages']] == ['initial','revision','final','initial']


def test_reduced_budget_is_enforced_by_real_runner_before_next_send(tmp_path, monkeypatch):
    monkeypatch.setattr(chain, 'FullChainEvidence', execution.ControlledFullChain)
    from scripts.run_full15_resumption_candidate import controls
    selected = [v for v in controls()[1] if v[0]['key'] in ('claim-scope:4', 'claim-scope:1')][::-1]
    session, plan, factory, source, judge, sent = chain.setup(tmp_path, monkeypatch, selected)
    # Smaller synthetic envelope exercises the exact same live batch check.
    plan['budget']['max_calls'] = 2
    (session.directory/'plan.json').write_text(json.dumps(dict(preparation_plan=plan,
        plan_sha256=session.runner.canonical_sha(plan))), encoding='utf-8')
    result = session.runner.observe(factory, session.directory, plan, event_source=source, adjudicate=judge)
    assert len(sent) == 2 and result['error_code'] == 'full15_batch_budget_exhausted'
    assert not (session.directory/selected[1][0]['key'].replace(':','-')).exists()


def test_proposal_rebuild_rejects_source_drift_and_alternate_run(tmp_path):
    session = execution.ControlledFullChain(
        directory=execution.ROOT/'data/runs/model_comparison'/execution.RUN_ID,
        answers=tmp_path/'operator/answers', observations=tmp_path/'operator/observations')
    value = execution.proposal(session)
    path = tmp_path/'proposal.json'; pin = write(path, value)
    loaded, saved = execution.load_proposal(path, pin)
    assert loaded.directory == session.directory and saved == value
    value['plan']['source_sha256'][execution.SOURCES[0]] = '0'*64
    pin = write(path, value)
    with pytest.raises(ValueError, match='preparation_changed'):
        execution.load_proposal(path, pin)
    alternate = execution.ControlledFullChain(directory=tmp_path/'another-run',
        answers=tmp_path/'operator/answers', observations=tmp_path/'operator/observations')
    pin = write(path, execution.proposal(alternate))
    with pytest.raises(ValueError, match='run_path'):
        execution.load_proposal(path, pin)
