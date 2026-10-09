"""Synthetic IO verifies isolation/provenance paths, not model quality."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from app.evaluation.golden_integrated_runtime import Exchange
from app.providers.models import ChatResponse,ToolCall,TokenUsage
from app.runtime.document_review_roles import DocumentRoleRoutedProvider
from scripts import run_document_accepted_tails as runner
from scripts import document_accepted_tail_handoff as handoff
from scripts import seal_document_accepted_tails as seal
from tests.test_coarse_edit_diagnostic import Host
from tests.test_reviewer_role_proposal import providers


@pytest.fixture(scope='module',autouse=True)
def no_private_local_run_reads():
    """Enforce public-checkout availability even on the operator's machine."""
    from pathlib import Path
    forbidden = (runner.base.ROOT/'data/runs').resolve()
    with pytest.MonkeyPatch.context() as patch:
        for method in ('read_bytes','read_text'):
            original = getattr(Path,method)
            def guarded(path,*args,_original=original,**kwargs):
                if path.resolve().is_relative_to(forbidden):
                    pytest.fail('Offline tests cannot read ignored local run originals')
                return _original(path,*args,**kwargs)
            patch.setattr(Path,method,guarded)
        yield


def public_controls():
    """Public historical inputs for synthetic IO, never raw/native evidence.

    A clean checkout has the sealed public export, not the private ignored run.
    The live controls() must keep requiring those originals; do not reconstruct
    transport receipts or independent attestations just to satisfy tests.
    """
    sealed = json.loads((runner.base.ROOT/runner.SEAL).read_bytes())
    assert runner.base.sha(runner.base.ROOT/runner.SEAL) == runner.SEAL_SHA
    preparation = json.loads((runner.base.ROOT/'data/evaluation/results/golden_document_accepted_tails_preparation_20261009.json').read_bytes())
    rows = {r['key']:r for r in preparation['cells']}
    sources = {r['key']:s for r,s in runner.backend.frozen_cases()[0]}
    variants = []
    for cell,inputs,initial in runner.scan.controls()[1]:
        key = cell['key']
        if key not in runner.KEYS:continue
        public = sealed['public_json_contents']
        issued = public[key.replace(':','-')+'/issued-request.json']
        request = replace(initial,timeout_s=issued['timeout_s'],
            metadata=dict(initial.metadata,coach_budget_contract=issued['metadata']['coach_budget_contract']))
        raw = runner.base.validate_request(request,transport_id=runner.base.REVIEW_MODEL_TRANSPORT_ID)
        assert json.loads(raw) == issued
        assert hashlib.sha256(raw).hexdigest() == rows[key]['historical_raw_request_sha256']
        response = runner.base.RESPONSE.validate_json(json.dumps(public[key.replace(':','-')+'/response.json']),strict=True)
        saved_journal = public[key.replace(':','-')+'/stage.json']['journal']
        arguments = json.loads(saved_journal['raw'])
        assert response.tool_calls[0].arguments == arguments
        response = replace(response,tool_calls=(replace(response.tool_calls[0],arguments=arguments),))
        historical = Exchange(request,response,rows[key]['historical_raw_request_sha256'])
        _,wire,journal = runner.backend.Workflow.validate_review(runner.base.tool_result(initial,historical),inputs)
        assert journal == saved_journal
        variants.append((rows[key],sources[key],inputs,initial,historical,runner.editor.edit_request(inputs,wire)))
    assert tuple(r['key'] for r,*_ in variants) == runner.KEYS
    return variants


@pytest.fixture(scope='module')
def frozen():
    variants = public_controls()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(runner,'controls',lambda:variants)
        plan = runner.prepare(root_thread_id='synthetic-root',independent_thread_id='synthetic-independent')
    return plan,variants


@pytest.fixture
def setup_run(tmp_path,monkeypatch,frozen):
    plan,variants = frozen
    plan = deepcopy(plan)
    monkeypatch.setattr(runner,'controls',lambda:variants)
    monkeypatch.setattr(runner,'prepare',lambda **_:plan)
    # Policy delivery consumes exact public issued bytes, not invented receipts.
    historical_root = tmp_path/'public-policy-inputs'
    for row,_,_,_,historical,_ in variants:
        arm = row['key'].replace(':','-')
        target = historical_root/arm
        target.mkdir(parents=True)
        (target/'issued-request.json').write_bytes(runner.base.validate_request(
            historical.issued_request,transport_id=runner.base.REVIEW_MODEL_TRANSPORT_ID))
    monkeypatch.setattr(runner,'HISTORICAL_RUN',historical_root)
    runner.base.write_new_json(tmp_path/'plan.json',dict(preparation_plan=plan,plan_sha256=runner.base.canonical_sha(plan)))
    return plan,variants


def fake_factory(variants,fault=None):
    requests = []
    def factory(name):
        row,source,inputs,initial,historical,edit = next(r for r in variants if r[0]['key'].replace(':','-')==name)
        generator,reviewer = providers()
        def chat(provider,request,role):
            requests.append((row['key'],role,request))
            if fault == 'transport':raise RuntimeError('Synthetic incomplete transport')
            if role == 'revision':
                raw = historical.response.tool_calls[0].arguments
                edits = []
                for issue in raw['issues']:
                    text = inputs.source.blocks[issue['block']-1][1]
                    # Pure parser/flow fixture, no assertion of real correction.
                    edits.append(dict(block=issue['block'],before=text,after=text+' Synthetic test edit.',reason='Synthetic test only.'))
                if fault == 'anchor':edits[0]['before']='ABSENT'
                arguments,tool = dict(edits=edits),runner.editor.TOOL
            else:
                arguments = dict(score=96,verdict='pass',issues=[],issue_resolutions=[],advisories=[])
                if fault == 'fresh_failed' and row['key']==runner.KEYS[0]:arguments.update(score=60,verdict='fail')
                tool = 'submit_report_review'
            response = ChatResponse(provider='zhipu',model=provider.model_name,content=None,finish_reason='tool_calls',
                tool_calls=(ToolCall('synthetic',tool,arguments),),usage=TokenUsage(input_tokens=20,output_tokens=10))
            provider.last_exchange = Exchange(request,response,hashlib.sha256(runner.base.validate_request(request,
                transport_id=runner.base.CAPACITY_TRANSPORT_ID if role=='revision' else runner.base.REVIEW_MODEL_TRANSPORT_ID)).hexdigest())
            return response
        generator.chat=lambda r:chat(generator,r,'revision')
        reviewer.chat=lambda r:chat(reviewer,r,'review')
        return DocumentRoleRoutedProvider(generator,reviewer,source_projection=runner.backend.CONTRACT.descriptor()['source_projection'])
    return factory,requests


def unique_host(plan):
    host = Host(plan,None)
    judge = host.adjudicate
    def adjudicate(path,remaining):
        submission=judge(path,remaining)
        event=submission['independent']['independent_source_event']
        event['event_id']+='-'+path.parent.parent.name
        host.events[event['event_id']]=event
        return submission
    host.adjudicate=adjudicate
    return host


def test_historical_acceptance_and_policy_compatibility(frozen):
    plan,variants=frozen
    assert plan['role_calls']=={'glm-5.3-flash':6,'glm-5.3':6}
    assert plan['budget']['max_calls']==12 and plan['budget']['max_tokens']==1161216
    assert plan['budget']['estimated_uncached_cny']=='9.4347264'
    assert plan['historical_initial_inputs']==6 and not plan['historical_inputs_are_new_calls']
    for row,source,inputs,initial,historical,edit in variants:
        assert row['key'] not in ('scope:3','attribution:1')
        assert historical.issued_request.messages==initial.messages
        _,wire,_=runner.backend.Workflow.validate_review(runner.base.tool_result(initial,historical),inputs)
        assert wire.verdict=='needs_revision' and edit==runner.editor.edit_request(inputs,wire)


def test_live_history_does_not_substitute_public_export_for_missing_originals(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'HISTORICAL_RUN',tmp_path/'absent-private-run')
    with pytest.raises(FileNotFoundError):runner.controls()


@pytest.mark.parametrize('fault,calls,completed',[(None,12,True),('host_reject',11,True),
    ('fresh_failed',12,True),('transport',1,False),('anchor',1,False),('host_unavailable',1,False),('budget',0,False)])
def test_shared_budget_case_semantics_continue_and_hard_fail_stop(tmp_path,setup_run,fault,calls,completed):
    plan,variants=setup_run
    if fault=='budget':plan['budget']['max_tokens']=1
    host=unique_host(plan)
    factory,requests=fake_factory(variants,fault)
    def judge(path,remaining):
        host.fault=('host_reject' if fault=='host_reject' and path.parent.parent.name==runner.KEYS[0].replace(':','-')
            else 'host_unavailable' if fault=='host_unavailable' else None)
        return host.adjudicate(path,remaining)
    result=runner.observe(factory,tmp_path,plan,event_source=host,adjudicate=judge)
    assert result['calls']==len(requests)==calls,result
    assert result['scan_completed'] is completed,result
    assert result['diagnostic_accepted'] is (fault is None),result
    assert not result['review_controls_qualified'] and not result['original15_qualified']
    assert (result['unknown_reserved_tokens']>0) is (fault=='transport')
    assert json.loads((tmp_path/'result.json').read_bytes())==result
    if completed:
        assert [c['key'] for c in result['cases']]==list(runner.KEYS)
    if fault=='host_reject':
        assert not (tmp_path/runner.KEYS[0].replace(':','-')/'final').exists()
        assert all(c['semantic_accepted'] for c in result['cases'][1:])
    if fault=='fresh_failed':assert result['cases'][0]['semantic_failure']=='fresh_not_pass'
    if calls and fault not in ('transport','budget'):
        assert result['known_tokens']==calls*30


@pytest.mark.parametrize('tamper',[None,'source','issued','stage','historical','binding','response',
    'semantic_edit','semantic_fresh','pretransport','seal_count'])
def test_real_receipts_task_native_submit_and_seal(tmp_path,monkeypatch,setup_run,tamper):
    from app.evaluation import golden_stream_bridge as bridge
    plan,variants=setup_run
    fake,requests=fake_factory(variants,'fresh_failed' if tamper=='semantic_fresh' else None)
    routers={}
    host=unique_host(plan)
    def child(command,raw,*,directory,timeout_s,environ,transport_id):
        request=bridge.REQUEST.validate_json(raw,strict=True)
        identity=runner.backend.CONTRACT.request_identity(request)
        name=next(part for part in directory.parts if part in [k.replace(':','-') for k in runner.KEYS])
        key=next(k for k in runner.KEYS if k.replace(':','-')==name)
        router=routers.setdefault(key,fake(key.replace(':','-')))
        provider=router.generator if identity[1]=='glm-5.3-flash' else router.reviewer
        response=provider.chat(request)
        runner.base.write_new_json(directory/'result.json',dict(state='complete',elapsed_ms=0,transport_id=transport_id))
        return response
    monkeypatch.setattr(bridge,'run_child',child)
    settings=lambda model:SimpleNamespace(model=model,api_key='offline-only',base_url='https://open.bigmodel.cn/api/paas/v4')
    actual_factory=runner.backend.ProviderFactory(generator_settings=settings('glm-5.3-flash'),reviewer_settings=settings('glm-5.3'),transport_root=tmp_path/'transport')
    def actual(name):
        router=actual_factory(name)
        if tamper=='pretransport':router.generator._identity=('tampered',*router.generator._identity[1:])
        return router
    def judge(path,remaining):
        required=json.loads(path.read_bytes())
        key,stage=required['binding']['key'],required['binding']['stage']
        if tamper in ('source','issued','stage','historical','binding','response'):
            target={'source':path.parent.parent/'source.json','issued':path.with_name('issued-request.json'),
                'stage':path.with_name('stage.json'),'historical':path.parent.parent/'historical-initial-journal.json',
                'binding':path,'response':path.with_name('response.json')}[tamper]
            value=json.loads(target.read_bytes());value['tampered']=True;target.write_text(json.dumps(value),encoding='utf-8')
            with pytest.raises(ValueError,match='accepted_tail_'):handoff.material(tmp_path,key,stage)
            raise ValueError('synthetic_tamper_detected')
        _,value,bound=handoff.material(tmp_path,key,stage)
        task=json.loads(handoff.task(tmp_path,key,stage))
        assert task['binding']==bound and 'VERIFIED BUSINESS-POLICY' in task['instructions']
        host.fault='host_reject' if tamper=='semantic_edit' and key==runner.KEYS[0] else None
        submission=host.adjudicate(path,remaining)
        notes={k:submission['primary'][k] for k in ('stage_assessment','report_assessment')}
        event_id=submission['independent']['independent_source_event']['event_id']
        handoff.submit(tmp_path,key,stage,notes,event_id,host)
        with pytest.raises(FileExistsError):handoff.submit(tmp_path,key,stage,notes,event_id,host)
        return json.loads(path.with_name('review-submission.json').read_bytes())
    result=runner.observe(actual,tmp_path,plan,event_source=host,adjudicate=judge)
    assert result['diagnostic_accepted'] is (tamper is None or tamper=='seal_count'),result
    if tamper in (None,'semantic_edit','semantic_fresh','seal_count','pretransport'):
        rebuilt=seal.replay(tmp_path,event_source=host)
        assert rebuilt['accounting']['calls']==(1 if tamper=='pretransport' else 11 if tamper=='semantic_edit' else 12)
        assert not rebuilt['unverified_host_files'] and not rebuilt['review_controls_qualified']
        if tamper=='pretransport':
            assert rebuilt['accounting']['unknown_usage_calls']==1
            assert rebuilt['accounting']['local_attempts_without_transport_receipt']==1
            assert len(requests)==0
        if tamper=='seal_count':
            changed=deepcopy(result);changed['historical_initial_inputs']+=1
            (tmp_path/'result.json').write_text(json.dumps(changed),encoding='utf-8')
            with pytest.raises(ValueError,match='accounting_changed'):seal.replay(tmp_path,event_source=host)
    else:
        assert result['calls']==1,result
        if tamper=='response':
            with pytest.raises(ValueError,match='pending_response_changed'):
                seal.replay(tmp_path,event_source=host)
    with pytest.raises(ValueError,match='closed'):handoff.task(tmp_path,runner.KEYS[0],'revision')


def test_existing_run_rejected_before_ci_or_credentials(tmp_path,monkeypatch):
    monkeypatch.setattr(runner.base,'ROOT',tmp_path)
    (tmp_path/'data/runs/model_comparison'/runner.EXPERIMENT).mkdir(parents=True)
    with pytest.raises(ValueError,match='closed_or_exists'):runner.execute(SimpleNamespace(),{})
