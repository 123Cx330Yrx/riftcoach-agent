"""Prospective observer with real receipt machinery and offline replies."""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.role_qualification import frozen_cases, replay_case
from app.evaluation import role_task_outcome
from app.providers.models import ChatResponse, TokenUsage
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts import run_role_task_observation as runner
from scripts.run_role_qualification_pair import observe
from scripts import run_role_qualification_pair as pair
from tests.test_role_review_notes import tool_response


@pytest.fixture(scope='module')
def prepared(tmp_path_factory):
    # Executor counterexamples need the current builder's identity ordering;
    # closed previews intentionally preserve the key-sorted historical export.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(runner, 'CLOSED_RESULT', tmp_path_factory.mktemp('open-plan')/'absent.json')
        return runner.prepare()


def test_plan_retains_original15_and_same_product_identity(prepared):
    plan, requests = prepared
    assert len(plan['original15_keys']) == len(set(plan['original15_keys'])) == 15
    assert [r['key'] for r in plan['cases']] == list(runner.KEYS)
    assert plan['identity']['contract']['version']=='1.5.2'
    assert plan['batch_budget']==dict(max_calls=7,max_tokens=677376,max_seconds=2100,
        estimated_uncached_cny='10.006528',hard_billing_cap=False)
    assert not plan['allow_reassessment']
    assert all(b'expected_initial' not in raw for raw in requests.values())


@pytest.mark.parametrize('failure', [None,'wrong_target','mixed_defects','wrong_binding',
    'bad_revision','bad_final','malformed','host_deadline','finish_deadline','accounting_deadline','identity_drift','false_positive','missed_error'])
def test_actual_executor_preserves_failed_initial_and_obeys_stop_branches(prepared,tmp_path,monkeypatch,failure):
    plan = deepcopy(prepared[0])
    # One negative case, except the explicit false-positive counterexample.
    index = 0 if failure=='false_positive' else 1
    plan['cases'] = [plan['cases'][index]]
    plan['case_budgets'] = [plan['case_budgets'][index]]
    sources = {f['key']:s for f,s in frozen_cases()[0]}
    good = dict(score=95,verdict='pass',issues=[],issue_resolutions=[],advisories=[])
    bad = dict(score=82,verdict='needs_revision',issues=[dict(block=4,severity='medium',category='fact_error',
        source_ids=[1],explanation='True target with incidental incorrect explanatory number.',
        suggested_correction='Use source-supported metric directions.')],issue_resolutions=[],advisories=[])
    first = good if failure=='missed_error' else deepcopy(bad)
    if failure=='malformed':
        del first['score']
    queue = [tool_response(first),ChatResponse(content=sources['claim-scope:1'].report,
        provider='zhipu',model='glm-5.3-flash',finish_reason='stop',usage=TokenUsage(10,10)),tool_response(good)]
    issued = []
    def child(command,raw,*,directory,timeout_s,environ,transport_id):
        issued.append(json.loads(raw))
        reply = queue.pop(0)
        write_new_json(directory/'result.json',dict(state='complete',transport_id=transport_id))
        return reply
    monkeypatch.setattr(bridge,'run_child',child)
    def settings(model):
        return NS(model=model,api_key='offline-only',base_url='https://open.bigmodel.cn/api/paas/v4')
    factory = RunScopedRoleReceiptedProviderFactory(generator_settings=settings('glm-5.3-flash'),
        reviewer_settings=settings('glm-5.3'),transport_root=tmp_path/'transport')
    now = [0.0]
    if failure=='accounting_deadline':
        original_summary = pair.summarize_calls
        def slow_summary(directory):
            result = original_summary(directory)
            now[0]=901
            return result
        monkeypatch.setattr(pair,'summarize_calls',slow_summary)
    def adjudicate(path,remaining):
        stage = json.loads(path.read_text(encoding='utf-8'))
        name = stage['stage']
        accepted = name!='initial' and not (
            failure=='bad_revision' and name=='revision' or failure=='bad_final' and name=='final')
        defects = [] if accepted else [dict(kind='unsupported_explanation',detail='Synthetic source adjudication only.')]
        if failure=='mixed_defects' and name=='initial':
            defects.append(dict(kind='wrong_correction',detail='A correction instruction is false.'))
        result = dict(response_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),accepted=accepted,
            key=plan['cases'][0]['key'],input_sha256=plan['cases'][0]['input_sha256'],
            candidate_sha256=digest(compact(plan['identity'])),target_and_correction_valid=failure!='wrong_target',
            assessment=dict(stage=name,stage_sha256=runner.stage_identity(stage),reviewer='offline-host',
                source_review='Synthetic structural counterexample; never model quality evidence.',accepted=accepted,defects=defects),
            final_report=None if name=='initial' else dict(report_sha256=digest(stage['report']),
                reviewer='offline-host',source_review='Synthetic full-report assertion.',facts_and_sources_correct=True,
                correct_content_preserved=True,identity_and_goal_preserved=True,true_errors_fixed=True))
        if failure=='wrong_binding':
            result['assessment']['stage_sha256']='0'*64
        if failure=='host_deadline':
            now[0]=901
        if failure=='identity_drift' and name=='final':
            changed = deepcopy(plan['identity'])
            changed['manifest_sha256']='0'*64
            monkeypatch.setattr(role_task_outcome,'candidate_identity',lambda:changed)
        return result
    class SlowObserver(runner.Observer):
        @staticmethod
        def finish(*args):
            result = runner.Observer.finish(*args)
            now[0] = 901
            return result
    result = observe(factory,tmp_path,plan,adjudicate=adjudicate,clock=lambda:now[0],
        workflow_type=runner.Workflow,replay=replay_case,success_field='tasks_observed',
        task_observer=SlowObserver if failure=='finish_deadline' else runner.Observer)
    assert result['tasks_observed'] is (failure is None), (result.get('error_code'), result.get('error_type'))
    expected_calls = 3 if failure in (None,'bad_final','finish_deadline','accounting_deadline','identity_drift') else 2 if failure=='bad_revision' else 1
    assert len(issued)==expected_calls
    assert 'qualification_row' not in result['cases'][0]
    assert not result['review_controls_qualified'] and not result['production_admitted']
    if failure is None:
        outcome = json.loads((tmp_path/'claim-scope-4/task-observation.json').read_text(encoding='utf-8'))
        assert not outcome['reviewer_quality'] and outcome['task_outcome']
        assert outcome['assessment']['stages'][0]['accepted'] is False
        final = json.JSONDecoder().raw_decode(issued[2]['messages'][1]['content'].split('[UNTRUSTED DATA]\n',1)[1])[0]
        assert not {'accepted_review','previous_review','previous_issues'} & final.keys()
    if failure=='malformed':
        assert result['error_code']=='task_observation_reassessment_forbidden'
    if failure=='accounting_deadline':
        assert result['cases'][0]['status']=='failed'
        assert result['cases'][0]['elapsed_seconds']==901
        assert not result['cases'][0]['continuous_observation_budget_verified']


def test_closed_or_wrong_preparation_never_reads_keys_or_ci(prepared,monkeypatch,tmp_path):
    monkeypatch.setattr(runner,'load_role_settings',lambda *_:pytest.fail('credentials accessed'))
    monkeypatch.setattr(runner,'verify_public_ci',lambda *_:pytest.fail('CI accessed'))
    monkeypatch.setattr(runner,'RUN_DIRECTORY',tmp_path/'new')
    monkeypatch.setattr(runner,'CLOSED_RESULT',tmp_path/'closed')
    monkeypatch.setattr(runner,'prepare',lambda:prepared)
    with pytest.raises(ValueError,match='preparation_required'):
        runner.run(NS(execute=True,env_file=tmp_path/'unused',ci_run='x',plan_sha='bad'))
    (tmp_path/'closed').write_text('{}')
    monkeypatch.setattr(runner,'prepare',lambda:pytest.fail('closed batch prepared'))
    with pytest.raises(ValueError,match='batch_closed_or_exists'):
        runner.run(NS(execute=True))


def test_closed_preview_retains_executed_plan_and_request_bytes(monkeypatch):
    monkeypatch.setattr(runner,'prepare_qualification',lambda:pytest.fail('historical preview used current identity'))
    plan,requests = runner.prepare()
    assert plan == json.loads(runner.PREPARATION.read_text(encoding='utf-8'))
    assert runner.canonical_sha(plan) == '6a04b8f45de649c003a7288c65081fb83e505b0f1b5a3a0d55e3792685c2d953'
    evidence = json.loads(runner.CLOSED_RESULT.read_text(encoding='utf-8'))
    for key,raw in requests.items():
        assert hashlib.sha256(raw).hexdigest() == evidence['original_file_sha256'][key.replace(':','-')+'-prepared-request.json']
    assert runner.run(NS(execute=False,output=None))['historical_closed']


def test_closed_preview_rejects_modified_export(monkeypatch,tmp_path):
    changed = tmp_path/'changed.json'
    changed.write_bytes(runner.CLOSED_RESULT.read_bytes()+b'\n')
    monkeypatch.setattr(runner,'CLOSED_RESULT',changed)
    with pytest.raises(ValueError,match='historical_evidence_changed'):
        runner.prepare()
