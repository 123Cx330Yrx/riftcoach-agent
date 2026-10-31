from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import original15_authorization_continuation as module


def write(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def setup(tmp_path):
    start = datetime(2026, 10, 26, tzinfo=timezone.utc)
    original = dict(issued_at=start.isoformat(), expires_at=(start+timedelta(days=1)).isoformat(),
        limits={'max_requests':120, 'max_reserved_tokens':9646080}, model='gpt-6.1-sol', group='enterprise')
    original_sha = write(tmp_path/'authorization.json', original)
    plan = {'operator':str(tmp_path/'operator')}
    binding = {'limits':original['limits'], 'model':original['model'], 'group':original['group']}
    def validate(value, plan, pin, *, now=None):
        if (value != original or pin != 'pinned-plan'
                or not datetime.fromisoformat(value['issued_at']) <= now < datetime.fromisoformat(value['expires_at'])):
            raise ValueError('original15_specific_unexpired_authorization_required')
    launch = SimpleNamespace(validate_grant=validate, grant_binding=lambda p, pin:deepcopy(binding))
    now = start+timedelta(days=1, hours=1)
    continuation = dict(version=module.VERSION, original_authorization_sha256=original_sha,
        original_plan_sha256='pinned-plan', original_operator=plan['operator'], original_envelope=deepcopy(binding),
        scope='remaining_original_batch', reset_accounting=False, rewrite_original_authorization=False,
        automatic_retries=False, qualified=False, publication_allowed=False,
        issued_at=now.isoformat(), expires_at=(now+timedelta(days=1)).isoformat(),
        user_authorization_evidence='User explicitly continued the original batch after expiry was disclosed.')
    selected = dict(file='authorization-continuation-test.json',
        sha256=write(tmp_path/'authorization-continuation-test.json',continuation),
        module_sha256=module.sha(module.__file__))
    config = dict(authorization_sha256=original_sha, authorization_continuation=selected)
    return SimpleNamespace(control=tmp_path, launch=launch, original=original, plan=plan,
        now=now, continuation=continuation, config=config)


def accept(s):
    module.install(s.launch,s.control,s.config).validate(s.original,s.plan,'pinned-plan',now=s.now)


def test_expired_original_accepts_explicit_current_addendum_and_keeps_bytes(setup):
    s=setup
    original=(s.control/'authorization.json').read_bytes()
    accept(s)
    assert (s.control/'authorization.json').read_bytes()==original
    assert set(s.control.iterdir())=={s.control/'authorization.json',s.control/'authorization-continuation-test.json'}


def test_expired_original_without_addendum_fails(setup):
    s=setup;s.config.pop('authorization_continuation')
    with pytest.raises(ValueError,match='specific_unexpired_authorization_required'):accept(s)


def test_unexpired_original_still_works_without_addendum(setup):
    s=setup;s.config.pop('authorization_continuation');s.now-=timedelta(hours=2)
    accept(s)


@pytest.mark.parametrize('field,value',[
    ('original_plan_sha256','other-plan'),('original_operator','other-run'),
    ('original_authorization_sha256','wrong-sha'),('reset_accounting',True),
    ('automatic_retries',True),('qualified',True),('publication_allowed',True),
    ('scope','new_batch'),('rewrite_original_authorization',True),
])
def test_pinned_addendum_cannot_expand_scope(setup,field,value):
    s=setup;s.continuation[field]=value
    s.config['authorization_continuation']['sha256']=write(s.control/'authorization-continuation-test.json',s.continuation)
    with pytest.raises(ValueError,match='continuation_scope_changed'):accept(s)


@pytest.mark.parametrize('change',['budget','model','group'])
def test_even_repinned_addendum_keeps_original_budget_and_provider(setup,change):
    s=setup
    if change=='budget':s.continuation['original_envelope']['limits']['max_requests']=121
    else:s.continuation['original_envelope'][change]='different'
    s.config['authorization_continuation']['sha256']=write(s.control/'authorization-continuation-test.json',s.continuation)
    with pytest.raises(ValueError,match='continuation_scope_changed'):accept(s)


@pytest.mark.parametrize('change',['expired','future','overlong','no_evidence'])
def test_actual_time_and_human_evidence_required(setup,change):
    s=setup
    if change=='expired':s.now+=timedelta(days=1)
    if change=='future':s.now-=timedelta(seconds=1)
    if change=='overlong':s.continuation['expires_at']=(s.now+timedelta(days=2)).isoformat()
    if change=='no_evidence':s.continuation['user_authorization_evidence']=' '
    s.config['authorization_continuation']['sha256']=write(s.control/'authorization-continuation-test.json',s.continuation)
    with pytest.raises(ValueError,match='specific_unexpired_continuation_required'):accept(s)


def test_original_tampering_rejected(setup):
    s=setup;value=deepcopy(s.original);value['expires_at']=(s.now+timedelta(days=1)).isoformat()
    write(s.control/'authorization.json',value)
    with pytest.raises(ValueError,match='original_authorization_required'):accept(s)


def test_addendum_tampering_rejected(setup):
    s=setup;s.continuation['reset_accounting']=True
    write(s.control/'authorization-continuation-test.json',s.continuation)
    with pytest.raises(ValueError,match='continuation_controls_changed'):accept(s)


def test_module_tampering_rejected(setup):
    s=setup;s.config['authorization_continuation']['module_sha256']='wrong'
    with pytest.raises(ValueError,match='continuation_controls_changed'):accept(s)


def test_reinstall_uses_frozen_validator_and_rechecks_addendum_before_next_send(setup):
    s=setup;accept(s);accept(s)
    s.continuation['reset_accounting']=True
    write(s.control/'authorization-continuation-test.json',s.continuation)
    with pytest.raises(ValueError,match='continuation_controls_changed'):
        s.launch.validate_grant(s.original,s.plan,'pinned-plan',now=s.now)


def test_same_callback_rechecks_actual_expiry_after_human_input_wait(setup):
    s=setup
    validator=module.install(s.launch,s.control,s.config)
    validator.validate(s.original,s.plan,'pinned-plan',now=s.now)
    with pytest.raises(ValueError,match='specific_unexpired_continuation_required'):
        validator.validate(s.original,s.plan,'pinned-plan',now=s.now+timedelta(days=1))
