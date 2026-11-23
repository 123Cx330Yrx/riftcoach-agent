"""Offline control-flow evidence. Synthetic reviews never certify live quality."""
from copy import deepcopy
from dataclasses import replace
from functools import lru_cache
import hashlib
import json
from types import SimpleNamespace

import pytest
from app.evaluation.golden_integrated_runtime import Exchange
from app.providers.models import ChatResponse, ToolCall, TokenUsage
from app.runtime.reviewer_roles import RoleRoutedProvider
from scripts import run_document_review_scan as runner
from scripts import document_review_scan_handoff as handoff
from scripts import seal_document_review_scan as sealing
from tests.test_scope_resolution_diagnostic import Host
from tests.test_reviewer_role_proposal import providers


@lru_cache
def controls():
    # Closed historical batches bind their original source identity. Current
    # shared code may evolve; use the public frozen inputs for synthetic IO,
    # never claim today's source fingerprint is that historical identity.
    sealed = json.loads((runner.base.ROOT / runner.SEAL).read_bytes())
    assert runner.base.sha(runner.base.ROOT / runner.SEAL) == runner.SEAL_SHA
    prior = sealed['public_json_contents']['plan.json']['preparation_plan']
    current, requests = runner.qualification.prepare_qualification()
    assert current['cases'] == prior['cases']
    assert tuple(r['key'] for r in sealed['execution_result']['cases']) == runner.HISTORICAL
    material = dict(current, identity=deepcopy(prior['identity']))
    sources = {r['key']: s for r, s in runner.qualification.frozen_cases()[0]}
    variants = []
    for row in prior['cases']:
        if row['key'] in runner.HISTORICAL:
            continue
        inputs = runner.qualification.Workflow.build_inputs(sources[row['key']])
        request = runner.qualification.Workflow.make_request(inputs)
        raw = runner.base.validate_request(request, transport_id=runner.base.REVIEW_MODEL_TRANSPORT_ID)
        assert raw == requests[row['key']]
        assert hashlib.sha256(raw).hexdigest() == row['request_sha256']
        variants.append((dict(row, synthetic_report=False), inputs, request))
    assert tuple(c['key'] for c, *_ in variants) == runner.KEYS
    return material, variants


LIVE_CONTROLS = runner.controls


def test_live_scan_refuses_current_source_identity_for_historical_batch():
    with pytest.raises(ValueError, match='document_scan_business_identity_changed'):
        LIVE_CONTROLS()


@lru_cache
def prepared():
    return runner.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent')


@pytest.fixture(autouse=True)
def fixed_controls(monkeypatch):
    value = controls()
    monkeypatch.setattr(runner, 'controls', lambda: value)


def reply():
    # A valid protocol output, deliberately wrong verdict on incorrect inputs.
    # Source accuracy is not claimed by any synthetic Host in these tests.
    seal = json.loads((runner.base.ROOT/runner.SEAL).read_bytes())
    return deepcopy(seal['public_json_contents']['claim-scope-1/initial.json']['journal']['parsed_review'])


def response(request, reviewer, fault=None):
    if fault == 'transport':
        raise RuntimeError('Synthetic interrupted send')
    answer = reply()
    if fault == 'schema':
        answer['extra'] = True
    result = ChatResponse(provider='zhipu', model='glm-5.3' if fault != 'wrong_model' else 'glm-5.3-flash',
        content=None, finish_reason='tool_calls', usage=TokenUsage(input_tokens=20, output_tokens=10),
        tool_calls=(ToolCall(id='synthetic',name='submit_report_review',arguments=answer),))
    reviewer.last_exchange = Exchange(request,result,hashlib.sha256(runner.base.validate_request(
        request,transport_id=runner.base.REVIEW_MODEL_TRANSPORT_ID)).hexdigest())
    if fault == 'receipt':
        reviewer.last_exchange = replace(reviewer.last_exchange, receipt_request_sha256='0'*64)
    return result


def factory(monkeypatch, fault=None):
    generator, reviewer = providers()
    def forbidden(*_):
        pytest.fail('scan must never send to editor')
    monkeypatch.setattr(generator,'chat',forbidden)
    monkeypatch.setattr(reviewer,'chat',lambda request: response(request,reviewer,fault))
    router = RoleRoutedProvider(generator,reviewer,
        source_projection=runner.base.CONTRACT.descriptor()['source_projection'])
    return lambda _:router


class FirstRejectHost(Host):
    def adjudicate(self,path,remaining):
        self.fault = 'reject' if path.parent.name == runner.arm_name(runner.KEYS[0]) else None
        return super().adjudicate(path,remaining)


def test_semantic_disagreement_and_wrong_verdict_collect_without_retry(tmp_path,monkeypatch):
    plan = prepared()
    host = FirstRejectHost(plan)
    result = runner.observe(factory(monkeypatch),tmp_path,plan,event_source=host,adjudicate=host.adjudicate)
    assert result['scan_completed'] and not result['diagnostic_accepted'],result
    assert result['calls'] == 11 and result['known_tokens'] == 330
    assert [s['key'] for s in result['stages']] == list(runner.KEYS)
    assert result['stages'][0]['semantic_failures'] == ['reviewer_disagreement','unexpected_verdict_or_score']
    assert any(s['semantic_accepted'] for s in result['stages'][1:])
    assert result['unexecuted_keys'] == result['unadjudicated_keys'] == []
    assert not result['original15_qualified'] and not result['product_admitted'] and result['historical_credit']==0
    for key in runner.KEYS:
        stage = json.loads((tmp_path/runner.arm_name(key)/'stage.json').read_bytes())
        assert stage['journal']['previous_raw'] is None
        assert not (tmp_path/runner.arm_name(key)/'revision.json').exists()


@pytest.mark.parametrize('fault,calls', [('transport',1),('wrong_model',1),('receipt',1),('schema',1),
    ('identity',1),('unavailable',1),('report_certification',1),('missing_report_field',1),('budget',0)])
def test_hard_failures_stop_never_become_semantics(tmp_path,monkeypatch,fault,calls):
    plan = deepcopy(prepared())
    if fault == 'budget':
        plan['budget']['max_tokens'] = 1
    host = Host(plan,fault)
    result = runner.observe(factory(monkeypatch,fault),tmp_path,plan,event_source=host,adjudicate=host.adjudicate)
    assert result['calls']==calls and not result['scan_completed'],result
    assert result['stages']==[] and not (tmp_path/runner.arm_name(runner.KEYS[1])).exists()
    assert len(result['unadjudicated_keys'])==calls
    assert len(result['unexecuted_keys'])==11-calls
    assert (result['unknown_reserved_tokens'] > 0)==(fault in ('transport','wrong_model'))
    assert json.loads((tmp_path/'result.json').read_bytes())==json.loads(json.dumps(result))


def test_immutable_remaining_inventory_exact_original_requests_and_no_label_injection():
    material,variants = controls()
    assert tuple(c['key'] for c,*_ in variants)==runner.KEYS
    assert not set(runner.HISTORICAL)&set(runner.KEYS)
    prior = json.loads((runner.base.ROOT/runner.SEAL).read_bytes())['public_json_contents']['plan.json']['preparation_plan']
    assert material['cases']==prior['cases'] and material['identity']==prior['identity']
    route = runner.diagnostic.DocumentDiagnosticRoute(variants)
    historical = next(s for r,s in runner.qualification.frozen_cases()[0] if r['key']==runner.HISTORICAL[0])
    with pytest.raises(ValueError,match='not_frozen'):
        route.request_identity(runner.qualification.Workflow.make_request(runner.qualification.Workflow.build_inputs(historical)))
    for cell,inputs,request in variants:
        assert len(request.messages)==4 and request.max_tokens==32768
        assert all(token not in str(request.messages) for token in ('expected_initial','host_only_expected','primary_accepted'))
        assert runner.base.digest(inputs.source.report)==cell['report_sha256']
        assert route.request_identity(request)==('zhipu','glm-5.3')
    plan=prepared()
    assert plan['budget']['estimated_uncached_cny']=='15.724544'
    assert set(runner.qualification.SOURCE_FILES)<=set(plan['source_sha256'])


def actual_factory(tmp_path,monkeypatch,fail_at=None):
    from app.evaluation import golden_stream_bridge as bridge
    count=[]
    def child(command,raw,*,directory,timeout_s,environ,transport_id):
        request=runner.shared.REQUEST.validate_json(raw,strict=True)
        count.append(request)
        if len(count)==fail_at:
            raise RuntimeError('Synthetic transport interruption')
        runner.base.write_new_json(directory/'result.json',dict(state='complete',elapsed_ms=0,transport_id=transport_id))
        return response(request,SimpleNamespace())
    monkeypatch.setattr(bridge,'run_child',child)
    def settings(model):
        return SimpleNamespace(model=model,api_key='offline-only',base_url='https://open.bigmodel.cn/api/paas/v4')
    actual=runner.base.RunScopedRoleReceiptedProviderFactory(generator_settings=settings('glm-5.3-flash'),
        reviewer_settings=settings('glm-5.3'),transport_root=tmp_path/'transport',
        source_projection=runner.base.CONTRACT.descriptor()['source_projection'])
    return actual,count


@pytest.mark.parametrize('fail_at', [None,3])
def test_receipts_native_handoff_closed_replay_and_public_export(tmp_path,monkeypatch,fail_at):
    plan=prepared()
    runner.base.write_new_json(tmp_path/'plan.json',dict(preparation_plan=plan,plan_sha256=runner.base.canonical_sha(plan)))
    actual,count=actual_factory(tmp_path,monkeypatch,fail_at)
    host=FirstRejectHost(plan)
    def adjudicate(path,remaining):
        key=json.loads(path.read_bytes())['binding']['key']
        task=json.loads(handoff.task(tmp_path,key))
        opinion=host.adjudicate(path,remaining)
        assert task['binding']==opinion['primary']['binding']
        notes={k:opinion['primary']['stage_assessment'][k] for k in ('accepted','defects','source_review')}
        handoff.submit(tmp_path,key,notes,opinion['independent']['independent_source_event']['event_id'],host)
        with pytest.raises(FileExistsError):
            handoff.submit(tmp_path,key,notes,opinion['independent']['independent_source_event']['event_id'],host)
        return json.loads((path.parent/'review-submission.json').read_bytes())
    result=runner.observe(actual,tmp_path,plan,event_source=host,adjudicate=adjudicate)
    assert result['calls']==(11 if fail_at is None else fail_at),result
    with pytest.raises(ValueError,match='batch_closed'):
        handoff.material(tmp_path,runner.KEYS[0])
    rebuilt=sealing.replay(tmp_path,event_source=host)
    assert rebuilt['stages']==result['stages']
    assert rebuilt['accounting']['unknown_usage_calls']==(0 if fail_at is None else 1)
    export=tmp_path.parent/(tmp_path.name+'-public.json')
    sealing.seal(tmp_path,export,event_source=host)
    public=json.loads(export.read_bytes())
    assert not public['review_controls_qualified']
    assert not any('stream-' in k for k in public['public_json_contents'])
    with pytest.raises(FileExistsError):
        sealing.seal(tmp_path,export,event_source=host)
    saved=deepcopy(result)
    saved['stages'][0]['semantic_accepted']=True
    (tmp_path/'result.json').write_text(json.dumps(saved),encoding='utf8')
    with pytest.raises(ValueError,match='semantic_record_changed'):
        sealing.replay(tmp_path,event_source=host)


def test_freeze_mismatch_and_ci_failure_precede_secrets_closed_batch_cannot_restart(tmp_path,monkeypatch):
    plan=prepared()
    monkeypatch.setattr(runner,'prepare',lambda **_:plan)
    monkeypatch.setattr(runner.base,'ROOT',tmp_path)
    file=tmp_path/'preparation.json'
    file.write_text(json.dumps(plan),encoding='utf8')
    args=SimpleNamespace(root_thread_id='synthetic-root',independent_thread_id='synthetic-independent',execute=True,
        preparation=file,plan_sha=runner.base.canonical_sha(plan),ci_run='synthetic',env_file=tmp_path/'absent.env',
        codex_executable=tmp_path/'absent.exe')
    def forbidden(*_):
        pytest.fail('credentials must not be used')
    monkeypatch.setattr(runner.base,'load_role_settings',forbidden)
    def failed_ci(*_):
        raise ValueError('synthetic_ci_failure')
    monkeypatch.setattr(runner.base,'verify_public_ci',failed_ci)
    with pytest.raises(ValueError,match='ci_failure'):
        runner.run(args)
    file.write_text('{}',encoding='utf8')
    with pytest.raises(ValueError,match='preparation_required'):
        runner.run(args)
    (tmp_path/'data/runs/model_comparison'/runner.EXPERIMENT).mkdir(parents=True)
    with pytest.raises(ValueError,match='closed_or_exists'):
        runner.run(args)


def test_close_during_native_fetch_rejects_late_submission(tmp_path,monkeypatch):
    plan=prepared();key=runner.KEYS[0]
    arm=tmp_path/runner.arm_name(key);arm.mkdir()
    bound=dict(plan_sha256=runner.base.canonical_sha(plan),key=key,stage='initial',
        request_sha256='a'*64,response_sha256='b'*64,report_sha256='c'*64)
    stage=dict(stage='initial',report='Synthetic',journal={})
    path=arm/'review-required.json'
    runner.base.write_new_json(path,dict(binding=bound,stage_sha256=runner.base.stage_identity(stage)))
    host=Host(plan);opinion=host.adjudicate(path,10)
    monkeypatch.setattr(handoff,'material',lambda *_:(plan,stage,bound))
    fetch=host.fetch
    def late_fetch(**kwargs):
        if not (tmp_path/'result.json').exists():
            runner.shared.close_result(tmp_path,dict(scan_completed=False))
        return fetch(**kwargs)
    host.fetch=late_fetch
    with pytest.raises(ValueError,match='batch_closed'):
        handoff.submit(tmp_path,key,dict(accepted=True,defects=[],source_review='Synthetic'),
            opinion['independent']['independent_source_event']['event_id'],host)
    assert not (arm/'review-submission.json').exists() and not list(arm.glob('.submission-*.tmp'))


def test_pre_send_failure_zero_receipts_replays_and_nonempty_orphan_is_rejected(tmp_path,monkeypatch):
    plan=prepared()
    runner.base.write_new_json(tmp_path/'plan.json',dict(preparation_plan=plan,plan_sha256=runner.base.canonical_sha(plan)))
    actual,count=actual_factory(tmp_path,monkeypatch)
    host=Host(plan)
    def unavailable():
        raise ValueError('synthetic_pre_send_unavailable')
    result=runner.observe(actual,tmp_path,plan,event_source=host,adjudicate=host.adjudicate,before_send=unavailable)
    assert result['calls']==0 and not count
    assert sealing.replay(tmp_path,event_source=host)['accounting']['calls']==0
    orphan=tmp_path/'transport'/runner.arm_name(runner.KEYS[0])/'orphan.txt'
    orphan.parent.mkdir(parents=True)
    orphan.write_text('Unexpected pre-send file',encoding='utf8')
    with pytest.raises(ValueError,match='task_call_inventory'):
        runner.read_calls(tmp_path/'transport')


def test_public_allowlist_refuses_non_null_private_reasoning(tmp_path):
    runner.base.write_new_json(tmp_path/'plan.json',dict(reasoning_content='private'))
    runner.base.write_new_json(tmp_path/'result.json',{})
    with pytest.raises(ValueError,match='public_private_field'):
        sealing.public_contents(tmp_path,dict(stages=[],unadjudicated_keys=[]))


def test_transport_identity_failure_before_receipt_is_explicit_unknown_attempt(tmp_path,monkeypatch):
    from app.runtime.receipted_provider_factory import RoleReceiptedStreamProvider
    plan=prepared()
    runner.base.write_new_json(tmp_path/'plan.json',dict(preparation_plan=plan,plan_sha256=runner.base.canonical_sha(plan)))
    actual,count=actual_factory(tmp_path,monkeypatch)
    def bad_identity(self):
        from app.providers.errors import ProviderResponseError
        raise ProviderResponseError(provider='zhipu',code='synthetic_identity_before_io')
    monkeypatch.setattr(RoleReceiptedStreamProvider,'_require_identity',bad_identity)
    host=Host(plan)
    result=runner.observe(actual,tmp_path,plan,event_source=host,adjudicate=host.adjudicate)
    assert result['calls']==1 and not count and result['unknown_reserved_tokens']>0
    calls=runner.read_calls(tmp_path/'transport')
    assert calls[0]['receipt_missing'] and not calls[0]['completed'] and calls[0]['usage'] is None
    rebuilt=sealing.replay(tmp_path,event_source=host)
    assert rebuilt['accounting']['transport_receipt_calls']==0
    assert rebuilt['accounting']['local_attempts_without_transport_receipt']==1
    assert rebuilt['accounting']['unknown_usage_calls']==1


@pytest.mark.parametrize('fault',['role','route'])
def test_wrapper_prechecks_record_local_attempt_without_parent_attempt(tmp_path,monkeypatch,fault):
    plan=prepared()
    runner.base.write_new_json(tmp_path/'plan.json',dict(preparation_plan=plan,plan_sha256=runner.base.canonical_sha(plan)))
    actual,count=actual_factory(tmp_path,monkeypatch)
    def bad_role(*args):
        raise ValueError('synthetic_role_before_io')
    if fault=='role':
        monkeypatch.setattr(runner.diagnostic,'require_role_provider',bad_role)
    else:
        original=runner.diagnostic.DocumentDiagnosticRoute.baseline
        def bad_route(self,request):
            if len(self.variants)==1:
                raise ValueError('synthetic_route_before_io')
            return original(self,request)
        monkeypatch.setattr(runner.diagnostic.DocumentDiagnosticRoute,'baseline',bad_route)
    host=Host(plan)
    result=runner.observe(actual,tmp_path,plan,event_source=host,adjudicate=host.adjudicate)
    assert result['calls']==1 and not count and result['attempts'][0]['local_pre_transport']
    rebuilt=sealing.replay(tmp_path,event_source=host)
    assert rebuilt['accounting']['local_attempts_without_transport_receipt']==1
    assert rebuilt['unadjudicated_keys']==[runner.KEYS[0]]


def test_invalid_native_tail_is_digest_only_and_dispatch_tampering_rejected(tmp_path,monkeypatch):
    plan=prepared()
    runner.base.write_new_json(tmp_path/'plan.json',dict(preparation_plan=plan,plan_sha256=runner.base.canonical_sha(plan)))
    actual,count=actual_factory(tmp_path,monkeypatch)
    host=Host(plan,'identity')
    result=runner.observe(actual,tmp_path,plan,event_source=host,adjudicate=host.adjudicate)
    assert result['calls']==1 and result['stages']==[] and not result['scan_completed']
    rebuilt=sealing.replay(tmp_path,event_source=host)
    host_file=runner.arm_name(runner.KEYS[0])+'/host-reviews.json'
    assert rebuilt['unverified_tail_host_files']==[host_file]
    contents=sealing.public_contents(tmp_path,rebuilt)
    assert host_file not in contents
    export=tmp_path.parent/(tmp_path.name+'-public.json')
    sealing.seal(tmp_path,export,event_source=host)
    assert host_file in json.loads(export.read_bytes())['original_file_sha256']
    required=tmp_path/runner.arm_name(runner.KEYS[0])/'review-required.json'
    value=json.loads(required.read_bytes());value['binding']['request_sha256']='0'*64
    required.write_text(json.dumps(value),encoding='utf8')
    with pytest.raises(ValueError,match='handoff_changed'):
        sealing.replay(tmp_path,event_source=host)
