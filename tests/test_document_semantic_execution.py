"""Offline execution/provenance counterexamples; never live quality evidence."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace as NS

import pytest

from app.evaluation.golden_stream_bridge import RESPONSE
from app.evaluation.role_task_outcome import stage_identity
from app.providers.models import ChatResponse, TokenUsage, ToolCall
from scripts import document_semantic_comparison as runner
from scripts import document_semantic_request as identity
from scripts import document_semantic_transport as transport
from scripts import prepare_document_semantic_comparison as prep
from scripts.codex_review_event_source import CodexHostReviewEventSource
from scripts.host_review_task_checkpoint import digest, read as read_checkpoint
from app.evaluation.golden_journal import write_new_json


@pytest.fixture(scope='module')
def prepared():
    return prep.prepare(root_thread_id='synthetic-root',independent_thread_id='synthetic-child')


CHILD = r'''
import json,sys,socket,openai
from pathlib import Path
from types import SimpleNamespace as NS
from tests.test_zhipu_stream_adapter import FakeClient,ClosableStream,chunk,usage,tool_fragment
from app.providers import config
def forbidden(*args,**kwargs): raise AssertionError('offline_network_forbidden')
socket.socket.connect=forbidden
socket.create_connection=forbidden
config.load_zhipu_settings=lambda: NS(model='glm-5.3',api_key='OFFLINE_FIXTURE',base_url='https://open.bigmodel.cn/api/paas/v4')
raw=ClosableStream([chunk(model='glm-5.3',reasoning='PRIVATE_FIXTURE'),
    chunk(model='glm-5.3',tool_calls=[tool_fragment(index=0,call_id='synthetic-tool',call_type='function',name='submit_report_review',
        arguments='{"score":96,"verdict":"pass","issues":[],"issue_resolutions":[],"advisories":[]}')],finish_reason='tool_calls'),
    chunk(model='glm-5.3',raw_usage=usage())])
client=FakeClient(raw)
original=client.completions.create
def create(**kwargs):
    hook=client.hook
    hook(NS(extensions={}))
    (Path(sys.argv[sys.argv.index('--worker')+1])/'sdk-fixture.json').write_text(json.dumps(kwargs),encoding='utf-8')
    return original(**kwargs)
client.completions.create=create
def close(): assert raw.closed
client.close=close
def factory(**kwargs):
    client.hook=kwargs['http_client']._event_hooks['request'][0]
    return client
openai.OpenAI=factory
from scripts.document_semantic_request import main
main()
'''


@pytest.mark.parametrize('variant_index',[0,1,2])
@pytest.mark.parametrize('tool_stream',[True,False])
def test_real_child_cli_sdk_assembly_and_owned_close(prepared,tmp_path,monkeypatch,variant_index,tool_stream):
    request=prepared[1][variant_index][2]
    bridge=identity.isolated_bridge()
    original=subprocess.Popen
    def child(command,**kwargs):
        assert command[command.index('-m')+1] == 'scripts.document_semantic_request'
        index=command.index('-m')
        command=[*command[:index],'-c',CHILD,*command[index+2:]]
        return original(command,**kwargs)
    monkeypatch.setattr(bridge.subprocess,'Popen',child)
    provider=bridge.GoldenProcessStreamProvider(settings=NS(model='glm-5.3',api_key='OFFLINE_FIXTURE',
        base_url='https://open.bigmodel.cn/api/paas/v4'),directory=tmp_path,
        transport_id=identity.TRANSPORT,stream_tool_arguments=tool_stream)
    response=provider.chat(request)
    assert response.model == 'glm-5.3' and response.reasoning_content == 'PRIVATE_FIXTURE'
    stream=tmp_path/'stream-001'
    assert runner.read(stream/'progress.json')['state'] == 'complete'
    assert runner.read(stream/'progress.json')['close_state'] == 'closed'
    assert runner.read(stream/'result.json')['transport_id'] == identity.TRANSPORT
    assert runner.read(stream/'reservation.json')['request_sha256'] == identity.request_sha(request)
    sdk=runner.read(stream/'sdk-fixture.json')
    assert sdk['messages'][0]['content'] == request.messages[0].content
    assert sdk['model'] == 'glm-5.3' and sdk['max_tokens'] == 32768
    assert sdk['temperature'] == 1 and sdk['top_p'] == .95
    assert sdk['stream_options'] == {'include_usage':True}
    assert 'metadata' not in sdk


class OfflineProvider:
    def __init__(self, failure=None):
        self.calls=[]
        self.failure=failure

    def chat(self,request,directory):
        directory.mkdir()
        raw=identity.request_bytes(request)
        (directory/'issued-request.json').write_bytes(raw)
        self.calls.append(request)
        bridge=identity.isolated_bridge()
        stream=directory/'stream-001'
        stream.mkdir()
        write_new_json(stream/'reservation.json',dict(transport_id=identity.TRANSPORT,ordinal=1,
            request_sha256=prep.sha(raw),stream_tool_arguments=True,state='reserved_before_io',
            request_metrics=bridge.request_metrics(request,raw),model='glm-5.3',
            thinking_profile_id=bridge.transport_profile(identity.TRANSPORT).profile_id))
        if self.failure == 'transport' and len(self.calls)==2:
            write_new_json(stream/'progress.json',bridge.TimedReviewBridgeObservation(
                state='failed',http_requests=1,input_tokens=None,output_tokens=None).model_dump())
            write_new_json(stream/'result.json',dict(state='failed',transport_id=identity.TRANSPORT,elapsed_ms=10,body_free=True))
            raise ValueError('semantic_synthetic_transport_failure')
        args=dict(score=96,verdict='pass',issues=[],issue_resolutions=[],advisories=[])
        response=ChatResponse(provider='zhipu',model='glm-5.3',content=None,reasoning_content='PRIVATE_FIXTURE',
            finish_reason='tool_calls',usage=TokenUsage(20,10),
            tool_calls=(ToolCall(id='synthetic',name='submit_report_review',arguments=args),))
        (directory/'raw-response.json').write_bytes(RESPONSE.dump_json(response))
        write_new_json(stream/'result.json',dict(state='complete',transport_id=identity.TRANSPORT,elapsed_ms=10,body_free=True))
        write_new_json(stream/'progress.json',bridge.TimedReviewBridgeObservation(
            state='complete',close_state='closed',http_requests=1,
            input_tokens=20,output_tokens=10,error=None).model_dump())
        write_new_json(directory/'receipt.json',transport.validate_complete(directory,request,response))
        return response


class OfflineNativeHost:
    def __init__(self,plan,directory,fault=None):
        self.plan,self.directory,self.fault=plan,directory,fault
        self.turns=[]
        self.source=CodexHostReviewEventSource(NS(request=self.native_read),plan)

    def native_read(self,method,params):
        assert params['threadId'] == 'synthetic-child'
        if method == 'thread/read':
            return dict(thread=dict(id='synthetic-child',parentThreadId='synthetic-root',
                source=dict(subAgent=dict(thread_spawn=dict(parent_thread_id='synthetic-root')))))
        return dict(data=deepcopy(self.turns),nextCursor=None)

    def adjudicate(self,directory,key,seconds):
        folder=directory/key.replace(':','-')
        pin=digest((folder/'task-checkpoint.json').read_bytes())
        _,task=read_checkpoint(folder/'task-checkpoint.json',pin)
        bound=task['binding']
        stage=runner.read(folder/'stage.json')
        index=len(self.turns)+1
        if self.fault == 'abort' and index==2:
            runner.abort(directory,key,'routing_failure')
            return runner.wait_reviews(directory,key,1)
        def notes(role):
            accepted=not(index==2 and role=='independent')
            return dict(stage_assessment=dict(stage=bound['stage'],stage_sha256=stage_identity(stage),
                reviewer=self.plan['review_principals'][role]['principal_id'],source_review='OFFLINE fixture only',
                accepted=accepted,defects=[] if accepted else [dict(kind='false_positive',detail='synthetic disagreement')]),
                report_assessment=None if bound['stage']=='initial' else dict(report_sha256=bound['report_sha256'],
                    reviewer=self.plan['review_principals'][role]['principal_id'],source_review='OFFLINE corrected report',
                    facts_and_sources_correct=True,correct_content_preserved=True,
                    identity_and_goal_preserved=True,true_errors_fixed=True))
        review=dict(binding=bound,**notes('independent'))
        turn=dict(id=f'turn-{index}',status='completed',itemsView='full',error=None,items=[
            dict(id=f'dispatch-{index}',type='userMessage',content=[dict(type='text',text=json.dumps(task))]),
            dict(id=f'final-{index}',type='agentMessage',phase='final_answer',
                text=json.dumps(dict(binding=bound,review=review)))])
        self.turns.insert(0,turn)
        if self.fault == 'native' and index==2:
            turn['items'].append(deepcopy(turn['items'][0]))
        if self.fault == 'checkpoint' and index==2:
            (folder/'independent-task.json').write_text('{}')
        runner.submit(directory,key,notes('primary'),f'synthetic-child/turn-{index}/final-{index}',
            self.source,folder/'task-checkpoint.json',pin)
        return runner.read(folder/'review-submission.json')


def setup_run(tmp_path,monkeypatch,prepared):
    plan,rows=deepcopy(prepared)
    monkeypatch.setattr(prep,'prepare',lambda *args,**kwargs:(deepcopy(plan),rows))
    write_new_json(tmp_path/'plan.json',dict(preparation_plan=plan,
        plan_sha256=prep.sha(prep.options.canonical(plan)),execution_head='f'*40,ci_run='synthetic-ci'))
    now=datetime.now(timezone.utc)
    write_new_json(tmp_path/'authorization.json',dict(version=runner.AUTH_VERSION,authorized=True,
        user_instruction='OFFLINE authorization fixture',plan_sha256=prep.sha(prep.options.canonical(plan)),
        budget=plan['budget'],head='f'*40,ci_run='synthetic-ci',issued_at=now.isoformat(),
        expires_at=(now+timedelta(hours=24)).isoformat()))
    write_new_json(tmp_path/'execution-preflight.json',dict(verified=True,root_thread_id='synthetic-root',
        independent_thread_id='synthetic-child',independent_agent_path='/root/synthetic',
        input_readability=dict(thread_id='synthetic-child',turn_id='synthetic-turn',dispatch_id='synthetic-dispatch',
            current_input_readable=True,future_input_guaranteed=False,current_route_and_final_available=True,
            host_review_evidence_policy=plan['host_review_evidence_policy'])))
    return plan,rows


@pytest.mark.parametrize('fault',[None,'abort','transport','native','checkpoint'])
def test_fifteen_once_semantic_continue_hard_stop_and_strict_seal(prepared,tmp_path,monkeypatch,fault):
    plan,rows=setup_run(tmp_path,monkeypatch,prepared)
    provider=OfflineProvider(fault)
    host=OfflineNativeHost(plan,tmp_path,fault)
    result=runner.observe(tmp_path,plan,rows,provider,host.source,adjudicate=host.adjudicate)
    if fault is None:
        assert result['scan_completed'] and len(provider.calls)==15, result
        assert len(result['completed'])==15 and result['completed'][1]['host_disagreement']
        assert not result['completed'][1]['semantic_accepted']
        assert runner.replay(tmp_path,event_source=host.source)['native_reviews']==15
        before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
        output=tmp_path.parent/(tmp_path.name+'-seal.json')
        assert runner.seal(tmp_path,output,event_source=host.source)['native_reviews']==15
        assert before == {str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
        assert 'PRIVATE_FIXTURE' not in output.read_text()
        with pytest.raises(FileExistsError):
            runner.seal(tmp_path,output,event_source=host.source)
    else:
        assert not result['scan_completed'] and len(provider.calls)==2, result
        assert len(result['completed'])==1 and len(result['unexecuted'])==13
        assert result['first_deviation']['key']==rows[1][0]['key']
        if fault in ('abort','transport'):
            assert runner.replay(tmp_path,event_source=host.source)['native_reviews']==1
        if fault=='transport':
            assert result['accounting']['known_tokens']==30
            assert result['accounting']['unknown_usage_calls']==1 and result['accounting']['receiptless_calls']==1


def test_authorization_budget_head_expiry_and_no_cost_reauthorization(prepared):
    plan,_=prepared
    now=datetime.now(timezone.utc)
    auth=dict(version=runner.AUTH_VERSION,authorized=True,user_instruction='用户继续本轮具体成本方案',
        plan_sha256=prep.sha(prep.options.canonical(plan)),budget=deepcopy(plan['budget']),
        head='f'*40,ci_run='ci',expires_at=(now+timedelta(hours=24)).isoformat())
    auth['issued_at']=now.isoformat()
    runner.check_authorization(auth,plan,'f'*40,'ci',now=now)
    for changed in (dict(auth,head='e'*40),dict(auth,budget={}),
            dict(auth,expires_at=(now-timedelta(seconds=1)).isoformat())):
        with pytest.raises(ValueError,match='authorization_invalid'):
            runner.check_authorization(changed,plan,'f'*40,'ci',now=now)


@pytest.mark.parametrize('fault',['receipt','source','orphan','outcome','native','phase','missing-failure','clock','worker-failure','negative-usage','rogue-progress'])
def test_closed_replay_rejects_crossbindings_tamper_and_invented_native(prepared,tmp_path,monkeypatch,fault):
    plan,rows=setup_run(tmp_path,monkeypatch,prepared)
    provider=OfflineProvider()
    host=OfflineNativeHost(plan,tmp_path,'abort')
    runner.observe(tmp_path,plan,rows,provider,host.source,adjudicate=host.adjudicate)
    folder=tmp_path/rows[0][0]['key'].replace(':','-')
    if fault=='receipt':
        value=runner.read(folder/'transport/receipt.json'); value['request_sha256']='0'*64
        (folder/'transport/receipt.json').write_text(json.dumps(value))
    elif fault=='source':
        (folder/'material.json').write_bytes(b'{}')
    elif fault=='outcome':
        value=runner.read(folder/'cell-result.json');value['semantic_accepted']=True
        (folder/'cell-result.json').write_text(json.dumps(value))
    elif fault=='native':
        host.turns[0]['items'][1]['text']+=' '
    elif fault=='phase':
        value=runner.read(tmp_path/'failure.json');value['phase']='before_send'
        (tmp_path/'failure.json').write_text(json.dumps(value))
        result=runner.read(tmp_path/'result.json');result['first_deviation']=value
        (tmp_path/'result.json').write_text(json.dumps(result))
    elif fault=='missing-failure':
        (tmp_path/'failure.json').unlink()
        result=runner.read(tmp_path/'result.json');result['first_deviation']=None
        (tmp_path/'result.json').write_text(json.dumps(result))
    elif fault=='clock':
        for p in (tmp_path/'development-host-clock').glob('*-*.json'):
            p.unlink()
        result=runner.read(tmp_path/'result.json')
        result['timing'].update(host_elapsed_seconds=0,completed_host_waits=0,
            active_elapsed_seconds=result['timing']['wall_elapsed_seconds'])
        (tmp_path/'result.json').write_text(json.dumps(result))
    elif fault=='worker-failure':
        write_new_json(folder/'transport/stream-001/failure.json',dict(category='worker_failed',assembly_code=None,provider_code=None))
    elif fault=='negative-usage':
        p=folder/'transport/stream-001/progress.json';value=runner.read(p);value['input_tokens']=-5
        p.write_text(json.dumps(value))
    elif fault=='rogue-progress':
        (tmp_path/'unexpected').mkdir()
        write_new_json(tmp_path/'unexpected/progress.json',dict(reasoning_content='PRIVATE_FIXTURE'))
    else:
        (tmp_path/'orphan.json').write_text('{}')
    with pytest.raises(ValueError):
        runner.seal(tmp_path,tmp_path.parent/(tmp_path.name+'-seal.json'),event_source=host.source)


def test_abort_during_native_validation_stops_before_next_send(prepared,tmp_path,monkeypatch):
    plan,rows=setup_run(tmp_path,monkeypatch,prepared)
    host=OfflineNativeHost(plan,tmp_path)
    provider=OfflineProvider()
    original=runner.validate_submission
    def validation(directory,key,submission,source):
        value=original(directory,key,submission,source)
        if key==rows[1][0]['key'] and (directory/key.replace(':','-')/'review-submission.json').exists():
            runner.abort(directory,key,'operator_stop')
        return value
    monkeypatch.setattr(runner,'validate_submission',validation)
    result=runner.observe(tmp_path,plan,rows,provider,host.source,adjudicate=host.adjudicate)
    assert not result['scan_completed'] and len(provider.calls)==2
    assert len(result['completed'])==1


def test_slow_native_gate_cannot_spend_unreserved_active_time(prepared,tmp_path,monkeypatch):
    plan,rows=setup_run(tmp_path,monkeypatch,prepared)
    now=[0.]
    def clock(directory,**kwargs):
        return runner.DevelopmentHostClock(directory,wall_clock=lambda:now[0],**kwargs)
    def before():
        now[0]=8401.
    host=OfflineNativeHost(plan,tmp_path)
    provider=OfflineProvider()
    result=runner.observe(tmp_path,plan,rows,provider,host.source,adjudicate=host.adjudicate,
        before_send=before,clock_factory=clock)
    assert not provider.calls and result['accounting']['attempted_calls']==0
    assert result['first_deviation']['code']=='semantic_request_time_reservation'


@pytest.mark.parametrize('fault',['package','authorization','native'])
def test_execution_gates_precede_credentials_and_run_creation(prepared,tmp_path,monkeypatch,fault):
    plan,_=prepared
    package=tmp_path/'package';package.mkdir()
    write_new_json(package/'plan.json',dict(preparation_plan=plan,plan_sha256=prep.sha(prep.options.canonical(plan))))
    now=datetime.now(timezone.utc)
    auth=dict(version=runner.AUTH_VERSION,authorized=True,user_instruction='OFFLINE gate fixture',
        plan_sha256=prep.sha(prep.options.canonical(plan)),budget=plan['budget'],head='f'*40,
        ci_run='synthetic-ci',issued_at=now.isoformat(),expires_at=(now+timedelta(hours=24)).isoformat())
    if fault=='authorization':
        auth['budget']={}
    write_new_json(tmp_path/'authorization.json',auth)
    def package_gate(path):
        if fault=='package':raise ValueError('semantic_package_inventory_changed')
    monkeypatch.setattr(prep,'verify_package',package_gate)
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'verify_public_ci',lambda ci:'f'*40)
    monkeypatch.setattr(runner,'require_unchanged_checkout',lambda head:None)
    class Reader:
        def __init__(self,*args):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
    monkeypatch.setattr(runner,'CodexReadOnlyClient',Reader)
    def native(*args):raise ValueError('boundary_v2_native_lineage_mismatch')
    monkeypatch.setattr(runner,'verify_native_principals',native)
    def secret(*args):raise AssertionError('credentials_must_not_be_read')
    monkeypatch.setattr(runner,'load_role_settings',secret)
    args=NS(package=package,authorization=tmp_path/'authorization.json',ci_run='synthetic-ci',
        codex_executable='OFFLINE_NOT_LAUNCHED',env_file='OFFLINE_NOT_READ')
    expected={'package':'semantic_package_inventory_changed',
        'authorization':'semantic_authorization_invalid_or_expired',
        'native':'boundary_v2_native_lineage_mismatch'}[fault]
    with pytest.raises(ValueError,match='^'+expected+'$'):runner.run(args)
    assert not (tmp_path/'data/runs/model_comparison'/plan['run_id']).exists()
