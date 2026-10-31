"""Task-scoped supplement on the real session budget, without network IO."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from app.evaluation.sol_natural_session import SessionPaused, digest
from app.product import sol_contract as product
from tests.test_sol_product_contract import session_at, current_pins, isolated_budget
from tests.test_sol_natural_candidate import offline
from tests.test_natural_duty_candidate import Responses
from scripts import review_duty_composition as duty


def opened(root, *, manual=False, grant=None):
    pins = current_pins(root) if (root/'session').exists() else None
    session = session_at(root, pins=pins, manual=manual)
    session.binding.update(run_id='retry-test-run', owner_id='retry-test-owner')
    session.manual_retry_grant = deepcopy(grant)
    return session


def prepare(root):
    request = product.make_request(duty.TimedDocumentWorkflow.build_inputs(Responses().req), 'facts')
    for manual in (False, True, True):
        with opened(root, manual=manual) as session:
            budget, attempts = isolated_budget(root, session, statuses=(524,))
            with pytest.raises(SessionPaused, match='session_timeout_awaiting_manual_retry'):
                budget.chat(request)
            assert attempts == [524]
    intents = sorted((root/'session/operations').glob('*-intent.json'))
    failed = next(p for p in reversed(intents) if json.loads(p.read_bytes())['kind'] == 'model')
    failed = failed.with_name(failed.name.replace('-intent', '-result'))
    grant = dict(kind='product-one-extra-retry-v1', authorized=True,
        task_id='product-test', run_id='retry-test-run', owner_id='retry-test-owner',
        checkpoint_sha256=current_pins(root)['checkpoint_sha256'],
        failed_result_sha256=digest(failed.read_bytes()), original_grant_sha256='a'*64,
        prior_retries=2, additional_retries=1,
        limits={k: product.CONTRACT.descriptor()[k] for k in
                ('max_calls', 'total_tokens', 'execution_timeout_s')},
        expires_at_utc=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())
    return request, grant


def test_supplement_sends_once_preserves_unknown_and_replays_without_grant(tmp_path, monkeypatch):
    request, grant = prepare(tmp_path)
    originals = {p: p.read_bytes() for p in (tmp_path/'session/operations').glob('*')}
    with opened(tmp_path, manual=True, grant=grant) as session:
        budget, attempts = isolated_budget(tmp_path, session)
        response = budget.chat(request)
        assert response and len(attempts) == 1
        assert budget.calls == 4 and budget.router._retries == 3
        unknown = budget.reserved_tokens
        assert unknown > 0 and session.manual_retry_grant is None
    assert all(p.read_bytes() == raw for p, raw in originals.items())
    from app.product import manual_retry_grant
    class Later(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz) + timedelta(days=1)
    monkeypatch.setattr(manual_retry_grant, 'datetime', Later)
    with opened(tmp_path) as session:
        budget, attempts = isolated_budget(tmp_path, session)
        assert budget.chat(request) == response
        assert attempts == [] and budget.calls == 4 and budget.router._retries == 3
        assert budget.reserved_tokens == unknown
    assert product.CONTRACT.descriptor()['transport_retries'] == 2


@pytest.mark.parametrize('fault', ['not_authorized', 'expired', 'owner', 'checkpoint',
    'failure', 'extra_slots', 'global_budget', 'no_manual_flag'])
def test_invalid_supplement_never_sends(tmp_path, fault):
    request, grant = prepare(tmp_path)
    if fault == 'not_authorized': grant['authorized'] = False
    elif fault == 'expired': grant['expires_at_utc'] = '2000-01-01T00:00:00+00:00'
    elif fault == 'owner': grant['owner_id'] = 'other-owner'
    elif fault == 'checkpoint': grant['checkpoint_sha256'] = 'b'*64
    elif fault == 'failure': grant['failed_result_sha256'] = 'c'*64
    elif fault == 'extra_slots': grant['additional_retries'] = 2
    elif fault == 'global_budget': grant['limits']['max_calls'] = 9
    with opened(tmp_path, manual=fault != 'no_manual_flag', grant=grant) as session:
        budget, attempts = isolated_budget(tmp_path, session)
        with pytest.raises((ValueError, SessionPaused)):
            budget.chat(request)
        assert attempts == [] and budget.router._retries == 2


def test_supplement_cannot_be_reused_after_another_timeout(tmp_path):
    request, grant = prepare(tmp_path)
    with opened(tmp_path, manual=True, grant=grant) as session:
        budget, attempts = isolated_budget(tmp_path, session, statuses=(524,))
        with pytest.raises(SessionPaused, match='session_timeout_awaiting_manual_retry'):
            budget.chat(request)
        assert attempts == [524] and budget.router._retries == 3
    with opened(tmp_path, manual=True, grant=grant) as session:
        budget, attempts = isolated_budget(tmp_path, session)
        with pytest.raises(ValueError, match='retry_grant_limits'):
            budget.chat(request)
        assert attempts == []
