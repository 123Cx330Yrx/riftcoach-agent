"""One-shot entry and read-only evidence closure on the real application, offline."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone, timedelta
import json
import socket
from types import SimpleNamespace

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_journal import write_new_json
from app.evaluation.natural_duty_contract import request_bytes
from scripts import natural_duty_preparation as preparation
from scripts import run_natural_duty_development as runner
from scripts.natural_duty_receipts import read_calls, replay, summarize
from tests.test_natural_duty_candidate import Responses


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*a,**k):
        raise AssertionError('development entry tests cannot connect')
    monkeypatch.setattr(socket.socket,'connect',deny)
    monkeypatch.setattr(socket,'create_connection',deny)


@pytest.fixture(scope='module')
def prepared():
    existed=runner.RUN_DIRECTORY.exists()
    value=preparation.prepare(runner.RUN_ID)
    assert runner.RUN_DIRECTORY.exists()==existed
    return value


def test_actual_preview_binds_source_observed_task_and_budget_without_run(prepared):
    first, plan = prepared
    assert plan['provider_requests']==0 and not plan['execution_authorized']
    assert plan['sources']==preparation.SOURCE_SHA and plan['relationship']=='observed'
    assert '不是阅读者本人' in plan['actual_compiled_task']
    assert first.metadata['coach_budget_contract']=='coach-bounded-review-v2'
    assert first.metadata['agent_loop_iteration']==1 and first.timeout_s==300
    assert plan['first_request_sha256']==preparation.sha(request_bytes(first))
    assert plan['reservation_estimate']['estimated_uncached_cny']=='5.7595904'
    assert plan['limits']==preparation.LIMITS


def grant(plan):
    now = datetime.now(timezone.utc)
    return dict(version=runner.GRANT_VERSION, run_id=runner.RUN_ID, execution_head='a'*40,
        issued_at=now.isoformat(), expires_at=(now+timedelta(hours=1)).isoformat(),
        preparation_plan_sha256=plan['preparation_plan_sha256'], limits=preparation.LIMITS,
        estimated_uncached_cny=plan['reservation_estimate']['estimated_uncached_cny'],
        retry_authorized=False, production_admitted=False, user_authorization_evidence='OFFLINE TEST ONLY')


def setup(tmp_path, monkeypatch, prepared, *, mode='pass', extra_round=False, fault=None):
    first, plan = prepared
    plan = deepcopy(plan)
    prep = tmp_path/'preparation.json'
    auth = tmp_path/'authorization.json'
    write_new_json(prep,plan)
    write_new_json(auth,grant(plan))
    monkeypatch.setattr(runner,'prepare',lambda _: (first,plan))
    monkeypatch.setattr(runner,'current_head',lambda:'a'*40)
    monkeypatch.setattr(runner,'verify_ci',lambda *a:dict(head_sha='a'*40,status='completed',conclusion='success'))
    monkeypatch.setattr(runner,'RUN_DIRECTORY',tmp_path/'run')
    from scripts import run_role_coach_development as old
    monkeypatch.setattr(old,'load_role_settings',lambda _: tuple(SimpleNamespace(model=m,
        base_url='https://open.bigmodel.cn/api/paas/v4',api_key='OFFLINE_FIXTURE') for m in ('glm-5.3-flash','glm-5.3')))
    generator = Responses(mode=mode,extra_round=extra_round)
    reviewer = Responses(reviewer=True,mode=mode,extra_round=extra_round)
    sent = []

    def child(command,raw,*,directory,transport_id,**kwargs):
        sent.append(raw)
        if fault=='unknown' and len(sent)==3:
            write_new_json(directory/'result.json',dict(state='deadline',transport_id=transport_id))
            from app.providers.errors import ProviderTimeoutError
            raise ProviderTimeoutError(provider='zhipu',code='stream_deadline')
        request = bridge.REQUEST.validate_json(raw)
        response = (reviewer if transport_id.endswith(':review') else generator).chat(request)
        write_new_json(directory/'result.json',dict(state='complete',transport_id=transport_id))
        if fault!='missing_observation' or len(sent)!=3:
            write_new_json(directory/'progress.json',bridge.CapacityBridgeObservation(
                state='complete',close_state='closed',eof_ms=1,close_ms=1,terminal_ms=1,
                http_requests=1,input_tokens=response.usage.input_tokens,output_tokens=response.usage.output_tokens).model_dump(mode='json'))
        return response

    monkeypatch.setattr(bridge,'run_child',child)
    kwargs = dict(preparation_file=prep,authorization_file=auth,ci_run='offline',
                  env_file=tmp_path/'never-loaded.env',operator_directory=tmp_path/'operator')
    return kwargs,sent


@pytest.mark.parametrize('mode,extra,calls,outcome',[
    ('pass',False,4,'candidate_initial_pass_unqualified'),
    ('repair',False,6,'candidate_repaired_pass_unqualified'),
    ('repair',True,5,'insufficient_fresh_call_slots')])
def test_entry_actual_rag_budget_patch_receipts_closure_and_duplicate_stop(tmp_path,monkeypatch,prepared,capsys,mode,extra,calls,outcome):
    kwargs,sent=setup(tmp_path,monkeypatch,prepared,mode=mode,extra_round=extra)
    result=runner.execute(**kwargs)
    assert result['status']==('stopped_unqualified' if extra else 'completed_unqualified') and result['first_request_matched']
    assert result['candidate_outcome']['outcome']==outcome
    assert result['accounting']['reserved_calls']==len(sent)==calls
    assert result['accounting']['completed_calls']==calls and result['accounting']['unknown_usage_calls']==0
    assert result['accounting']['http_calls_known']==calls and not result['publication_allowed']
    records=[json.loads(line) for line in capsys.readouterr().out.splitlines()]
    guard_sha,closure_sha=records[0]['guard_sha256'],records[-1]['closure_sha256']
    assert records[0]['event']=='execution_guard' and records[-1]['event']=='execution_closed'
    root=tmp_path/'run'
    before=preparation.inventory(root.rglob('*'),root=root)
    checked=replay(run_directory=root,operator_directory=tmp_path/'operator',guard_sha=guard_sha,closure_sha=closure_sha)
    assert checked['accounting']==result['accounting'] and checked['native_semantic_reviews_required']
    assert preparation.inventory(root.rglob('*'),root=root)==before
    with pytest.raises(FileExistsError,match='natural_run_or_claim_already_exists'):
        runner.execute(**kwargs)
    assert len(sent)==calls
    with pytest.raises(ValueError,match='natural_original_stdout_root_mismatch'):
        replay(run_directory=root,operator_directory=tmp_path/'operator',guard_sha='0'*64,closure_sha=closure_sha)
    (root/'injected.json').write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='natural_closed_inventory_changed'):
        replay(run_directory=root,operator_directory=tmp_path/'operator',guard_sha=guard_sha,closure_sha=closure_sha)


@pytest.mark.parametrize('fault',['unknown','missing_observation'])
def test_incomplete_call_never_becomes_zero_or_success(tmp_path,monkeypatch,prepared,capsys,fault):
    kwargs,sent=setup(tmp_path,monkeypatch,prepared,fault=fault)
    result=runner.execute(**kwargs)
    assert len(sent)==3 and not result['publication_allowed']
    if fault=='unknown':
        assert result['accounting']['reserved_calls']==3
        assert result['accounting']['completed_calls']==2 and result['accounting']['unknown_usage_calls']==1
        assert result['accounting']['total_estimated_uncached_cny'] is None
    else:
        assert result['status']=='failed'
        assert result['accounting']['accounting_status']=='invalid_receipts'
        assert result['accounting']['unknown_usage_calls'] is None
    assert (tmp_path/'operator/closure.json').exists()
    records=[json.loads(line) for line in capsys.readouterr().out.splitlines()]
    checked=replay(run_directory=tmp_path/'run',operator_directory=tmp_path/'operator',
        guard_sha=records[0]['guard_sha256'],closure_sha=records[-1]['closure_sha256'])
    assert checked['accounting']==result['accounting']


@pytest.mark.parametrize('field,value',[
    ('version','old-authorization'),('run_id','different'),('execution_head','b'*40),
    ('preparation_plan_sha256','0'*64),('retry_authorized',True),('production_admitted',True),
    ('estimated_uncached_cny','0'),('user_authorization_evidence',''),
    ('expires_at','2026-01-01T00:00:00+00:00'),('limits',dict(max_calls=7))])
def test_wrong_or_expired_grant_stops_before_claim_credentials_or_io(tmp_path,monkeypatch,prepared,field,value):
    kwargs,sent=setup(tmp_path,monkeypatch,prepared)
    auth=json.loads(kwargs['authorization_file'].read_bytes());auth[field]=value
    kwargs['authorization_file'].write_bytes(preparation.canonical(auth))
    with pytest.raises(ValueError,match='natural_fresh_specific_authorization_required'):
        runner.execute(**kwargs)
    assert not sent and not (tmp_path/'run').exists() and not (tmp_path/'operator').exists()


def test_first_request_drift_rejected_before_stream_claim(tmp_path,monkeypatch,prepared):
    kwargs,sent=setup(tmp_path,monkeypatch,prepared)
    first,plan=prepared
    first=replace(first,metadata={**first.metadata,'unexpected':'changed'})
    plan=deepcopy(plan)
    plan['first_request_sha256']=preparation.sha(request_bytes(first))
    del plan['preparation_plan_sha256']
    plan['preparation_plan_sha256']=preparation.sha(preparation.canonical(plan))
    kwargs['preparation_file'].write_bytes(preparation.canonical(plan))
    kwargs['authorization_file'].write_bytes(preparation.canonical(grant(plan)))
    monkeypatch.setattr(runner,'prepare',lambda _:(first,plan))
    result=runner.execute(**kwargs)
    assert not sent and not result['first_request_matched']
    assert result['accounting']['reserved_calls']==0


def test_ci_requires_all_shards_same_head_and_keeps_network_process_local(monkeypatch):
    monkeypatch.setattr(runner,'current_head',lambda:'a'*40)
    names=['web-checks','postgres-migrations','packaging-smoke',*(f'pytest-shards ({i})' for i in range(4))]
    value=dict(headSha='a'*40,status='completed',conclusion='success',jobs=[dict(name=n,conclusion='success') for n in names])
    def read(*a,**kw):
        assert kw['env']['HTTPS_PROXY']=='http://127.0.0.1:12000'
        return preparation.canonical(value)
    monkeypatch.setattr(runner.subprocess,'check_output',read)
    assert runner.verify_ci('offline','a'*40)['conclusion']=='success'
    value['jobs'][-1]['conclusion']='failure'
    with pytest.raises(ValueError,match='natural_exact_head_public_ci_required'):
        runner.verify_ci('offline','a'*40)


def test_source_drift_fails_before_build(tmp_path,monkeypatch):
    monkeypatch.setattr(preparation,'SOURCES',tmp_path)
    (tmp_path/'evidence_bundle.json').write_bytes(b'{}')
    with pytest.raises(ValueError,match='natural_source_changed'):
        preparation.load_sources()


@pytest.mark.parametrize('filename',['first-request.json','authorization.json','plan.json'])
def test_modified_pre_send_root_cannot_be_blessed_by_terminal_closure(tmp_path,monkeypatch,prepared,capsys,filename):
    kwargs,sent=setup(tmp_path,monkeypatch,prepared)
    real_child=bridge.run_child
    def child(*a,**kw):
        response=real_child(*a,**kw)
        if len(sent)==4:
            path=tmp_path/'run'/filename
            value=json.loads(path.read_bytes())
            value['unexpected']='post-send mutation'
            path.write_bytes(preparation.canonical(value))
        return response
    monkeypatch.setattr(bridge,'run_child',child)
    result=runner.execute(**kwargs)
    assert len(sent)==4 and result['status']=='failed'
    records=[json.loads(line) for line in capsys.readouterr().out.splitlines()]
    with pytest.raises(ValueError,match='natural_archived_input_root_mismatch'):
        replay(run_directory=tmp_path/'run',operator_directory=tmp_path/'operator',
            guard_sha=records[0]['guard_sha256'],closure_sha=records[-1]['closure_sha256'])


@pytest.mark.parametrize('after_guard,expected_sends,expected_timeout',[(901,0,None),(899.5,4,.5)])
def test_expensive_preflight_uses_same_budget_deadline(tmp_path,monkeypatch,prepared,after_guard,expected_sends,expected_timeout):
    kwargs,sent=setup(tmp_path,monkeypatch,prepared)
    from app.runtime import coach_budget
    real_init=coach_budget.CoachBudgetedProvider.__init__
    clock=[0]
    budgets=[]
    def init(self,*a,**kw):
        real_init(self,*a,**dict(kw,clock=lambda:clock[0]))
        budgets.append(self)
        clock[0]=899
    monkeypatch.setattr(coach_budget.CoachBudgetedProvider,'__init__',init)
    original=runner.inventory
    def expensive(paths,**kw):
        result=original(paths,**kw)
        clock[0]=after_guard
        return result
    monkeypatch.setattr(runner,'inventory',expensive)
    result=runner.execute(**kwargs)
    assert len(sent)==expected_sends
    if not sent:
        assert budgets[0].calls==0 and budgets[0].reserved_tokens==0
        assert result['status']=='failed'
    else:
        assert all(bridge.REQUEST.validate_json(raw).timeout_s==expected_timeout for raw in sent)
