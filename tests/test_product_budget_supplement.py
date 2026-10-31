"""Task limits, expiry and replay stay independent of global product policy."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import pytest

from app.evaluation.sol_natural_session import CandidateSession, SessionPaused
from app.product import sol_contract as product
from app.product.budget_supplement import activate, validate, execution_limits
from app.product.session_usage import session_accounting
from tests.test_sol_product_contract import isolated_budget, current_pins
from tests.test_sol_natural_candidate import offline
from tests.test_natural_duty_candidate import Responses
from scripts import review_duty_composition as duty


def opened(root, pins=None):
    return CandidateSession(root/'session',binding=dict(worker_profile=product.WORKER_PROFILE,
        candidate_contract=product.VERSION,task_id='supplement-test',run_id='candidate',owner_id='owner',
        execution_contract=product.CONTRACT.snapshot().model_dump(mode='json')),
        transport_root=root/'transport/candidate',journal_root=root/'journal',contract_module=product,
        worker_product=True,before_new_model=lambda:None,
        guard_sha=None if pins is None else pins['guard_sha256'],
        checkpoint_sha=None if pins is None else pins['checkpoint_sha256'])


def grant(session):
    return dict(kind='product-task-budget-supplement-v1',authorized=True,authorization_sha256='a'*64,
        binding=deepcopy(session.binding),guard_sha256=session.guard_sha,checkpoint_sha256=session.checkpoint_sha,
        baseline=session_accounting(session),
        original_limits=dict(max_calls=8,total_tokens=401920,execution_timeout_s=900),
        limits=dict(max_calls=12,total_tokens=723456,execution_timeout_s=2100),
        expires_at_utc=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())


@pytest.mark.parametrize('boundary',['calls','tokens','time','expiry','generation'])
def test_scoped_limit_stops_before_send(tmp_path,boundary,monkeypatch):
    from tests.test_natural_duty_transport import generation
    request=product.make_request(duty.TimedDocumentWorkflow.build_inputs(Responses().req),'facts')
    with opened(tmp_path) as session:
        activate(session,grant(session))
        budget,attempts=isolated_budget(tmp_path,session)
        if boundary=='calls':budget.calls=12
        elif boundary=='tokens':budget.tokens=723455
        elif boundary=='time':session.active_before=2101
        elif boundary=='generation':request=generation()
        else:
            from app.product import budget_supplement
            class Later(datetime):
                @classmethod
                def now(cls,tz=None):return datetime.now(tz)+timedelta(days=1)
            monkeypatch.setattr(budget_supplement,'datetime',Later)
        with pytest.raises(SessionPaused):budget.chat(request)
        assert attempts==[]


def test_request_nine_uses_supplement_and_can_replay_without_it(tmp_path):
    request=product.make_request(duty.TimedDocumentWorkflow.build_inputs(Responses().req),'facts')
    with opened(tmp_path) as session:
        value=grant(session);activate(session,value)
        budget,attempts=isolated_budget(tmp_path,session)
        budget.calls=budget.router._calls=8
        budget.tokens,budget.reserved_tokens=29323,366910
        response=budget.chat(request)
        assert budget.calls==9 and attempts==[200]
        assert budget.reserved_tokens==366910
    with opened(tmp_path,current_pins(tmp_path)) as session:
        activate(session)
        budget,attempts=isolated_budget(tmp_path,session)
        assert budget.chat(request)==response and attempts==[] and budget.calls==9
        assert execution_limits(session)['total_tokens']==723456
    assert product.CONTRACT.descriptor()['max_calls']==8
    assert product.CONTRACT.descriptor()['execution_timeout_s']==900


@pytest.mark.parametrize('fault',['owner','checkpoint','baseline','expired','limits','unauthorized'])
def test_invalid_supplement_is_not_persisted(tmp_path,fault):
    with opened(tmp_path) as session:
        value=grant(session)
        if fault=='owner':value['binding']['owner_id']='other'
        elif fault=='checkpoint':value['checkpoint_sha256']='b'*64
        elif fault=='baseline':value['baseline']['known_tokens']=1
        elif fault=='expired':value['expires_at_utc']='2000-01-01T00:00:00+00:00'
        elif fault=='limits':value['limits']['total_tokens']=True
        else:value['authorized']=False
        with pytest.raises(ValueError):activate(session,value)
        assert not (session.root/'budget-supplement.json').exists()
