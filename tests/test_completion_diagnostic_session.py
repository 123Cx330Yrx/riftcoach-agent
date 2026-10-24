"""Real worker/SDK with synthetic HTTP/native events; no semantic admission."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import socket
import sys

import pytest

from app.evaluation import completion_diagnostic_session as engine
from app.evaluation import sol_completion_contract as contract, sol_necessity_contract as old
from app.evaluation.sol_natural_session import CandidateSession, SessionPaused, SessionBlocked, canonical, digest, tree
from app.evaluation.sol_session_review import SessionReviewGate
from app.evaluation.golden_stream_bridge import RESPONSE
from app.providers.models import ChatResponse, TokenUsage, ToolCall
from app.providers.errors import ProviderResponseError
from app.runtime.sol_natural_provider import SolReviewProvider, SolNaturalProvider
from scripts.host_review_workspace import HostReviewWorkspace
from scripts.prepare_reviewer_profile_screen import visible, json_value
from scripts.reviewer_responses_process import run_once
from scripts.reviewer_profile_batch import inventory
from scripts.review_completion_necessity_candidate import materials
from scripts import review_duty_direct_patch as direct
from tests.test_sol_session_review import controls, author
from tests.test_natural_duty_candidate import Responses


def opinion(context):
    inputs = (old.restore_context(context) if context['version'] == old.VERSION
              else contract.restore_context(context))
    value = dict(score=95, verdict='pass', issues=[], issue_resolutions=[], advisories=[])
    if context['stage'] == 'fresh':
        return value
    value['repairs'] = []
    if context.get('control_case') == 'b':
        return value
    request = old.make_request(inputs, context['duty'])
    content = next(m.content for m in request.messages if (m.content or '').startswith('[UNTRUSTED DATA]\n'))
    root = json.loads(content.split('\n',1)[1].rsplit('\n[END UNTRUSTED DATA]',1)[0])['source_roots']['roots'][0][0]
    block, before, after = 18, '禁用率 3%', '禁用率 4%'
    if context['duty'] == 'completion':
        block = 21 if context.get('control_case') in ('c', 'd') else 18
        before = inputs.source.blocks[block-1][1].splitlines()[-1][-12:]
        after = before+' OFFLINE fixture action.'
    value.update(score=70, verdict='needs_revision', issues=[dict(block=block, source_ids=[root],
        severity='medium', category='fact_error', explanation='Synthetic test only.',
        suggested_correction='Synthetic exact change.')], repairs=[dict(issue_ids=[1], edits={
            f'block_{block}':[dict(before=before, after=after, reason='Synthetic test only.') ]})])
    direct.validate(json.dumps(value, ensure_ascii=False), inputs, context['duty'])
    return value


WORKER = r'''
import json,socket
from pathlib import Path
import httpx
from scripts import reviewer_responses_nonstream as codec, reviewer_responses_process as process
from tests.test_completion_diagnostic_session import opinion
from tests.test_reviewer_responses_nonstream import response
def deny(*a,**k): raise AssertionError('network forbidden')
socket.socket=socket.create_connection=deny
original=codec.collect
def collect(business,**kwargs):
    folder=Path(kwargs['observation_dir']).parent
    context=process.read_json(folder/'validation-context.json')
    value=response(opinion(context))
    if MODE=='text':
        value['output']=[dict(type='message',status='completed',content=[dict(type='output_text',text='OFFLINE',annotations=[])])]
    if MODE=='identity': value['model']='offline-wrong-model'
    return original(business,**kwargs,transport=httpx.MockTransport(lambda request:httpx.Response(STATUS,
        stream=httpx.ByteStream(json.dumps(value if STATUS==200 else {'error':'timeout'}).encode()),
        headers={'content-type':'application/json'})))
codec.collect=collect
process.worker()
'''


@pytest.fixture
def setup(tmp_path, monkeypatch):
    def deny(*a, **k):
        pytest.fail('unexpected real network/generation')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    opened, turns, _ = controls(tmp_path/'native')
    _, template = opened()
    review_plan, source = template.plan, template.native.event_source
    root = tmp_path/'parent'
    workspace = HostReviewWorkspace(cwd=Path.cwd(), python=sys.executable,
        answers=tmp_path/'parent-authors', evidence_roots=[root])
    inputs = materials()['a']
    issued = old.make_request(inputs, 'facts')
    issued = replace(issued, metadata={**issued.metadata, 'coach_budget_contract':'coach-bounded-review-v2'})
    raw = json.dumps(opinion(issued.metadata[old.CONTEXT]), ensure_ascii=False, separators=(',', ':'))
    response = ChatResponse(provider=old.REVIEW_PROVIDER, model=old.REVIEW_MODEL, content=None,
        tool_calls=(ToolCall(id='fixture-facts', name='submit_report_review', arguments=json.loads(raw)),),
        finish_reason='tool_calls', usage=TokenUsage(input_tokens=10, output_tokens=10))
    prior = dict(calls=3, router_calls=3, tokens=45060, reserved_tokens=0, retries=0,
        stopped=False, failed=False, logical=dict(generation=2, review=1),
        attempts=[dict(ordinal=n, role='generation' if n<3 else 'review', status='completed') for n in (1,2,3)])
    historical = deepcopy(prior)
    historical.update(calls=4, router_calls=4, tokens=66591, stopped=True, failed=True)
    historical['logical']['review'] = 2
    historical['attempts'].append(dict(ordinal=4, role='review', status='failed'))
    binding=dict(fixture_only=True, candidate_contract=old.VERSION, review_plan_sha256=digest(canonical(review_plan)))

    def parent_session(previous=None):
        s=CandidateSession(root/'execution/session', binding=binding,
            transport_root=root/'execution/transport/candidate', journal_root=root/'execution/journal',
            contract_module=old, before_new_model=lambda:None,
            guard_sha=previous.guard_sha if previous else None,
            checkpoint_sha=previous.checkpoint_sha if previous else None)
        return s, SessionReviewGate(s, plan=review_plan, workspace=workspace, event_source=source)

    first, gate = parent_session()
    material=dict(report=inputs.source.report, responses=[raw], request_raw=old.request_bytes(issued).decode(),
        complete_source=dict(data_json=inputs.data_json, pack_json=inputs.pack_json), duty='facts', stage='initial')
    with pytest.raises(SessionPaused), first:
        first.operation('model', {'fixture_generation':1}, lambda:dict(ok=True))
        for n in range(3):
            first.operation('tool', {'name':'knowledge.search','fixture':n}, lambda:dict(success=True))
        first.operation('model', {'fixture_generation':2}, lambda:dict(ok=True))
        first.operation('model', json_value(issued), lambda:dict(ok=True, issued_raw=old.request_bytes(issued).decode(),
            response_raw=RESPONSE.dump_json(response).decode(), budget=prior))
        def save():
            first.journal_root.mkdir()
            (first.journal_root/'facts-initial.json').write_bytes(canonical(dict(raw=raw)))
            return dict(recorded=True)
        first.operation('journal', {'name':'facts-initial'}, save)
        gate.require('facts-initial','opinion',material,inputs.source.report)
    second, gate = parent_session(first)
    with second:
        primary, event = author(list(gate.handles())[-1], turns, workspace)
        gate.submit('facts-initial', primary, event)
        second.cursor=7
        gate.require('facts-initial','opinion',material,inputs.source.report)
        second.operation('model', json_value(old.make_request(inputs,'completion')),
            lambda:dict(ok=False,error_code='sol_call_failed',budget=historical))
        second.operation('journal', {'name':'outcome'}, lambda:dict(recorded=True))
        second.close(dict(synthetic=True))
    (root/'plan.json').write_bytes(canonical(dict(run_id='candidate', review_plan=review_plan,
        cwd=str(Path.cwd()), python=sys.executable)))
    derived=deepcopy(historical)
    derived.update(stopped=False,failed=False)
    derived['logical']['review']=1
    result=dict(strict_replay=True, native_reviews=1, accounting={k:historical[k]
        for k in ('calls','tokens','reserved_tokens','retries')})
    roots=dict(guard=second.guard_sha,checkpoint=second.checkpoint_sha,authorization_sha='fixture')
    (root/'seal.json').write_bytes(canonical(dict(result=result,original_roots=roots,inventory=inventory(root))))
    proof=dict(version='completion-continuation-offline-v1',parent_operator=str(root),
        parent_inventory=inventory(root),parent_author_inventory=inventory(workspace.answers),
        parent_seal_sha256=digest((root/'seal.json').read_bytes()),strict_parent_replay=result,parent_roots=roots,
        original_native_review_replayed=True,provider_requests=0,key_reads=0,imported_operations=9,
        historical_budget=historical,derived_budget=derived,inherited_active_seconds=20,
        accepted_handle=list(gate.handles())[0],frontier=json_value(old.make_request(inputs,'completion')))
    proof_path=tmp_path/'parent-proof.json'
    proof_path.write_bytes(canonical(proof))
    spec=engine.parent_binding(proof_path,digest(proof_path.read_bytes()))
    return dict(spec=spec,source=source,turns=turns,root=tmp_path/'child',http=[],modes=[],
                before_count=0,stages=[],parent_inventory=inventory(root))


def drive(state, *, statuses=(), modes=(), reject=None, retry=False, previous=None, read_only=False):
    def before():
        state['before_count']+=1
    session,gate=engine.open_session(state['root'],state['spec'],state['source'],before_new_model=before,
        guard=previous.guard_sha if previous else None,checkpoint=previous.checkpoint_sha if previous else None,
        manual_retry=retry,read_only=read_only)
    def sender(business,**kwargs):
        index=len(state['http'])
        status=statuses[index] if index<len(statuses) else 200
        mode=modes[index] if index<len(modes) else 'valid'
        state['http'].append(status)
        command=[sys.executable,'-X','utf8','-c','STATUS='+str(status)+'\nMODE='+repr(mode)+'\n'+WORKER]
        return run_once(business,**kwargs,command=command)
    generator=Responses()
    generator.chat=lambda *a,**kw: pytest.fail('generation was repurchased')
    router=SolNaturalProvider(generator,SolReviewProvider(api_key='OFFLINE_SENTINEL',
        directory=session.transport_root/'review',task_directory=session.transport_root,
        sender=sender,contract_module=contract),contract_module=contract)
    try:
        with session:
            result=engine.run_chain(session,router)
            if not read_only:
                session.close(dict(outcome=result['outcome']))
    except SessionPaused:
        return session,gate,None
    return session,gate,result


def complete(state, *, statuses=(), modes=(), reject=None):
    previous=None
    for _ in range(16):
        session,gate,result=drive(state,previous=previous,statuses=statuses,modes=modes)
        if result is not None:
            return session,gate,result
        previous=session
        if session.status()['timeout_waiting'] or session.status()['format_waiting']:
            return session,gate,None
        importer,gate=engine.open_session(state['root'],state['spec'],state['source'],before_new_model=lambda:None,
            guard=session.guard_sha,checkpoint=session.checkpoint_sha)
        with importer:
            handle=list(gate.handles())[-1]
            key=handle['binding']['key']
            state['stages'].append(key)
            primary,event=author(handle,state['turns'],gate.native.current.workspace,accepted=key!=reject)
            gate.submit(key,primary,event)
        previous=importer
        if key==reject:
            return importer,gate,None
    pytest.fail('too many diagnostic segments')


def test_controls_then_one_a_application_same_report_fresh_and_readonly_replay(setup):
    s,g,result=complete(setup)
    assert result['outcome']=='candidate_repaired_pass_unqualified'
    assert setup['http']==[200]*6
    assert setup['stages']==['control-b','control-c','control-d','completion-initial',
                            'compatibility','edit','facts-fresh','completion-fresh']
    assert result['accounting']['calls']==10
    assert result['accounting']['logical']==dict(generation=2,review=4,control=3)
    assert result['accounting']['tokens']==66591+6*20
    assert len(list(s.journal_root.glob('application.json')))==1
    contexts=[json.loads(p.read_bytes()) for p in s.transport_root.glob('review/call-*/validation-context.json')]
    fresh=[c for c in contexts if c['stage']=='fresh']
    assert len(fresh)==2 and fresh[0]['report']==fresh[1]['report']==result['application']
    assert '禁用率 4%' in result['application'] and 'OFFLINE fixture action.' in result['application']
    material=json.loads((s.journal_root/'host/edit/material.json').read_bytes())
    assert len(material['initial_requests_with_complete_policies'])==2
    before=tree(setup['root']),list(setup['http'])
    _,_,replayed=drive(setup,previous=s,read_only=True)
    assert replayed==result and before==(tree(setup['root']),setup['http'])
    parent=Path(setup['spec']['proof']['parent_operator'])
    assert inventory(parent)==setup['parent_inventory']


@pytest.mark.parametrize('mode', ['timeout','format'])
def test_failure_keeps_prior_cost_and_plain_resume_never_resends(setup,mode):
    statuses=(524,) if mode=='timeout' else ()
    modes=('text',) if mode=='format' else ()
    s,g,result=complete(setup,statuses=statuses,modes=modes)
    assert result is None and len(setup['http'])==1
    resumed,_,result=drive(setup,previous=s,statuses=statuses,modes=modes)
    assert result is None and len(setup['http'])==1
    retried,_,_=drive(setup,previous=resumed,statuses=statuses,modes=modes,retry=True)
    assert len(setup['http'])==2
    # Current segment pauses at native review after successful same-control retry.
    models=[json.loads(p.read_bytes())['value'] for p in sorted((retried.root/'operations').glob('*-result.json'))]
    budget=[v['budget'] for v in models if isinstance(v,dict) and 'budget' in v][-1]
    assert budget['calls']==6 and budget['retries']==1
    assert budget['logical']==dict(generation=2,review=1,control=1)
    assert budget['tokens']==66591+(20 if mode=='timeout' else 40)
    assert (budget['reserved_tokens']>0)==(mode=='timeout')


def test_semantic_rejection_keeps_success_and_blocks_next_control(setup):
    s,_,_=complete(setup,reject='control-b')
    assert setup['http']==[200]
    with pytest.raises(SessionBlocked):
        drive(setup,previous=s)
    assert setup['http']==[200]


def test_contract_isolates_inherited_facts_and_candidate_policies():
    inputs=materials()['a']
    inherited=contract.make_request(inputs,'facts')
    assert inherited==old.make_request(inputs,'facts')
    assert contract.request_bytes(inherited)==old.request_bytes(inherited)
    with pytest.raises(ValueError):
        contract.validate_business(visible(json_value(inherited)),inherited.metadata[old.CONTEXT])
    for duty in ('facts','completion'):
        r=contract.make_request(inputs,duty,'fresh')
        contract.validate_business(visible(json_value(r)),r.metadata[contract.CONTEXT])
        with pytest.raises(ValueError):
            old.validate_business(visible(json_value(r)),r.metadata[contract.CONTEXT])


def test_identity_conflict_is_not_retryable_or_attributed_as_known_usage(setup):
    with pytest.raises(ProviderResponseError):
        drive(setup, modes=('identity',))
    assert setup['http'] == [200]
    rows = [json.loads(p.read_bytes())['value'] for p in
            sorted((setup['root']/'session/operations').glob('*-result.json'))]
    failed = [v for v in rows if isinstance(v, dict) and v.get('ok') is False][-1]
    assert not any(k in failed for k in ('reaped_timeout', 'recoverable_format'))
    assert failed['budget']['calls'] == 5
    assert failed['budget']['tokens'] == 66591
    assert failed['budget']['reserved_tokens'] > 0
    assert failed['budget']['retries'] == 0


@pytest.mark.parametrize('failure', ['missing_guard', 'parent_changed', 'bound_source'])
def test_missing_send_guard_or_changed_source_blocks_before_http(setup, failure):
    if failure == 'parent_changed':
        parent = Path(setup['spec']['proof']['parent_operator'])
        (parent/'plan.json').write_bytes(b'{}')
        with pytest.raises(SessionBlocked, match='completion_parent_originals_changed'):
            drive(setup)
    else:
        s, _ = engine.open_session(setup['root'], setup['spec'], setup['source'],
                                   before_new_model=None)
        if failure == 'missing_guard':
            with pytest.raises(SessionBlocked, match='completion_specific_send_guard_required'), s:
                engine.import_parent(s)
                s.cursor = 9
                s.operation('model', {}, lambda: pytest.fail('unguarded send'))
        else:
            workflow = engine.CompletionWorkflow(None, session=s)
            with pytest.raises(SessionBlocked, match='completion_bound_source_required'):
                workflow.inputs_for(engine.BoundRequest(workflow.inputs.source.report, '0'*64))
    assert setup['http'] == []
