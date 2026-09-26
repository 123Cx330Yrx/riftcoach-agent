"""Execution/adjudication boundaries with network forbidden and scripted replies."""
from dataclasses import replace
import json
import socket
from types import SimpleNamespace

import pytest

from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_journal import write_new_json
from scripts import run_native_editor_diagnostic as runner
from scripts.check_native_contract_options import corrected_case3, PASS
from tests.test_golden_integrated_review import ReplayProvider
from scripts.native_contract_options import body


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*a,**kw): pytest.fail('diagnostic test must never reach network')
    monkeypatch.setattr(socket.socket,'connect',denied)
    monkeypatch.setattr(socket,'create_connection',denied)


def setup(tmp_path, *, started=1000):
    case, req, request = runner.prepare(1)
    write_new_json(tmp_path/'plan.json',dict(started_at_unix=started,case_id=case['id'],
        input_sha256=case['input_sha256'],head_sha='test-head',batch_id='test-batch'))
    write_new_json(tmp_path/'input.json',dict(report=req.report,review_raw=case['proposed_review_raw']))
    return case,req,request


def accept(directory,phase='edit',**kw):
    return runner.adjudicate(directory,phase,accepted=kw.get('accepted',True),
        reviewer='offline-scripted-reviewer',reasons='Analyst test fixture only; not actual independent model semantic acceptance.')


def test_preview_rebuilds_frozen_transport_and_never_loads_credentials(tmp_path,monkeypatch):
    import dotenv
    monkeypatch.setattr(dotenv,'dotenv_values',lambda *a: pytest.fail('preview loaded secrets'))
    for index in (1,2,3):
        result=runner.run(SimpleNamespace(case_index=index,phase='edit',execute=False))
        assert result['max_case_calls']==3 and result['semantic_approval'] is False
        assert result['input_ceiling']<=63936
    preview=runner.run(SimpleNamespace(case_index=1,phase='recheck',execute=False))
    assert preview['preview_scope'].startswith('frozen_editor_plan_only;')
    monkeypatch.setattr(runner,'prepare_editor_diagnostic',lambda: {})
    with pytest.raises(ValueError,match='frozen_plan_changed'): runner.prepare(1)


def test_edit_manual_pause_recheck_preserves_actual_report_and_prior_usage(tmp_path):
    case,req,_=setup(tmp_path)
    _,_,edit=corrected_case3()
    provider=ReplayProvider(lambda *_:compact(edit))
    result=runner.observe(provider,tmp_path,case,req,phase='edit',clock=lambda:1010)
    assert result['protocol_success'] and result['completed_calls']==1
    assert result['stop_reason']=='manual_editor_review_required' and not result['semantic_approval']
    recheck=ReplayProvider(lambda *_:PASS)
    with pytest.raises(FileNotFoundError):
        runner.observe(recheck,tmp_path,case,req,phase='recheck',clock=lambda:1020)
    assert not recheck.requests
    accept(tmp_path)
    result=runner.observe(recheck,tmp_path,case,req,phase='recheck',clock=lambda:1850)
    assert result['protocol_success'] and result['cumulative_budget_calls']==2
    assert result['cumulative_budget_tokens']==40 and result['elapsed_seconds']==850
    assert recheck.requests[0].timeout_s==50
    sent=body(recheck.requests[0])
    assert 'expected_dispositions_host_only' not in sent and 'reasons' not in sent
    assert '合并计算后，胜局补刀均值为 8.805' in compact(sent)
    accept(tmp_path,'recheck')
    assert runner.require_adjudication(tmp_path,'recheck').accepted
    with pytest.raises(FileExistsError):
        runner.observe(recheck,tmp_path,case,req,phase='recheck',clock=lambda:1850)
    assert len(recheck.requests)==1


@pytest.mark.parametrize('bad',['malformed','disposition','incomplete','interrupted'])
def test_failed_editor_is_terminal_without_paid_recheck_or_retry(tmp_path,bad):
    case,req,_=setup(tmp_path)
    _,_,value=corrected_case3()
    if bad=='disposition': value['decisions'][1]['disposition']='apply'
    class Provider(ReplayProvider):
        def chat(self,r):
            if bad=='interrupted':
                self._calls+=1
                raise RuntimeError('private secret must not appear in result')
            response=super().chat(r)
            if bad=='incomplete':
                response=replace(response,finish_reason='length')
                self.last_exchange=replace(self.last_exchange,response=response)
            return response
    provider=Provider(lambda *_:'{"report":' if bad=='malformed' else compact(value))
    result=runner.observe(provider,tmp_path,case,req,phase='edit',clock=lambda:1010)
    assert not result['protocol_success'] and result['attempted_calls']==1
    assert 'private secret' not in compact(result)
    assert result['unknown_usage_calls']==(1 if bad=='interrupted' else 0)
    with pytest.raises(FileExistsError): runner.observe(provider,tmp_path,case,req,phase='edit',clock=lambda:1010)
    if bad=='disposition':
        accept(tmp_path)
        with pytest.raises(ValueError,match='previous_phase_failed'):
            runner.observe(provider,tmp_path,case,req,phase='recheck',clock=lambda:1020)


@pytest.mark.parametrize('change',['plan','report','response','usage','request','rejected'])
def test_adjudication_cannot_be_reused_after_identity_changes(tmp_path,change):
    case,req,_=setup(tmp_path)
    _,_,value=corrected_case3()
    runner.observe(ReplayProvider(lambda *_:compact(value)),tmp_path,case,req,phase='edit',clock=lambda:1010)
    accept(tmp_path,accepted=change!='rejected')
    names={'plan':'plan.json','report':'edit/report.md','response':'edit/response-001.json',
        'usage':'edit/result.json','request':'edit/request-001.json'}
    if change!='rejected':
        p=tmp_path/names[change]
        p.write_text(p.read_text(encoding='utf-8')+' ',encoding='utf-8')
    provider=ReplayProvider(lambda *_:pytest.fail('tampered/rejected case emitted request'))
    with pytest.raises(ValueError,match='adjudication_identity_changed|manual_acceptance_required'):
        runner.observe(provider,tmp_path,case,req,phase='recheck',clock=lambda:1020)
    assert not provider.requests


def test_final_schema_recovery_is_last_call_and_deadline_does_not_reset(tmp_path):
    case,req,_=setup(tmp_path)
    _,_,value=corrected_case3()
    runner.observe(ReplayProvider(lambda *_:compact(value)),tmp_path,case,req,phase='edit',clock=lambda:1010)
    accept(tmp_path)
    provider=ReplayProvider(lambda _,n:PASS+'\ntrailing text' if n==1 else PASS)
    with pytest.raises(ValueError,match='deadline_exhausted'):
        runner.observe(provider,tmp_path,case,req,phase='recheck',clock=lambda:1900)
    assert not provider.requests and not (tmp_path/'recheck').exists()
    result=runner.observe(provider,tmp_path,case,req,phase='recheck',clock=lambda:1800)
    assert result['protocol_success'] and result['cumulative_budget_calls']==3
    assert result['cumulative_budget_tokens']==60
    assert len(provider.requests)==2 and all(r.timeout_s==100 for r in provider.requests)


def test_next_case_requires_previous_final_manual_acceptance_before_credentials(tmp_path,monkeypatch):
    import dotenv
    monkeypatch.setattr(runner,'LIVE_STATUS','bounded_editor_diagnostic_after_exact_ci')
    monkeypatch.setattr(runner,'verify_public_ci',lambda _: 'tested-head')
    monkeypatch.setattr(dotenv,'dotenv_values',lambda *a:pytest.fail('gate loaded secrets'))
    args=SimpleNamespace(execute=True,case_index=2,phase='edit',batch_id='editor-diagnostic-test',
        ci_run='test',output_root=tmp_path,env_file=tmp_path/'missing')
    with pytest.raises(ValueError,match='batch_start_order'): runner.run(args)
    batch=tmp_path/args.batch_id
    batch.mkdir()
    write_new_json(batch/'batch.json',dict(experiment=runner.EXPERIMENT,head_sha='tested-head',
        frozen_plan_sha256=runner.sha(runner.PLAN),max_cases=3,
        order=[c['id'] for c in runner.read(runner.PLAN)['cases']]))
    with pytest.raises(FileNotFoundError): runner.run(args)
    assert not (batch/'true_universal').exists()


def test_failed_candidate_is_offline_before_ci_or_credentials(monkeypatch):
    monkeypatch.setattr(runner,'verify_public_ci',lambda *_:pytest.fail('closed diagnostic reached CI'))
    with pytest.raises(ValueError,match='editor_diagnostic_offline'):
        runner.run(SimpleNamespace(execute=True,case_index=1,phase='edit'))


def test_crlf_report_is_preserved_exactly_across_manual_pause(tmp_path):
    case,req,_=setup(tmp_path)
    _,_,value=corrected_case3()
    value['report']=value['report'].replace('\n','\r\n')
    result=runner.observe(ReplayProvider(lambda *_:compact(value)),tmp_path,case,req,phase='edit',clock=lambda:1010)
    assert result['protocol_success']
    accept(tmp_path)
    wire,_=runner.restored_edit(tmp_path,case,req)
    assert wire.report==value['report']
    assert (tmp_path/'edit/report.md').read_bytes()==value['report'].encode('utf-8')


@pytest.mark.parametrize('target',['request','wire','reservation','terminal'])
def test_final_acceptance_binds_actual_request_and_transport_receipts(tmp_path,target):
    case,req,_=setup(tmp_path)
    _,_,value=corrected_case3()
    runner.observe(ReplayProvider(lambda *_:compact(value)),tmp_path,case,req,phase='edit',clock=lambda:1010)
    accept(tmp_path)
    runner.observe(ReplayProvider(lambda *_:PASS),tmp_path,case,req,phase='recheck',clock=lambda:1020)
    transport=tmp_path/'transport-recheck/stream-001'
    transport.mkdir(parents=True)
    write_new_json(transport/'reservation.json',dict(transport_id=runner.CAPACITY_TRANSPORT_ID,
        ordinal=1,request_sha256=runner.sha(tmp_path/'recheck/request-001.wire.json')))
    write_new_json(transport/'result.json',dict(transport_id=runner.CAPACITY_TRANSPORT_ID,state='complete'))
    path=tmp_path/'recheck/result.json'
    result=runner.read(path)
    result['receipted_transport']=True
    path.write_text(compact(result),encoding='utf-8')
    accept(tmp_path,'recheck')
    runner.require_adjudication(tmp_path,'recheck')
    path={'request':tmp_path/'recheck/request-001.json','wire':tmp_path/'recheck/request-001.wire.json',
        'reservation':transport/'reservation.json','terminal':transport/'result.json'}[target]
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='adjudication_identity_changed'):
        runner.require_adjudication(tmp_path,'recheck')


def test_inconsistent_wire_cannot_be_accepted_even_with_new_manual_digest(tmp_path):
    case,req,_=setup(tmp_path)
    _,_,value=corrected_case3()
    runner.observe(ReplayProvider(lambda *_:compact(value)),tmp_path,case,req,phase='edit',clock=lambda:1010)
    path=tmp_path/'edit/request-001.wire.json'
    path.write_bytes(path.read_bytes()+b' ')
    accept(tmp_path)
    with pytest.raises(ValueError,match='saved_exchange_identity_changed'):
        runner.restored_edit(tmp_path,case,req)
