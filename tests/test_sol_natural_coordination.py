"""Actual natural Application/Runtime/worker path; HTTP/native are synthetic."""
import json
from pathlib import Path
import socket
import sys

import pytest

from app.evaluation import sol_review_contract as candidate
from app.evaluation.sol_natural_session import digest
from app.product.natural_duty_candidate import build_natural_duty_candidate
from app.runtime import sol_natural_provider
from scripts import sol_natural_launch as launch
from scripts.reviewer_profile_batch import inventory
from tests.test_patch_coordination import selection
from tests.test_sol_natural_candidate import application
from tests.test_sol_natural_launch import plan, grant
from tests.test_sol_session_review import controls, author


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail('natural coordination must not access network or credentials')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(launch, 'credentials', deny)
    monkeypatch.setattr(launch, 'continuation_credentials', deny)


def test_dual_preparation_and_choices_fail_before_keys(tmp_path, monkeypatch):
    p, pin = plan(tmp_path, monkeypatch, candidate=candidate)
    assert launch.candidate_for(p) is candidate
    assert p['limits'] == launch.limits(candidate)
    assert p['review_profile']['group'] == 'GPT-企业专线'
    assert not (Path(p['operator'])/'execution').exists()
    launch.validate_grant(grant(p, pin), p, pin)
    with pytest.raises(ValueError, match='requires_session'):
        build_natural_duty_candidate(summary_builder=None, provider_factory=None,
            knowledge_provider=None, runs_root=tmp_path, candidate=candidate, patch_coordination={})
    with pytest.raises(ValueError, match='patch_conflicts_required'):
        launch.execute(p, pin, None, authorization_file=tmp_path/'absent', authorization_sha='0'*64,
            ci_run='unused', preflight_proof={}, patch_coordination={})
    with pytest.raises(ValueError, match='host_only_requires_existing_roots'):
        launch.execute(p, pin, None, authorization_file=tmp_path/'absent', authorization_sha='0'*64,
            ci_run='unused', preflight_proof={}, host_only=True)


def test_cli_checks_choice_digest_before_opening_plan_or_native(tmp_path, monkeypatch):
    choice = tmp_path/'choice.json'
    choice.write_text('{}', encoding='utf-8')
    monkeypatch.setattr(sys, 'argv', ['sol_natural_launch', 'run', '--operator', str(tmp_path/'absent'),
        '--patch-coordination-file', str(choice), '--patch-coordination-sha', '0'*64])
    monkeypatch.setattr(launch, 'load', lambda *a, **k: pytest.fail('bad choice reached plan/native'))
    with pytest.raises(ValueError, match='patch_coordination_file_changed'):
        launch.main()


@pytest.mark.parametrize('scenario', ['success', 'timeout', 'reject'])
def test_natural_overlap_selection_gates_application_recovery_and_seal(tmp_path, monkeypatch, scenario):
    p, pin = plan(tmp_path, monkeypatch, candidate=candidate)
    opened, turns, _ = controls(tmp_path/'history')
    _, template = opened()
    native = launch.CodexHostReviewEventSource(template.native.event_source.client, p['review_plan'])
    ci_queries, keys, factories, attempts, receipts = [], [], [], [], []
    def verify_ci(*args):
        ci_queries.append('synthetic')
        return dict(conclusion='success')
    monkeypatch.setattr(launch, 'verify_ci', verify_ci)
    monkeypatch.setattr(launch, 'verify_native_principals', lambda *args: True)
    monkeypatch.setattr(launch, 'verify_preflight', lambda *args: True)
    def credentials(*args, **kwargs):
        assert kwargs['reviewer_group'] == 'GPT-企业专线'
        keys.append('synthetic')
        return None, 'OFFLINE_SENTINEL'
    monkeypatch.setattr(launch, 'credentials', credentials)
    injected = False
    def factory(**kwargs):
        nonlocal injected
        assert kwargs['contract_module'] is candidate
        statuses = ()
        if (scenario == 'timeout' and not injected and sum(map(len, attempts)) == 2
                and kwargs['api_key'] == 'OFFLINE_SENTINEL'):
            statuses, injected = (524,), True
        _, value, _, calls = application(Path(p['operator'])/'execution', candidate=candidate,
            mode='overlap', statuses=statuses)
        factories.append(value)
        attempts.append(calls)
        return value
    monkeypatch.setattr(sol_natural_provider, 'SolNaturalProviderFactory', factory)
    original_session_for = launch.session_for
    def session_for(*args, **kwargs):
        return original_session_for(*args, **dict(kwargs, sink=receipts.append))
    monkeypatch.setattr(launch, 'session_for', session_for)
    raw = json.dumps(grant(p, pin)).encode()
    authorization = tmp_path/'authorization.json'
    authorization.write_bytes(raw)
    common = dict(authorization_file=authorization, authorization_sha=digest(raw),
        ci_run='synthetic', preflight_proof={})
    roots, choice, host_only, manual = {}, None, False, False
    stages, waiting, retried = [], False, False
    journal = Path(p['operator'])/'execution/journal'
    for index in range(18):
        before = len(keys), len(ci_queries), sum(map(len, attempts))
        result = launch.execute(p, pin, native, **common, **roots, host_only=host_only,
            manual_retry=manual, patch_coordination=choice)
        choice, manual = None, False
        roots = dict(guard=receipts[-1]['guard_sha256'], checkpoint=receipts[-1]['checkpoint_sha256'])
        if host_only:
            assert before == (len(keys), len(ci_queries), sum(map(len, attempts)))
        if result['phase'] == 'closed':
            break
        reason = result['reason']
        if reason == 'session_awaiting_patch_coordination':
            assert not waiting and sum(map(len, attempts)) == 2
            assert not (journal/'application.json').exists()
            waiting = True
            conflict = json.loads((journal/'patch-conflicts.json').read_bytes())
            assert len(conflict['operations']) == 2 and len(conflict['conflicts']) == 1
            choice, host_only = selection(conflict), True
            continue
        if reason == 'session_model_boundary':
            assert host_only and (journal/'application.json').exists()
            host_only = False
            continue
        if reason == 'session_timeout_awaiting_manual_retry':
            assert scenario == 'timeout' and not retried
            prefix = inventory(journal)
            count = len(keys), sum(map(len, attempts))
            again = launch.execute(p, pin, native, **common, **roots)
            assert again['reason'] == reason and count == (len(keys), sum(map(len, attempts)))
            assert prefix == inventory(journal) and not (journal/'outcome.json').exists()
            roots = dict(guard=receipts[-1]['guard_sha256'], checkpoint=receipts[-1]['checkpoint_sha256'])
            manual, retried = True, True
            continue
        assert reason == 'session_awaiting_native_review'
        current, gate = session_for(p, pin, native, read_only=True,
            authorization_sha=common['authorization_sha'], **roots)
        with current:
            handle = list(gate.handles())[-1]
        stage = handle['binding']['key']
        stages.append(stage)
        if stage in ('facts-initial', 'completion-initial', 'patch-coordination', 'compatibility', 'edit'):
            assert not (journal/'application.json').exists()
        accepted = not (scenario == 'reject' and stage == 'patch-coordination')
        primary, event = author(handle, turns, gate.native.workspace, accepted=accepted)
        primary_file = tmp_path/f'primary-{index}.json'
        primary_file.write_text(json.dumps(primary), encoding='utf-8')
        submitted = launch.submit(p, pin, native, stage, primary_file, event,
            authorization_sha=common['authorization_sha'], **roots)
        assert submitted['accepted'] is accepted
        roots = dict(guard=receipts[-1]['guard_sha256'], checkpoint=receipts[-1]['checkpoint_sha256'])
        if not accepted:
            break
        host_only = stage not in ('facts-initial', 'facts-fresh')
    else:
        pytest.fail('natural coordination never completed')
    assert waiting
    count = sum(map(len, attempts))
    assert count == (2 if scenario == 'reject' else 4+int(retried))
    assert sum(len(f.providers[p['run_id']].generator.requests) for f in factories) == 2
    if scenario == 'reject':
        assert stages == ['facts-initial', 'completion-initial', 'patch-coordination']
        assert not (journal/'application.json').exists()
    else:
        assert result['phase'] == 'closed'
        assert stages == ['facts-initial', 'completion-initial', 'patch-coordination',
            'compatibility', 'edit', 'facts-fresh', 'completion-fresh']
        applied = json.loads((journal/'application.json').read_bytes())
        for stage in ('facts-fresh', 'completion-fresh'):
            material = json.loads((journal/'host'/stage/'material.json').read_bytes())
            assert digest(material['report'].encode()) == applied['report_sha256']
        assert len(list(journal.glob('application.json'))) == 1
    sealed = launch.seal(p, pin, native, authorization_sha=common['authorization_sha'], **roots)
    assert sealed['sealed'] and sealed['strict_replay'] and not sealed['publication_allowed']
    assert sealed['accounting']['calls'] == count+2
    assert (sealed['accounting']['reserved_tokens'] > 0) is retried
    assert sum(map(len, attempts)) == count
    with pytest.raises(ValueError, match='seal_already_exists'):
        launch.seal(p, pin, native, authorization_sha=common['authorization_sha'], **roots)
