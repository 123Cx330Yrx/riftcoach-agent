"""Time-only continuation keeps money/accounting and unrelated cases bounded."""
import hashlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
import threading

import pytest

from scripts import original15_execution_time_allowance as allowance
from scripts.sol_original15_launch import ENVELOPE
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.sol_session_runtime import SessionBudget
from app.evaluation.sol_natural_session import CandidateSession
from app.evaluation.natural_duty_workflow import NaturalDutyWorkflow
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
    assert fn.__kwdefaults__ == SessionBudget._manual_retry.__kwdefaults__ == {'format_repair': False}

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


def test_committed_application_replays_after_old_and_new_time_limits(tmp_path,monkeypatch):
    manifest,stub,_,_=fixture()
    session=CandidateSession.__new__(CandidateSession)
    session.root=tmp_path/'session';(session.root/'operations').mkdir(parents=True)
    session.guard_sha='guard';session.cursor=18;session._open=True
    session.read_only=True;session.reconciling=False;session.continuation=None
    session.binding={};session._mutex=threading.RLock();session.verify=lambda:None
    manifest['session_root']=str(session.root)
    budget=stub;budget.session=session;budget.stopped=False;budget.calls=5
    budget.tokens=58785;budget.reserved_tokens=137228;budget.started=0;budget.clock=lambda:9000
    draft='unchanged actual report';old='original report'
    evaluation=object()
    request=SimpleNamespace(evaluation=evaluation,player_summary=None,
        deterministic_report='',knowledge=None,report=old)
    data=dict(version='contract',report_sha256=hashlib.sha256(draft.encode()).hexdigest(),
        original_report_sha256=hashlib.sha256(old.encode()).hexdigest(),
        deterministic_application=True,host_semantics_verified=False,production_admitted=False)
    intent=dict(ordinal=19,kind='journal',request=dict(name='application',data=data))
    path=session.root/'operations/0019-intent.json';path.write_text(json.dumps(intent),encoding='utf-8')
    result=path.with_name('0019-result.json')
    result.write_text(json.dumps(dict(intent_sha256=allowance.sha(path),value=dict(recorded=True))),encoding='utf-8')
    original_bytes=path.read_bytes(),result.read_bytes()
    calls=[]
    def forbidden():raise AssertionError('must replay the committed application')
    def record(name,payload):
        calls.append(name)
        assert session.operation('journal',dict(name=name,data=payload),forbidden)==(dict(recorded=True),True)
    workflow=SimpleNamespace(send=SimpleNamespace(provider=budget),session=session,
        assembly=SimpleNamespace(report=draft),original_request=request,original=SimpleNamespace(source=SimpleNamespace(report=old)),
        proposals=[],initial_result=evaluation,state='revision',contract_module=SimpleNamespace(VERSION='contract'),
        record=record,stop=forbidden)
    workflow.verify_assembly=lambda:workflow.assembly
    monkeypatch.setattr(NaturalDutyWorkflow.revise.__globals__['direct'],'preview',lambda *args:workflow.assembly)
    patched=allowance.compile_retry(NaturalDutyWorkflow.revise,
        "if budget.clock()-budget.started >= budget.contract.descriptor()['execution_timeout_s']:",
        'if _original15_retry_limits(self, request):',
        lambda owner,req:allowance.application_time_exhausted(owner,req,manifest,lambda:None))
    assert patched(workflow,request).report==draft
    assert workflow.state=='fresh' and session.cursor==19 and calls==['application']
    assert original_bytes==(path.read_bytes(),result.read_bytes())
    assert budget.clock()==9000 and budget.tokens==58785 and budget.reserved_tokens==137228


def test_new_application_still_has_finite_time_and_exact_scope(tmp_path):
    manifest,budget,_,_=fixture();manifest['session_root']=str(tmp_path)
    budget.session=SimpleNamespace(root=tmp_path,guard_sha='guard',cursor=18)
    budget.started=0;budget.clock=lambda:4000
    workflow=SimpleNamespace(session=budget.session,send=SimpleNamespace(provider=budget),
        assembly=SimpleNamespace(report='unchanged actual report'),contract_module=SimpleNamespace(VERSION='contract'))
    request=SimpleNamespace(report='original')
    assert allowance.application_time_exhausted(workflow,request,manifest,lambda:None) is False
    budget.clock=lambda:7201
    assert allowance.application_time_exhausted(workflow,request,manifest,lambda:None) is True
    budget.session.root=tmp_path/'other'
    budget.clock=lambda:4000
    assert allowance.application_time_exhausted(workflow,request,manifest,lambda:None) is True


def test_additive_time_record_keeps_legacy_scope_and_money_unchanged():
    manifest, budget, request, original = fixture()
    legacy = dict(manifest)
    manifest.update(version=allowance.ADDITIVE_VERSION, case='claim-scope:6',
        prior_batch_active_seconds=57600, effective_batch_active_seconds=61200,
        prior_allowance_manifest_sha256='a'*64)
    allowance.validate(manifest, plan_sha='plan', authorization_sha='auth', original_limits=ENVELOPE)
    assert allowance.adjusted_limits(budget, request, manifest, lambda:None) == dict(original, execution_timeout_s=7200)
    assert budget.contract.descriptor() == original
    assert legacy['case'] == 'scope:3' and legacy['effective_batch_active_seconds'] == 57600
    for field, value in [('additional_requests',1), ('additional_tokens',1), ('reset_accounting',True),
                         ('prior_batch_active_seconds',0), ('effective_batch_active_seconds',999999)]:
        changed = dict(manifest, **{field:value})
        with pytest.raises(ValueError, match='allowance_invalid'):
            allowance.validate(changed, plan_sha='plan', authorization_sha='auth', original_limits=ENVELOPE)


def time_chain():
    first, _, _, _ = fixture()
    second = dict(first, version=allowance.ADDITIVE_VERSION, case='claim-scope:6',
        prior_batch_active_seconds=57600, effective_batch_active_seconds=61200,
        prior_allowance_manifest_sha256='a'*64)
    third = dict(first, version=allowance.ADDITIVE_VERSION, case='observed:2',
        prior_batch_active_seconds=61200, effective_batch_active_seconds=64800,
        prior_allowance_manifest_sha256='b'*64)
    return [first, second, third], [dict(sha256=letter*64) for letter in 'abc']


def test_third_case_extends_prior_total_without_borrowing_old_case_time():
    manifests, selections = time_chain()
    for manifest in manifests:
        allowance.validate(manifest, plan_sha='plan', authorization_sha='auth', original_limits=ENVELOPE)
    allowance.validate_lineage(manifests, selections, ENVELOPE)
    _, budget, request, original = fixture()
    for manifest in manifests[1:]:
        # Another case's entry alone must not change the selected session.
        manifest['session_root'] = str(Path(manifest['case'])/'session')
        assert allowance.adjusted_limits(budget, request, manifest, lambda:None) == original
    assert [m['effective_batch_active_seconds'] for m in manifests] == [57600, 61200, 64800]


@pytest.mark.parametrize('field,value', [
    ('prior_allowance_manifest_sha256', 'a'*64),
    ('prior_batch_active_seconds', 57600),
    ('effective_batch_active_seconds', 68400),
    ('version', allowance.VERSION),
])
def test_third_time_record_cannot_skip_reset_or_duplicate_lineage(field, value):
    manifests, selections = time_chain()
    manifests[2][field] = value
    with pytest.raises(ValueError, match='allowance_lineage'):
        allowance.validate_lineage(manifests, selections, ENVELOPE)


@pytest.mark.parametrize('value', [True, 61201, 54000])
def test_additive_time_record_requires_whole_existing_additions(value):
    manifests, _ = time_chain()
    manifests[2]['prior_batch_active_seconds'] = value
    manifests[2]['effective_batch_active_seconds'] = value + 3600
    with pytest.raises(ValueError, match='allowance_invalid'):
        allowance.validate(manifests[2], plan_sha='plan', authorization_sha='auth', original_limits=ENVELOPE)
