"""Prospective pipeline checks with public inputs and synthetic IO only."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_document_accepted_tails as legacy
from scripts import run_document_checkpoint_tails as runner
from scripts import document_checkpoint_tail_handoff as handoff
from scripts import seal_document_checkpoint_tails as seal
from tests.test_document_accepted_tails import public_controls,fake_factory,unique_host


@pytest.fixture(scope='module',autouse=True)
def public_checkout_only():
    forbidden=(runner.base.ROOT/'data/runs').resolve()
    with pytest.MonkeyPatch.context() as patch:
        for method in ('read_bytes','read_text'):
            original=getattr(Path,method)
            def guarded(path,*args,_original=original,**kwargs):
                if path.resolve().is_relative_to(forbidden):pytest.fail('No private local run reads in offline tests')
                return _original(path,*args,**kwargs)
            patch.setattr(Path,method,guarded)
        yield


@pytest.fixture(scope='module')
def frozen():
    variants=public_controls()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(legacy,'controls',lambda:variants)
        plan=runner.prepare(root_thread_id='synthetic-root',independent_thread_id='synthetic-independent')
        original=legacy.prepare(root_thread_id='synthetic-root',independent_thread_id='synthetic-independent')
    return plan,variants,original


@pytest.fixture
def setup(tmp_path,monkeypatch,frozen):
    plan,variants,_=frozen
    plan=deepcopy(plan)
    monkeypatch.setattr(legacy,'controls',lambda:variants)
    monkeypatch.setattr(runner,'controls',lambda:variants)
    monkeypatch.setattr(runner,'prepare',lambda **_:plan)
    policy_root=tmp_path/'public-policy-inputs'
    for row,_,_,_,historical,_ in variants:
        p=policy_root/row['key'].replace(':','-')/'issued-request.json'
        p.parent.mkdir(parents=True)
        p.write_bytes(runner.base.validate_request(historical.issued_request,
            transport_id=runner.base.REVIEW_MODEL_TRANSPORT_ID))
    monkeypatch.setattr(runner,'HISTORICAL_RUN',policy_root)
    runner.base.write_new_json(tmp_path/'plan.json',dict(preparation_plan=plan,
        plan_sha256=runner.base.canonical_sha(plan)))
    return plan,variants


def actual_factory(tmp_path,monkeypatch,variants):
    from app.evaluation import golden_stream_bridge as bridge
    fake,requests=fake_factory(variants)
    routers={}
    def child(command,raw,*,directory,timeout_s,environ,transport_id):
        request=bridge.REQUEST.validate_json(raw,strict=True)
        model=runner.backend.CONTRACT.request_identity(request)[1]
        name=next(p for p in directory.parts if p in [k.replace(':','-') for k in runner.KEYS])
        router=routers.setdefault(name,fake(name))
        response=(router.generator if model=='glm-5.3-flash' else router.reviewer).chat(request)
        runner.base.write_new_json(directory/'result.json',dict(state='complete',elapsed_ms=0,transport_id=transport_id))
        return response
    monkeypatch.setattr(bridge,'run_child',child)
    settings=lambda model:SimpleNamespace(model=model,api_key='offline-only',base_url='https://open.bigmodel.cn/api/paas/v4')
    return runner.backend.ProviderFactory(generator_settings=settings('glm-5.3-flash'),
        reviewer_settings=settings('glm-5.3'),transport_root=tmp_path/'transport'),requests


def test_new_plan_preserves_exact_workload_and_budget(frozen):
    plan,_,original=frozen
    assert plan['cells']==original['cells'] and plan['sequence']==original['sequence']
    assert plan['identity']==original['identity'] and plan['budget']==original['budget']
    assert plan['run_id']!=legacy.EXPERIMENT
    assert plan['host_review_evidence_policy']==original['host_review_evidence_policy']=='native-final-attestation-v1'
    assert set(plan['source_sha256'])-set(original['source_sha256'])==set(runner.SOURCE_FILES)-set(legacy.SOURCE_FILES)
    assert all(plan['source_sha256'][k]==v for k,v in original['source_sha256'].items())


@pytest.mark.parametrize('mode',['success','abort','bad_checkpoint','semantic_reject','missing_checkpoint','source_abort'])
def test_real_receipted_flow_checkpoint_and_abort(tmp_path,monkeypatch,setup,mode):
    plan,variants=setup
    factory,requests=actual_factory(tmp_path,monkeypatch,variants)
    host=unique_host(plan)
    publications=[]
    def judge(path,remaining):
        bound=json.loads(path.read_bytes())['binding']
        key,stage=bound['key'],bound['stage']
        if mode in ('abort','source_abort'):
            if mode=='source_abort':
                target=path.parent.parent/'source.json'
                target.write_text('{"changed":true}',encoding='utf-8')
                with pytest.raises(ValueError):handoff.material(tmp_path,key,stage)
            marker=handoff.abort(tmp_path,key,stage,'source_or_request_changed' if mode=='source_abort' else 'native_binding_failure')
            assert marker['review_submitted'] is False
            with pytest.raises(ValueError,match='closed'):handoff.abort(tmp_path,key,stage,'reviewer_unavailable')
            return runner.wait_reviews(path,remaining)
        if mode=='missing_checkpoint':return host.adjudicate(path,remaining)
        packet=handoff.publish_checkpoint(tmp_path,key,stage,tmp_path/'operator')
        publications.append(packet)
        host.fault='host_reject' if mode=='semantic_reject' and key==runner.KEYS[0] else None
        submission=host.adjudicate(path,remaining)
        notes={k:submission['primary'][k] for k in ('stage_assessment','report_assessment')}
        event_id=submission['independent']['independent_source_event']['event_id']
        sha='0'*64 if mode=='bad_checkpoint' else packet['checkpoint_sha256']
        handoff.submit(tmp_path,key,stage,notes,event_id,host,packet['checkpoint'],sha)
        with pytest.raises(ValueError,match='closed'):
            handoff.publish_checkpoint(tmp_path,key,stage,tmp_path/'duplicate')
        with pytest.raises(ValueError,match='closed'):
            handoff.submit(tmp_path,key,stage,notes,event_id,host,packet['checkpoint'],sha)
        return json.loads(path.with_name('review-submission.json').read_bytes())
    result=runner.observe(factory,tmp_path,plan,event_source=host,adjudicate=judge)
    assert result['calls']==len(requests)==(1 if mode in ('abort','bad_checkpoint','missing_checkpoint','source_abort') else 11 if mode=='semantic_reject' else 12)
    assert result['scan_completed'] is (mode in ('success','semantic_reject')),result
    assert result['diagnostic_accepted'] is (mode=='success'),result
    assert not result['review_controls_qualified'] and not result['original15_qualified']
    if mode=='source_abort':
        assert result['error_code']=='checkpoint_tail_operator_abort'
        with pytest.raises(ValueError,match='source_changed'):seal.replay(tmp_path,event_source=host)
        return
    rebuilt=seal.replay(tmp_path,event_source=host)
    assert rebuilt['run_id']==runner.RUN_ID and rebuilt['accounting']['calls']==result['calls']
    if mode=='abort':
        assert result['error_code']=='checkpoint_tail_operator_abort'
        assert len(rebuilt['operator_aborts'])==1
        assert not (tmp_path/'scope-4/revision/host-reviews.json').exists()
        assert not (tmp_path/'scope-4/revision/review-submission.json').exists()
        marker=tmp_path/'scope-4/revision/operator-abort.json'
        altered=json.loads(marker.read_bytes());altered['binding']['key']='wrong';marker.write_text(json.dumps(altered),encoding='utf-8')
        with pytest.raises(ValueError,match='abort_binding'):seal.replay(tmp_path,event_source=host)
    elif mode in ('bad_checkpoint','missing_checkpoint'):
        assert result['error_code']==('host_checkpoint_digest' if mode=='bad_checkpoint' else 'checkpoint_tail_checkpoint_required')
        assert not rebuilt['stages'] and not (tmp_path/'scope-4/final').exists()
    else:
        assert len(rebuilt['stages'])==(11 if mode=='semantic_reject' else 12)
        raw=tmp_path/'scope-4/revision/independent-task.json'
        value=json.loads(raw.read_bytes());value['instructions']='Wrong task';raw.write_text(json.dumps(value),encoding='utf-8')
        with pytest.raises(ValueError,match='checkpoint_changed'):seal.replay(tmp_path,event_source=host)
    with pytest.raises(ValueError,match='closed'):handoff.publish_checkpoint(tmp_path,runner.KEYS[0],'revision',tmp_path/'late')


def test_existing_new_run_rejected_before_ci_or_credentials(tmp_path,monkeypatch):
    monkeypatch.setattr(runner.base,'ROOT',tmp_path)
    (tmp_path/'data/runs/model_comparison'/runner.RUN_ID).mkdir(parents=True)
    with pytest.raises(ValueError,match='closed_or_exists'):runner.execute(SimpleNamespace(),{})


@pytest.mark.parametrize('change',[dict(reason='not_a_reason'),dict(binding={}),dict(native_event_reference='secret_or_unbound_text')])
def test_invalid_operator_abort_is_rejected(change):
    bound={'key':'scope:4'}
    marker=dict(kind=runner.ABORT_KIND,binding=bound,reason='checkpoint_unavailable',native_event_reference=None)
    marker.update(change)
    with pytest.raises(ValueError,match='abort_binding_or_format'):runner.validate_abort(marker,bound)
