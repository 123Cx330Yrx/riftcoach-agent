"""Time-only continuation keeps money/accounting and unrelated cases bounded."""
import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import original15_execution_time_allowance as allowance
from scripts.sol_original15_launch import ENVELOPE
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.sol_session_runtime import SessionBudget
from app.providers.errors import ProviderResponseError
from app.providers.models import ChatMessage, ChatRequest, MessageRole


def fixture():
    report = 'unchanged actual report'
    manifest = dict(version=allowance.VERSION, plan_sha256='plan', authorization_sha256='auth',
        case='scope:3', remaining_stage='completion-fresh', original_limits=dict(ENVELOPE),
        additional_active_seconds=3600, effective_case_active_seconds=7200,
        effective_batch_active_seconds=57600, reset_accounting=False,
        additional_requests=0, additional_tokens=0, extend_authorization_expiry=False,
        user_authorization_evidence='budget may be increased', session_root=str(Path('case/session')),
        guard_sha256='guard', report_sha256=hashlib.sha256(report.encode()).hexdigest())
    descriptor = dict(execution_timeout_s=3600, max_calls=8, total_tokens=739840,
        max_output_tokens=16384, request_timeout_s=300, max_input_tokens=64000)
    contract = SimpleNamespace(descriptor=lambda:dict(descriptor), grounded=True)
    budget = SimpleNamespace(contract=contract,
        session=SimpleNamespace(root=Path(manifest['session_root']),guard_sha='guard'))
    request = ChatRequest(messages=(ChatMessage(role=MessageRole.USER,content='review'),), metadata={'sol_review_validation':
        dict(duty='completion',stage='fresh',report=report)}, timeout_s=300, max_tokens=16)
    return manifest, budget, request, descriptor


def test_only_recorded_session_and_stage_receive_time():
    manifest,budget,request,original = fixture()
    allowance.validate(manifest,plan_sha='plan',authorization_sha='auth',original_limits=ENVELOPE)
    limits = allowance.adjusted_limits(budget,request,manifest,lambda:None)
    assert limits == dict(original,execution_timeout_s=7200)
    assert budget.contract.descriptor() == original
    budget.session.root = Path('other/session')
    assert allowance.adjusted_limits(budget,request,manifest,lambda:None) == original
    budget.session.root = Path(manifest['session_root'])
    request.metadata['sol_review_validation']['duty'] = 'facts'
    assert allowance.adjusted_limits(budget,request,manifest,lambda:None) == original


@pytest.mark.parametrize('field,value',[
    ('reset_accounting',True),('additional_requests',1),('additional_tokens',1),
    ('extend_authorization_expiry',True),('case','scope:4'),
    ('effective_case_active_seconds',99999),('plan_sha256','other')])
def test_scope_or_money_cannot_expand(field,value):
    manifest,_,_,_ = fixture();manifest[field]=value
    with pytest.raises(ValueError,match='allowance_invalid'):
        allowance.validate(manifest,plan_sha='plan',authorization_sha='auth',original_limits=ENVELOPE)


def test_changed_report_or_control_rejected():
    manifest,budget,request,_ = fixture()
    request.metadata['sol_review_validation']['report'] += 'changed'
    with pytest.raises(ValueError,match='allowance_report'):
        allowance.adjusted_limits(budget,request,manifest,lambda:None)
    def changed():raise ValueError('controls changed')
    with pytest.raises(ValueError,match='controls changed'):
        allowance.adjusted_limits(budget,request,manifest,changed)


def test_real_shared_budget_uses_new_limit_without_resetting_counters():
    manifest,stub,request,_ = fixture()
    budget = CoachBudgetedProvider.__new__(CoachBudgetedProvider)
    budget.__dict__.update(stub.__dict__)
    budget.clock=lambda:4000.0;budget.started=0.0
    budget.calls=5;budget.tokens=58785;budget.reserved_tokens=137228;budget.stopped=False
    budget.provider_name='test';budget.model_name='test'
    sent=[]
    class Provider:
        provider_name='test';model_name='test'
        def chat(self,issued):
            sent.append(issued)
            raise ProviderResponseError(provider='test',code='expected_test_stop')
    budget.provider=Provider();budget._provider_for_request=lambda issued:budget.provider
    patched=allowance.compile_chat(CoachBudgetedProvider._chat_once,
        lambda owner,issued:allowance.adjusted_limits(owner,issued,manifest,lambda:None))
    with pytest.raises(ProviderResponseError,match='expected_test_stop'):
        patched(budget,request)
    assert len(sent)==1 and sent[0].timeout_s==300
    assert budget.calls==6 and budget.tokens==58785 and budget.reserved_tokens>137228
    # Cumulative 7200 really expires; there is no restarted clock or extra send.
    budget.stopped=False;budget.clock=lambda:7201.0
    with pytest.raises(ProviderResponseError,match='timeout'):
        patched(budget,request)
    assert len(sent)==1 and budget.calls==6


def test_retry_patch_preserves_real_source_and_closure():
    fn=allowance.compile_retry(SessionBudget._manual_retry,
        'limits = self.contract_module.CONTRACT.descriptor()',
        'limits = _original15_retry_limits(self, failed)',lambda owner,failed:{})
    assert callable(fn) and inspect.getsourcefile(fn)=='<original15-recorded-time-allowance>'

    class Parent:
        def chat(self,request):return 'parent'
    captured='closure stays'
    class Child(Parent):
        def chat(self,request):
            limits = self.contract_module.CONTRACT.descriptor()
            return super().chat(request), captured, limits
    fn=allowance.compile_retry(Child.chat,
        'limits = self.contract_module.CONTRACT.descriptor()',
        'limits = _original15_retry_limits(self, request)',lambda owner,request:7200)
    assert fn(Child(),None)==('parent','closure stays',7200)
