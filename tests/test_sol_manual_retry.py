"""Human-invoked timeout recovery uses original receipts, never paid IO."""
import json
import sys
from types import SimpleNamespace

import pytest

from app.evaluation import sol_necessity_contract as candidate
from app.evaluation.sol_natural_session import SessionPaused, tree
from scripts import sol_natural_launch as launch
from tests.test_natural_duty_candidate import run
from tests.test_sol_natural_candidate import offline
from tests.test_sol_natural_launch import plan, grant
from tests.test_sol_natural_session import session, app_for, crash_after_model, NoSearch


def paused(tmp_path):
    first = session(tmp_path, candidate=candidate)
    with pytest.raises(SessionPaused, match='timeout_awaiting_manual_retry'), first:
        app, _, calls = app_for(tmp_path, first, 1, candidate=candidate, statuses=(524,))
        run(app)
    assert calls == [524]
    return first


def test_successful_retry_after_parent_loss_reconciles_without_resend(tmp_path):
    first = paused(tmp_path)
    retry = session(tmp_path, first, candidate=candidate, manual_retry=True)
    crash_after_model(retry, 4)
    with pytest.raises(SessionPaused, match='pending_reconciliation'), retry:
        app, _, calls = app_for(tmp_path, retry, 2, candidate=candidate, knowledge=NoSearch())
        run(app)
    assert calls == [200]
    originals = tree(retry.transport_root)
    recovered = session(tmp_path, retry, candidate=candidate, reconcile=True)
    with recovered:
        result = recovered.reconcile_completed()
        assert result['reconciled_ordinal'] == 4 and result['provider_requests'] == 0
    assert tree(recovered.transport_root) == originals
    resumed = session(tmp_path, recovered, candidate=candidate)
    with resumed:
        app, factory, calls = app_for(tmp_path, resumed, 3, candidate=candidate, knowledge=NoSearch())
        run(app)
        router = factory.providers['candidate']
        assert calls == [200, 200, 200]
        assert router._logical == {'generation':2, 'review':4}
        assert router._retries == 1 and router.candidate_budget.calls == 7
        assert router.candidate_budget.reserved_tokens > 0
        assert json.loads((resumed.journal_root/'outcome.json').read_bytes())['outcome'] == 'candidate_repaired_pass_unqualified'


def test_protocol_fault_on_manual_retry_cannot_buy_another_attempt(tmp_path):
    first = paused(tmp_path)
    retry = session(tmp_path, first, candidate=candidate, manual_retry=True)
    with retry:
        app, factory, calls = app_for(tmp_path, retry, 2, candidate=candidate,
            mode='reasoning_conflict', knowledge=NoSearch())
        run(app)
        assert calls == [200]
        assert not retry.status()['timeout_waiting']
        assert factory.providers['candidate'].candidate_budget.calls == 4
        assert json.loads((retry.journal_root/'outcome.json').read_bytes())['outcome'] == 'candidate_execution_failed'


def test_exhausted_active_budget_stays_paused_without_new_receipt(tmp_path):
    first = paused(tmp_path)
    original = tree(first.transport_root)
    retry = session(tmp_path, first, candidate=candidate, manual_retry=True)
    with pytest.raises(SessionPaused, match='retry_budget_extension_required'), retry:
        retry.active_before = candidate.CONTRACT.descriptor()['execution_timeout_s']+1
        app, _, calls = app_for(tmp_path, retry, 2, candidate=candidate, knowledge=NoSearch())
        run(app)
    assert calls == [] and tree(retry.transport_root) == original
    assert not retry.status()['closed'] and not (retry.journal_root/'outcome.json').exists()


def test_new_launcher_freezes_manual_policy_group_and_specific_grant(tmp_path, monkeypatch):
    p, pin = plan(tmp_path, monkeypatch, candidate=candidate)
    assert launch.candidate_for(p) is candidate
    assert p['retry_mode'] == 'manual-reaped-timeout-v1'
    assert p['review_profile']['group'] == 'GPT-企业专线'
    assert p['limits']['max_calls'] == 10 and p['limits']['transport_retries'] == 4
    value = grant(p, pin)
    launch.validate_grant(value, p, pin)
    for key in ('candidate_contract', 'retry_mode', 'review_profile'):
        wrong = dict(value)
        wrong.pop(key)
        with pytest.raises(ValueError, match='candidate_specific_authorization'):
            launch.validate_grant(wrong, p, pin)
    assert not (tmp_path/'operator/execution').exists()


def test_owned_flash_deadline_requires_manual_same_request_retry(tmp_path, monkeypatch):
    from app.evaluation import golden_stream_bridge as bridge
    from app.runtime.sol_natural_provider import SolNaturalProviderFactory
    from app.runtime.sol_session_runtime import SessionBudget
    from app.runtime.observed_provider import ObservedLLMProvider
    from tests.test_runtime_execution_factory_combined import _NoopObserver
    from tests.test_natural_duty_transport import generation, scripted_child
    sent = []
    supervisor, success = bridge.run_child, scripted_child(sent)
    def child(command, raw, **kwargs):
        if not sent:
            sent.append(raw)
            return supervisor([sys.executable, '-c', 'import time; time.sleep(10)'], raw,
                directory=kwargs['directory'], timeout_s=.05, transport_id=kwargs['transport_id'])
        return success(command, raw, **kwargs)
    monkeypatch.setattr(bridge, 'run_child', child)
    factory = SolNaturalProviderFactory(generator_settings=SimpleNamespace(model='glm-5.3-flash',
        api_key='OFFLINE_SENTINEL', base_url='https://open.bigmodel.cn/api/paas/v4'),
        api_key='OFFLINE_SENTINEL', transport_root=tmp_path/'transport', contract_module=candidate)
    def budget_for(sess):
        provider = ObservedLLMProvider(delegate=factory('candidate'), observer=_NoopObserver(),
            request_identity=candidate.request_identity)
        return SessionBudget(provider, session=sess, coach_contract=candidate.CONTRACT)
    first = session(tmp_path, candidate=candidate)
    with pytest.raises(SessionPaused, match='timeout_awaiting_manual_retry'), first:
        budget_for(first).chat(generation())
    assert len(sent) == 1
    with session(tmp_path, first, candidate=candidate, manual_retry=True) as retry:
        budget = budget_for(retry)
        assert budget.chat(generation()).model == 'glm-5.3-flash'
        assert len(sent) == 2 and json.loads(sent[0]) == json.loads(sent[1])
        assert budget.calls == 2 and budget.reserved_tokens > 0
        assert budget.router._logical == {'generation':1, 'review':0}
