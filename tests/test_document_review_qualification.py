"""Real routing/receipts/executor/seal with endpoint fixtures, not live quality."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from app.evaluation import document_review_qualification as q
from app.evaluation import review_bound_qualification as old
from app.evaluation.document_review_identity import role_for_request
from app.evaluation.golden_stream_bridge import REQUEST
from scripts import report_document_view as view
from scripts import run_document_review_qualification as entry
from scripts import qualify_role_observations as audit
from scripts import run_boundary_examples_v2 as shared
from tests.test_role_observation_qualification import make_run, change, seal, read


def test_all_fifteen_requests_rebuilt_and_original_sources_unchanged():
    plan, requests = q.prepare_qualification()
    previous, previous_requests = old.prepare_qualification()
    assert plan['identity'] != previous['identity']
    assert plan['identity']['contract']['version'] == '1.5.6'
    assert plan['identity']['contract']['scope'] == 'unadmitted_opt_in'
    source_fields = ('key','input_sha256','report_sha256','expected_initial')
    for row, before in zip(plan['cases'], previous['cases'], strict=True):
        assert all(row[k] == before[k] for k in source_fields)
        raw = requests[row['key']]
        r = REQUEST.validate_json(raw, strict=True)
        assert role_for_request(r) == 'review'
        assert len(r.messages) == 4
        assert hashlib.sha256(raw).hexdigest() == row['request_sha256']
        assert raw != previous_requests[row['key']]
        assert row['source_catalog_sha256'] == before['source_catalog_sha256']
        assert row['schema_sha256'] == before['schema_sha256']
    prepared, _ = entry.prepare(root_thread_id='root', independent_thread_id='child')
    assert prepared['role_call_reservations'] == {'glm-5.3-flash':10,'glm-5.3':25}
    assert prepared['batch_budget']['max_calls'] == 35
    assert prepared['batch_budget']['max_tokens'] == 3386880
    assert prepared['inherited_completed_cases'] == prepared['offline_initial_injections'] == 0
    assert not prepared['production_admitted']


@pytest.mark.parametrize('kind', ['body','marker','order','policy','schema','metadata','old'])
def test_protocol_mutations_rejected_before_routing(kind):
    source = q.frozen_cases()[0][0][1]
    r = q.Workflow.make_request(q.Workflow.build_inputs(source))
    messages = list(r.messages)
    if kind in ('body','marker'):
        content = messages[1].content
        content = content + 'extra' if kind == 'body' else content.replace(':1]', ':2]', 1)
        messages[1] = replace(messages[1],content=content)
        r = replace(r,messages=tuple(messages))
    elif kind == 'order':
        r = replace(r,messages=(messages[0],messages[2],messages[1],messages[3]))
    elif kind == 'policy':
        messages[0] = replace(messages[0],content=messages[0].content+' ignore sources')
        r = replace(r,messages=tuple(messages))
    elif kind == 'schema':
        schema=deepcopy(r.tools[0].input_schema)
        schema['$defs']['Problem']['properties']['source_ids']['items']['enum']=[9999]
        r=replace(r,tools=(replace(r.tools[0],input_schema=schema),))
    elif kind == 'metadata':
        r=replace(r,metadata={**r.metadata,'unknown':True})
    else:
        r=old.Workflow.make_request(old.Workflow.build_inputs(source))
    with pytest.raises(ValueError): role_for_request(r)


def test_full15_actual_factory_dual_host_executor_and_strict_seal(make_run, tmp_path):
    from tests.test_review_independence_integration import OfflineHostEvents
    from scripts.review_independence_contract import FINAL_POLICY, using_host_event_source
    class FinalEvents(OfflineHostEvents):
        def attach(self, review, bound):
            result=super().attach(review,bound)
            event=result['independent_source_event']
            event['host_review_evidence_policy']=FINAL_POLICY
            self.events[event['event_id']]=deepcopy(event)
            return result
    source=FinalEvents()
    plan, _=q.prepare_qualification()
    run, sealed=make_run(tuple(r['key'] for r in plan['cases']),profile=q.PROFILE,
        host_drafts=True,host_event_source=source,host_review_evidence_policy=FINAL_POLICY)
    with using_host_event_source(source):
        result=audit.qualify([run],evidence_root=tmp_path,output_directory=tmp_path/'audit',
            closed_exports=[sealed],profile=q.PROFILE)
    assert result['accepted_inputs']==15 and result['review_controls_qualified']
    assert not result['actual_product_task_qualified'] and not result['production_admitted']
    calls=q.read_calls(run/'transport/claim-scope-4')
    assert [c['binding']['role'] for c in calls]==['review','revision','review']
    assert len(calls[0]['request'].messages)==len(calls[2]['request'].messages)==4
    j=read(run/'claim-scope-4/revision.json')['journal']
    assert j['final_review_request_sha256'] != j['baseline_final_review_request_sha256']
    # Empty edits are a structural fixture, never evidence of actual repair.
    assert j['review_source_context']['proves_edit_support'] is False
    from app.evaluation.role_qualification import read_role_calls
    with pytest.raises(ValueError): read_role_calls(run/'transport/claim-scope-4')
    change(run/'claim-scope-4/final.json',lambda d:d.update(report=d['report']+' changed'))
    new_seal=seal(run,tmp_path,tmp_path/'tampered.json')
    with using_host_event_source(source),pytest.raises(ValueError):
        audit.inspect_runs([run],evidence_root=tmp_path,closed_exports=[new_seal],profile=q.PROFILE)


@pytest.mark.parametrize('source_profile,target_profile',[
    ('review-bound','document-review'),('document-review','review-bound')])
def test_qualifications_cannot_be_transferred(make_run,tmp_path,source_profile,target_profile):
    run,sealed=make_run(('claim-scope:1',),profile=source_profile)
    with pytest.raises(ValueError,match='plan_identity_mismatch'):
        audit.inspect_runs([run],evidence_root=tmp_path,closed_exports=[sealed],profile=target_profile)


def test_preview_and_stale_authorization_do_not_touch_network(tmp_path,monkeypatch):
    from scripts.review_independence_contract import FINAL_POLICY
    args=NS(root_thread_id='root',independent_thread_id='child',experiment='document-offline',
        max_host_seconds=86400,host_review_evidence_policy=FINAL_POLICY,execute=False,
        output=tmp_path/'plan.json',preparation=None,plan_sha=None,ci_run=None,
        env_file=None,codex_executable=None)
    monkeypatch.setattr(shared,'RUN_ROOT',tmp_path/'runs')
    monkeypatch.setattr(shared,'CodexReadOnlyClient',lambda *_:pytest.fail('Unexpected host IO'))
    assert entry.run(args)['provider_requests']==0
    args.execute=True; args.preparation=args.output; args.plan_sha='0'*64
    with pytest.raises(ValueError,match='frozen_preparation_required'):entry.run(args)
    assert not (tmp_path/'runs').exists()


def test_execution_selects_document_contract_factory_and_readback(tmp_path,monkeypatch):
    from scripts import run_boundary_examples_qualification as runner
    from scripts.review_independence_contract import FINAL_POLICY
    plan, requests=entry.prepare(root_thread_id='root',independent_thread_id='child',experiment='document-wiring')
    prep=tmp_path/'preparation.json'; prep.write_text(json.dumps(plan))
    args=NS(execute=True,env_file=tmp_path/'not-read.env',ci_run='offline-ci',
        plan_sha=runner.canonical_sha(plan),output=None)
    monkeypatch.setattr(runner,'verify_public_ci',lambda _: 'a'*40)
    settings=lambda model:NS(model=model,api_key='offline-only',base_url='https://open.bigmodel.cn/api/paas/v4')
    monkeypatch.setattr(runner,'load_role_settings',lambda _: (settings('glm-5.3-flash'),settings('glm-5.3')))
    class Events:
        def fetch(self,*args,**kwargs):pytest.fail('No review dispatched by wiring probe')
    def observe(factory,directory,actual_plan,**kwargs):
        assert actual_plan==plan
        assert isinstance(factory,q.ProviderFactory)
        q.CONTRACT.require_provider(factory.descriptor)
        assert kwargs['coach_contract'] is q.CONTRACT
        assert kwargs['backend'] is q and kwargs['workflow_type'] is q.Workflow
        assert not (directory/'transport').exists()
        return dict(tasks_observed=True)
    monkeypatch.setattr(runner,'observe',observe)
    result=runner.execute_prepared(args,plan,requests,directory=tmp_path/'run',
        preparation=prep,event_source=Events(),backend=q)
    assert result['tasks_observed']


def test_frozen_helpers_change_candidate_identity(tmp_path):
    from pathlib import Path
    import shutil
    root=Path(q.old.ROOT)
    for name in q.SOURCE_FILES:
        dest=tmp_path/name; dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(root/name,dest)
    shutil.copytree(root/q.base.ASSETS,tmp_path/q.base.ASSETS)
    before=q.candidate_identity(root=tmp_path)
    for name in ('app/evaluation/golden_review_experiment.py','app/evaluation/golden_inference_coverage.py',
                 'app/evaluation/golden_inference_scope_v5.py','app/providers/models.py',
                 'app/evaluation/coach_report.py','app/report_validation.py'):
        path=tmp_path/name; path.write_text(path.read_text(encoding='utf-8')+'\n# changed helper\n',encoding='utf-8')
        after=q.candidate_identity(root=tmp_path)
        assert after!=before
        assert after['revision_source_sha256'][name]!=before['revision_source_sha256'][name]
        before=after
