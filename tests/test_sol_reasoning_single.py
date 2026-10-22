"""One-request entry lifecycle, offline real worker/SDK; not model evidence."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import socket
import sys

import pytest

from app.evaluation import sol_natural_contract as contract
from app.evaluation.golden_native_issues_review import build_inputs
from scripts import sol_reasoning_single as single
from scripts import reviewer_responses_process as process
from scripts.prepare_reviewer_profile_screen import visible, json_value
from tests.test_natural_duty_candidate import Responses
from tests.test_sol_natural_candidate import CHILD


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('network forbidden')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    request = contract.make_request(build_inputs(Responses().req), 'facts')
    business, context = visible(json_value(request)), request.metadata[contract.CONTEXT]
    parent, control, operator = (tmp_path/name for name in ('parent', 'control', 'operator'))
    call = parent/single.CALL
    call.mkdir(parents=True)
    control.mkdir()
    old_plan = dict(head='previous-head', review_plan={'offline': True})
    process.write_json(parent/'plan.json', old_plan)
    process.write_json(call/'request.json', business)
    process.write_json(call/'validation-context.json', context)
    now = datetime.now(timezone.utc)
    grant = dict(head='previous-head', plan_sha256=single.sha(parent/'plan.json'),
        issued_at=(now-timedelta(minutes=1)).isoformat(), expires_at=(now+timedelta(hours=1)).isoformat(),
        continuation=dict(max_new_attempts=5, max_new_tokens=401920))
    process.write_json(control/'authorization.json', grant)
    (control/'start-0001.stdout.txt').write_text('ORIGINAL_STDOUT_ROOT\n', encoding='utf-8')
    monkeypatch.setattr(single, 'PARENT_GRANT', single.sha(control/'authorization.json'))
    monkeypatch.setattr(single, 'PARENT_STDOUT', single.sha(control/'start-0001.stdout.txt'))
    seal = dict(inventory=single.inventory(parent), original_roots=dict(authorization_sha=single.PARENT_GRANT),
        result=dict(accounting=dict(calls=6, tokens=80137, reserved_tokens=145824, retries=1),
                    continuation=dict(new_calls=1, new_known_tokens=28070)))
    process.write_json(parent/'seal.json', seal)
    monkeypatch.setattr(single, 'PARENT_SEAL', single.sha(parent/'seal.json'))
    monkeypatch.setattr(single, 'REQUEST_SHA', single.sha(call/'request.json'))
    monkeypatch.setattr(single, 'CONTEXT_SHA', single.sha(call/'validation-context.json'))
    monkeypatch.setattr(single, 'WIRE_SHA', single.digest(single.codec.build_wire(business)))
    monkeypatch.setattr(single, 'REPORT_SHA', single.hashlib.sha256(context['report'].encode()).hexdigest())
    monkeypatch.setattr(single, 'current_head', lambda: 'offline-frozen-head')
    monkeypatch.setattr(single, 'source_identity', lambda: {'offline_source': True})
    monkeypatch.setattr(single, 'verify_ci', lambda ci, head: dict(run_id=ci, head_sha=head))
    monkeypatch.setattr(single, 'native_state', lambda plan: dict(verified=True, fixture_only=True))
    monkeypatch.setattr(single, 'hidden_key', lambda: 'OFFLINE_SENTINEL')
    monkeypatch.chdir(single.ROOT)
    root = single.prepare(operator, parent, control)
    return operator, root['plan_sha256'], parent, control, now


@pytest.mark.parametrize('mode,status,code,unknown', [
    ('pass', 200, 'ok', 0), ('reasoning_conflict', 200, 'worker_rejected', 0),
    ('sdk_decode_conflict', 200, 'worker_rejected', 0), ('pass', 524, 'worker_rejected', 80384),
])
def test_actual_worker_once_retains_opinion_usage_and_history(prepared, monkeypatch, mode, status, code, unknown):
    operator, pin, parent, control, _ = prepared
    original = (single.inventory(parent), single.inventory(control))
    sends = []
    def send(business, **kwargs):
        sends.append(deepcopy(business))
        command = [sys.executable, '-c', 'MODE='+repr(mode)+'\nSTATUS='+str(status)+'\n'+CHILD]
        return process.run_once(business, **kwargs, command=command)
    monkeypatch.setattr(single, 'run_once', send)
    result = single.execute(operator, pin, 'offline-ci')
    assert len(sends) == 1 and result['code'] == code and result['http_requests'] == 1
    assert result['history'] == single.HISTORY and result['new_unknown_reserved_tokens'] == unknown
    assert result['public_opinion_retained'] is (status == 200)
    assert result['publication_allowed'] is result['qualified'] is result['semantic_approval'] is False
    if status == 200:
        assert result['new_known_tokens'] == 20
        assert result['decode']['identity_fields_equal'] is (mode != 'sdk_decode_conflict')
    worker = process.read_json(operator/'call/worker-result.json')
    if mode == 'reasoning_conflict':
        assert worker['code'] == 'reasoning_identity' and worker['public_tool_call'] is None
        assert worker['diagnostic_tool_call']['purpose'] == 'diagnostic_only'
    if mode == 'sdk_decode_conflict':
        assert worker['code'] == 'response_decode_mismatch'
    sealed = process.read_json(operator/'seal.json')
    assert single.inventory(operator) == {**sealed['inventory'], 'seal.json': single.sha(operator/'seal.json')}
    assert single.replay(operator, pin, result['seal_sha256'])['readonly'] is True
    assert (single.inventory(parent), single.inventory(control)) == original
    assert 'OFFLINE_SENTINEL' not in ''.join(p.read_text(encoding='utf-8') for p in operator.rglob('*.json'))
    with pytest.raises(ValueError, match='already_claimed'):
        single.execute(operator, pin, 'offline-ci')
    assert len(sends) == 1
    (operator/'call/receipt.json').write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='sealed_inventory_changed'):
        single.replay(operator, pin, result['seal_sha256'])


@pytest.mark.parametrize('fault', ['parent', 'stdout', 'source', 'python', 'expired'])
def test_preflight_failure_never_prompts_or_claims(prepared, monkeypatch, fault):
    operator, pin, parent, control, now = prepared
    if fault == 'parent':
        (parent/'unexpected.json').write_text('{}', encoding='utf-8')
    elif fault == 'stdout':
        (control/'start-0001.stdout.txt').write_text('changed', encoding='utf-8')
    elif fault == 'source':
        monkeypatch.setattr(single, 'source_identity', lambda: {'changed': True})
    elif fault == 'python':
        monkeypatch.setattr(sys, 'executable', str(operator/'wrong-python'))
    else:
        original = single.check
        monkeypatch.setattr(single, 'check', lambda *a, **kw: original(*a, now=now+timedelta(days=1)))
    monkeypatch.setattr(single, 'hidden_key', lambda: pytest.fail('unexpected credential prompt'))
    with pytest.raises(ValueError):
        single.execute(operator, pin, 'offline-ci')
    assert not (operator/'claim.json').exists() and not (operator/'call').exists()


def test_expiry_or_material_change_while_waiting_for_key_never_sends(prepared, monkeypatch):
    operator, pin, parent, _, now = prepared
    original = single.check
    state = {'now': now}
    monkeypatch.setattr(single, 'check', lambda *a, **kw: original(*a, now=state['now']))
    def waited():
        state['now'] += timedelta(hours=2)
        return 'OFFLINE_SENTINEL'
    monkeypatch.setattr(single, 'hidden_key', waited)
    monkeypatch.setattr(single, 'run_once', lambda *a, **kw: pytest.fail('sent after expiry'))
    with pytest.raises(ValueError, match='unexpired'):
        single.execute(operator, pin, 'offline-ci')
    assert not (operator/'claim.json').exists()


def test_cancelled_hidden_prompt_can_resume_but_claimed_crash_cannot(prepared, monkeypatch):
    operator, pin, _, _, _ = prepared
    def cancel():
        raise KeyboardInterrupt
    monkeypatch.setattr(single, 'hidden_key', cancel)
    with pytest.raises(KeyboardInterrupt):
        single.execute(operator, pin, 'offline-ci')
    assert not (operator/'claim.json').exists()
    single.check(operator, pin)
    monkeypatch.setattr(single, 'hidden_key', lambda: 'OFFLINE_SENTINEL')
    def crash(*args, **kwargs):
        raise OSError('OFFLINE_SECRET_IN_EXCEPTION')
    monkeypatch.setattr(single, 'run_once', crash)
    with pytest.raises(OSError):
        single.execute(operator, pin, 'offline-ci')
    assert (operator/'claim.json').exists() and not (operator/'seal.json').exists()
    with pytest.raises(ValueError, match='already_claimed'):
        single.execute(operator, pin, 'offline-ci')


def test_hidden_input_refuses_noninteractive_or_echo_fallback(monkeypatch, capsys):
    import getpass
    import warnings
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: False)
    with pytest.raises(ValueError, match='interactive_hidden_key'):
        single.hidden_key()
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: True)
    def fallback(*a):
        warnings.warn('offline fallback', getpass.GetPassWarning)
        pytest.fail('insecure fallback continued')
    monkeypatch.setattr(getpass, 'getpass', fallback)
    with pytest.raises(getpass.GetPassWarning):
        single.hidden_key()
    assert 'OFFLINE_SENTINEL' not in capsys.readouterr().out


def test_ci_failure_is_not_a_paid_failure(prepared, monkeypatch):
    operator, pin, _, _, _ = prepared
    def unavailable(*a):
        raise OSError('offline CI lookup failure')
    monkeypatch.setattr(single, 'verify_ci', unavailable)
    monkeypatch.setattr(single, 'hidden_key', lambda: pytest.fail('prompted without CI'))
    with pytest.raises(OSError):
        single.execute(operator, pin, 'offline-ci')
    assert not (operator/'claim.json').exists()
