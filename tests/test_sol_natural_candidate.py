"""Actual application and owned Sol worker, scripted HTTP only; no quality claim."""
from dataclasses import replace
import json
from pathlib import Path
import socket
import sys

import pytest
from app.evaluation import sol_natural_contract as contract
from app.evaluation import natural_duty_contract as legacy
from app.product.natural_duty_candidate import build_natural_duty_candidate
from app.runtime.sol_natural_provider import SolNaturalProvider, SolReviewProvider
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.store import RuntimeTraceStore
from app.product.run_receipts import FileRunReceiptStore
from scripts.reviewer_responses_process import run_once
from tests.test_natural_duty_candidate import Responses, run
from tests.test_native_editor_product_budget import SummaryBuilder

CHILD = r'''
import json,socket
from pathlib import Path
import httpx
from scripts import reviewer_responses_nonstream as codec, reviewer_responses_process as process
from app.evaluation import sol_natural_contract as contract, natural_duty_contract as legacy
from tests.test_natural_duty_candidate import Responses
from tests.test_reviewer_responses_nonstream import response
def deny(*args,**kwargs): raise AssertionError('network forbidden')
socket.socket = socket.create_connection = deny
original=codec.collect
def collect(business,**kwargs):
    directory=Path(kwargs['observation_dir']).parent
    context=process.read_json(directory/'validation-context.json')
    request=legacy.make_request(contract.restore_context(context),context['duty'],context['stage'])
    scripted=Responses(reviewer=True,mode=MODE)
    result=scripted.chat(request)
    value=response(dict(result.tool_calls[0].arguments))
    if MODE == 'non_tool':
        value['output'] = [dict(type='message', status='completed',
            content=[dict(type='output_text', text='OFFLINE_TEXT_ONLY', annotations=[])])]
    if MODE == 'wrong_model':
        value['model'] = 'offline-other-model'
    if MODE == 'reasoning_conflict':
        value['reasoning'] = dict(effort='low')
    status=STATUS
    return original(business,**kwargs,transport=httpx.MockTransport(lambda request:httpx.Response(status,
        stream=httpx.ByteStream(json.dumps(value if status==200 else {'error':'timeout'}).encode()),
        headers={'content-type':'application/json'})))
codec.collect=collect
process.worker()
'''


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*a, **k):
        raise AssertionError('network forbidden')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)


def application(tmp_path, *, mode='repair', statuses=()):
    attempts = []

    def sender(business, **kwargs):
        status = statuses[len(attempts)] if len(attempts) < len(statuses) else 200
        attempts.append(status)
        command = [sys.executable, '-c', 'MODE='+repr(mode)+'\nSTATUS='+str(status)+'\n'+CHILD]
        return run_once(business, **kwargs, command=command)

    class Factory:
        def __init__(self):
            self.providers = {}
            self.descriptor = self.make('_identity_only')

        def make(self, name):
            folder = tmp_path/'transport'/name
            return SolNaturalProvider(Responses(), SolReviewProvider(api_key='OFFLINE_SENTINEL',
                directory=folder/'review', task_directory=folder, sender=sender))

        def __call__(self, run_id):
            self.providers[run_id] = self.make(run_id)
            return self.providers[run_id]

    factory = Factory()
    app = build_natural_duty_candidate(summary_builder=SummaryBuilder(factory.descriptor.generator.req.player_summary),
        provider_factory=factory, knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path/'reports', candidate=contract)
    flows=[]
    original=app._runtime._execution_factory._review_workflow_factory
    def capture(runtime,budget):
        flow=original(runtime,budget);flows.append(flow);return flow
    app._runtime._execution_factory._review_workflow_factory=capture
    return app, factory, flows, attempts


@pytest.mark.parametrize('mode,calls,outcome', [('repair',6,'candidate_repaired_pass_unqualified'),
    ('pass',4,'candidate_initial_pass_unqualified'), ('bad_anchor',4,'candidate_execution_failed'),
    ('fresh_reject',5,'fresh_facts_rejected')])
def test_full_application_with_owned_workers(tmp_path,mode,calls,outcome):
    app,f,flows,attempts=application(tmp_path,mode=mode)
    result=run(app)
    assert flows[0].outcome==outcome
    assert flows[0].send.provider.calls==calls
    assert len(attempts)==calls-2
    assert result.publication_status.value=='rejected'
    trace=RuntimeTraceStore(tmp_path/'reports','candidate').read_trace(result.trace_reference)
    assert trace.identity.coach_contract==contract.CONTRACT.snapshot()
    assert trace.identity.provider_id==contract.PROVIDER
    assert trace.usage.provider_calls_attempted==calls
    if mode=='repair':
        records=[json.loads(p.read_text(encoding='utf-8')) for p in
            (tmp_path/'transport/candidate/review').glob('call-*/validation-context.json')]
        fresh=[r for r in records if r['stage']=='fresh']
        assert len(fresh)==2 and fresh[0]['report']==fresh[1]['report']==flows[0].assembly.report
        assert all(r['report']!=fresh[0]['report'] for r in records if r['stage']=='initial')


def test_timeout_retries_only_current_stage_and_preserves_unknown(tmp_path):
    app,f,flows,attempts=application(tmp_path,statuses=(524,))
    result=run(app)
    assert attempts==[524,200,200,200,200]
    assert flows[0].outcome=='candidate_repaired_pass_unqualified'
    budget=flows[0].send.provider
    assert budget.calls==7 and budget.reserved_tokens>0
    assert len(f.providers['candidate'].generator.requests)==2
    assert len(list((tmp_path/'transport/candidate/review').glob('call-*/receipt.json')))==5
    assert result.publication_status.value=='rejected'


def test_second_timeout_does_not_loop_or_erase_first(tmp_path):
    app,f,flows,attempts=application(tmp_path,statuses=(524,524))
    run(app)
    assert attempts==[524,524]
    assert flows[0].outcome=='candidate_execution_failed'
    assert flows[0].send.provider.calls==4
    assert flows[0].send.provider.reserved_tokens>0


def test_dynamic_context_rejects_mutated_report_before_io(tmp_path):
    from app.evaluation.golden_native_issues_review import build_inputs
    from scripts.prepare_reviewer_profile_screen import visible,json_value
    from scripts.reviewer_responses_transport import Profile
    request=contract.make_request(build_inputs(Responses().req),'facts')
    context=dict(request.metadata[contract.CONTEXT],report='wrong report')
    with pytest.raises(ValueError):
        run_once(visible(json_value(request)),profile=Profile(group='GPT-pro',route='proxy-12000'),
            api_key='OFFLINE_SENTINEL',directory=tmp_path/'call',response_mode='natural-sol-v1',validation_context=context)
    assert not (tmp_path/'call').exists()


@pytest.mark.parametrize('status', [401, 400])
def test_nontransient_http_failure_never_retries(tmp_path, status):
    app,f,flows,attempts=application(tmp_path,statuses=(status,))
    run(app)
    assert attempts == [status]
    assert flows[0].outcome == 'candidate_execution_failed'
    assert not (tmp_path/'transport/candidate/retry-decision.json').exists()


def test_flash_reaped_timeout_retries_same_request_and_retains_reservation(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from app.evaluation import golden_stream_bridge as bridge
    from app.runtime.sol_natural_provider import SolNaturalProviderFactory
    from app.runtime.coach_budget import CoachBudgetedProvider
    from tests.test_natural_duty_transport import generation, scripted_child
    sent = []
    supervisor = bridge.run_child
    success = scripted_child(sent)

    def child(command, raw, **kwargs):
        if not sent:
            sent.append(raw)
            # A real owned subprocess is killed and reaped by the existing supervisor.
            return supervisor([sys.executable, '-c', 'import time; time.sleep(10)'], raw,
                directory=kwargs['directory'], timeout_s=.05, transport_id=kwargs['transport_id'])
        return success(command, raw, **kwargs)

    monkeypatch.setattr(bridge, 'run_child', child)
    router = SolNaturalProviderFactory(generator_settings=SimpleNamespace(model='glm-5.3-flash',
        api_key='OFFLINE_SENTINEL', base_url='https://open.bigmodel.cn/api/paas/v4'),
        api_key='OFFLINE_SENTINEL', transport_root=tmp_path)('candidate')
    budget = CoachBudgetedProvider(router, coach_contract=contract.CONTRACT)
    response = budget.chat(generation())
    assert response.model == 'glm-5.3-flash'
    assert budget.calls == 2 and budget.tokens == 30 and budget.reserved_tokens > 0
    assert router._logical == {'generation': 1, 'review': 0}
    assert json.loads(sent[0]) == json.loads(sent[1])
    assert json.loads((tmp_path/'candidate/generation/stream-001/result.json').read_bytes())['state'] == 'deadline'
    assert (tmp_path/'candidate/generation/stream-002/result.json').exists()


def test_changed_timeout_evidence_forbids_retry(tmp_path):
    from app.evaluation.golden_native_issues_review import build_inputs
    from app.providers.errors import ProviderResponseError
    app,f,flows,attempts=application(tmp_path,statuses=(524,))
    router=f('isolated')
    request=contract.make_request(build_inputs(Responses().req),'facts')
    with pytest.raises(ProviderResponseError) as caught:
        router.chat(request)
    path=tmp_path/'transport/isolated/review/call-001/observation/observation.json'
    path.write_text('{}', encoding='utf-8')
    assert not router.prepare_retry(caught.value, request)
    assert attempts == [524]


@pytest.mark.parametrize('worker_code', ['business_contract_invalid', 'non_tool_output', 'model_identity',
    'http_status_401', 'ok'])
def test_persisted_worker_result_takes_precedence_over_supervisor_deadline(tmp_path, worker_code):
    from app.evaluation.golden_native_issues_review import build_inputs
    from app.providers.errors import ProviderResponseError
    from app.runtime.coach_budget import CoachBudgetedProvider

    app, factory, flows, attempts = application(tmp_path)
    router = factory('deadline')
    sent = []
    child = '''
import json,sys,time
from pathlib import Path
payload=json.load(sys.stdin)
Path(payload['directory'], 'worker-result.json').write_text(
    json.dumps(dict(ok=WORKER_CODE == 'ok', code=WORKER_CODE)), encoding='utf-8')
time.sleep(30)
'''

    def sender(business, **kwargs):
        sent.append(business)
        return run_once(business, **kwargs, command=[sys.executable, '-c',
            'WORKER_CODE='+repr(worker_code)+'\n'+child])

    router.reviewer.sender = sender
    request = replace(contract.make_request(build_inputs(Responses().req), 'facts'), timeout_s=1)
    budget = CoachBudgetedProvider(router, coach_contract=contract.CONTRACT)
    with pytest.raises(ProviderResponseError):
        budget.chat(request)
    receipt = json.loads((tmp_path/'transport/deadline/review/call-001/receipt.json').read_bytes())
    assert receipt['code'] == 'deadline_exceeded' and receipt['worker_code'] == worker_code
    assert receipt['reaped'] is True and len(sent) == budget.calls == 1
    assert not (tmp_path/'transport/deadline/retry-decision.json').exists()


def test_known_usage_from_structural_failure_is_counted_without_retry(tmp_path):
    app,f,flows,attempts=application(tmp_path,mode='non_tool')
    result=run(app)
    assert attempts == [200]
    assert flows[0].outcome == 'candidate_execution_failed'
    budget=flows[0].send.provider
    assert budget.calls == 3 and budget.reserved_tokens == 0 and budget.tokens >= 20
    receipt=json.loads(next((tmp_path/'transport/candidate/review').glob('call-*/receipt.json')).read_bytes())
    assert receipt['worker_code'] == 'non_tool_output' and receipt['usage_state'] == 'known'
    trace=RuntimeTraceStore(tmp_path/'reports','candidate').read_trace(result.trace_reference)
    assert trace.usage.provider_calls_attempted == 3
    assert trace.usage.input_tokens + trace.usage.output_tokens == budget.tokens
    failed = [e.signal for e in trace.events if e.signal.kind == 'provider_call_failed_usage']
    assert len(failed) == 1 and failed[0].input_tokens == 12 and failed[0].output_tokens == 8


@pytest.mark.parametrize('evidence', ['missing', 'malformed', 'empty', 'valid', 'body_complete'])
def test_supervisor_deadline_requires_valid_observation_before_retry(tmp_path, evidence):
    from app.evaluation.golden_native_issues_review import build_inputs
    from app.providers.errors import ProviderResponseError
    app,f,flows,attempts=application(tmp_path)
    router=f('deadline-observation')
    child='''
import json,sys,time
from pathlib import Path
payload=json.load(sys.stdin)
directory=Path(payload['directory'])/'observation'
if EVIDENCE == 'body_complete':
    import socket,httpx
    from openai import OpenAI
    from scripts.reviewer_responses_nonstream import collect
    from scripts.reviewer_responses_transport import Profile
    def deny(*args, **kwargs): raise AssertionError('network forbidden')
    socket.socket=socket.create_connection=deny
    def stalled_close(self): time.sleep(30)
    OpenAI.close=stalled_close
    collect(payload['business'],profile=Profile(**payload['profile']),api_key='OFFLINE_SENTINEL',
        observation_dir=directory,timeout_s=payload['timeout_s'],transport=httpx.MockTransport(
            lambda request:httpx.Response(200,stream=httpx.ByteStream(b'not json'),
                headers={'content-type':'application/json'})))
elif EVIDENCE == 'valid':
    import httpx
    from scripts.stream_observation import StreamObservation
    observer=StreamObservation(directory)
    observer.on_request(httpx.Request('POST', 'https://offline.invalid'))
    observer._save()
elif EVIDENCE != 'missing':
    directory.mkdir()
    (directory/'observation.json').write_text('not json' if EVIDENCE == 'malformed' else '{}', encoding='utf-8')
time.sleep(30)
'''
    def sender(business, **kwargs):
        return run_once(business, **kwargs, command=[sys.executable, '-c',
            'EVIDENCE='+repr(evidence)+chr(10)+child])
    router.reviewer.sender=sender
    request=replace(contract.make_request(build_inputs(Responses().req),'facts'),
        timeout_s=5 if evidence == 'body_complete' else 1)
    with pytest.raises(ProviderResponseError) as caught:
        router.chat(request)
    receipt=json.loads((tmp_path/'transport/deadline-observation/review/call-001/receipt.json').read_bytes())
    assert receipt['code'] == 'deadline_exceeded' and receipt['reaped'] is True
    if evidence == 'body_complete':
        observed=json.loads((tmp_path/'transport/deadline-observation/review/call-001/observation/observation.json').read_bytes())
        assert observed['response_status'] == 200 and observed['eof'] is True
        assert 'response_contract' not in observed and receipt['worker_code'] is None
    assert router.prepare_retry(caught.value, request) is (evidence == 'valid')
    assert len(list((tmp_path/'transport/deadline-observation/review').glob('call-*'))) == 1


def test_wrong_model_usage_is_retained_but_not_attributed_to_sol(tmp_path):
    app,f,flows,attempts=application(tmp_path,mode='wrong_model')
    result=run(app)
    assert attempts == [200] and flows[0].outcome == 'candidate_execution_failed'
    budget=flows[0].send.provider
    receipt=json.loads(next((tmp_path/'transport/candidate/review').glob('call-*/receipt.json')).read_bytes())
    assert receipt['worker_code'] == 'model_identity' and receipt['usage_state'] == 'known'
    assert receipt['usage']['total_tokens'] == 20 and budget.reserved_tokens > 0
    trace=RuntimeTraceStore(tmp_path/'reports','candidate').read_trace(result.trace_reference)
    assert trace.usage.observed_input_tokens + trace.usage.observed_output_tokens == budget.tokens
    assert trace.usage.input_tokens is None and trace.usage.output_tokens is None
    assert not [e for e in trace.events if e.signal.kind == 'provider_call_failed_usage']
    assert not (tmp_path/'transport/candidate/retry-decision.json').exists()


@pytest.mark.parametrize('fault,known', [('worker_identity', False), ('missing_identity', False),
    ('usage_conflict', False), ('checkpoint_missing', True), ('worker_missing', True)])
def test_failure_usage_requires_matching_persisted_model_evidence(tmp_path, fault, known):
    from app.evaluation.golden_native_issues_review import build_inputs
    from app.providers.errors import ProviderResponseError
    from app.runtime.coach_budget import CoachBudgetedProvider
    app,f,flows,attempts=application(tmp_path,mode='non_tool')
    router=f('identity')
    original=router.reviewer.sender
    def sender(business, **kwargs):
        receipt=original(business, **kwargs)
        directory=kwargs['directory']
        if fault == 'checkpoint_missing':
            (directory/'usage.json').unlink()
        elif fault == 'worker_missing':
            (directory/'worker-result.json').unlink()
        else:
            path=directory/('observation/observation.json' if fault == 'missing_identity' else 'worker-result.json')
            value=json.loads(path.read_text(encoding='utf-8'))
            if fault == 'missing_identity':
                value.pop('response_contract')
            elif fault == 'worker_identity':
                value['response_observation']['model_matches']=False
            else:
                value['usage']['input_tokens']+=1
                value['usage']['total_tokens']+=1
            path.write_text(json.dumps(value, ensure_ascii=True), encoding='utf-8')
        return receipt
    router.reviewer.sender=sender
    budget=CoachBudgetedProvider(router, coach_contract=contract.CONTRACT)
    request=contract.make_request(build_inputs(Responses().req),'facts')
    with pytest.raises(ProviderResponseError) as caught:
        budget.chat(request)
    assert attempts == [200] and budget.calls == 1
    assert budget.tokens == (20 if known else 0)
    assert (budget.reserved_tokens == 0) is known
    assert hasattr(caught.value, 'observed_usage') is known
    if known:
        path=tmp_path/'transport/identity/review/call-001/observation/observation.json'
        path.write_text('{}', encoding='utf-8')
        assert router.failure_usage(caught.value, router.reviewer.last_failure['request']) is None


@pytest.mark.parametrize('exhaustion', ['time', 'tokens'])
def test_retry_cannot_exceed_shared_budget(tmp_path, exhaustion):
    from app.evaluation.golden_native_issues_review import build_inputs
    from app.providers.errors import ProviderError
    from app.runtime.coach_budget import CoachBudgetedProvider
    app,f,flows,attempts=application(tmp_path,statuses=(524,))
    router=f('budget')
    now=[0.0]
    budget=CoachBudgetedProvider(router, coach_contract=contract.CONTRACT, clock=lambda:now[0])
    send=router.reviewer.sender
    def limited(*args, **kwargs):
        receipt=send(*args, **kwargs)
        if exhaustion == 'time':
            now[0]=1200
        else:
            budget.tokens=contract.CONTRACT.descriptor()['total_tokens']
        return receipt
    router.reviewer.sender=limited
    with pytest.raises(ProviderError):
        budget.chat(contract.make_request(build_inputs(Responses().req),'facts'))
    assert attempts == [524] and budget.calls == 1 and budget.stopped
