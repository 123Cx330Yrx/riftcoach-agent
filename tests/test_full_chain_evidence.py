"""Offline transport and native-event fixtures; real author-file/CLI/import IO."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.providers.models import ChatResponse, ToolCall, TokenUsage
from scripts.full_chain_evidence import FullChainEvidence, ROOT
from scripts.full_chain_modules import private_module
from scripts import full_chain_observed_transport as observed
from scripts.role_development_host_clock import DevelopmentHostClock
from scripts.codex_review_event_source import CodexHostReviewEventSource
from tests.test_coarse_revision_editor import cases, BEFORE, AFTER


@pytest.fixture(scope='module')
def controls():
    from scripts.run_full15_resumption_candidate import controls
    rows, variants = controls()
    return [v for v in variants if v[0]['key'] in ('claim-scope:4', 'claim-scope:1')][::-1]


def setup(tmp_path, monkeypatch, controls, fault=None, fault_stage='initial'):
    def forbidden(*args, **kwargs):
        raise AssertionError('offline test attempted network')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    directory = tmp_path / 'run'
    directory.mkdir()
    session = FullChainEvidence(directory=directory, answers=tmp_path/'answers', observations=tmp_path/'observations')
    runner, evidence = session.runner, session.evidence
    runner.controls = lambda root=ROOT: ([v[0] for v in controls], controls)
    plan = session.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent')
    # Freeze this explicit two-case OFFLINE plan; source-plan rebuild is covered
    # separately. Avoid rebuilding complete prompts at every inventory poll.
    runner.prepare = lambda **kwargs:deepcopy(plan)
    runner._write_json(directory/'plan.json', dict(preparation_plan=plan, plan_sha256=runner.canonical_sha(plan)))
    wall = NS(now=0)
    runner.DevelopmentHostClock = lambda directory, **kwargs: DevelopmentHostClock(directory, wall_clock=lambda:wall.now, **kwargs)
    sent, turns = [], []
    parent_bridge = private_module(bridge.__file__, {})

    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        request = bridge.REQUEST.validate_json(raw)
        sent.append(request)
        phase = request.metadata['review_phase']
        stage = ('initial', 'revision', 'final')[min(len(sent), 3)-1]
        wall.now += 450 if len(sent) == 1 else 100
        if phase == 'native_business_revision':
            model, tool = 'glm-5.3-flash', 'submit_block_edits'
            args = dict(edits={'block_4':[dict(before=BEFORE,after=AFTER,reason='OFFLINE author edit')]})
        else:
            model, tool = 'glm-5.3', 'submit_report_review'
            args = json.loads(cases()['claim-scope:4'][3]) if len(sent) == 1 else dict(
                score=96, verdict='pass', issues=[], issue_resolutions=[], advisories=[])
        if fault == 'deadline' and stage == fault_stage:
            wall.now += 901
        side = session.observations / __import__('hashlib').sha256(str(directory.resolve()).encode()).hexdigest()
        if not (fault == 'missing_observation' and stage == fault_stage):
            side.mkdir(parents=True)
            runner._write_json(side/'binding.json', dict(version=observed.VERSION,transport_id=transport_id,
                request_sha256=runner._bytes_sha(raw),worker_directory=str(directory.resolve()),
                route=dict(route='direct',destination_host='open.bigmodel.cn',process_proxy_present=False,
                           no_proxy_matches_host=True,system_network_path_proven=False)))
            runner._write_json(side/'parent-audit.json', dict(transport_complete=True,observation_valid=True,
                files={'binding.json':runner._sha(side/'binding.json')}, fixture='OFFLINE synthetic observation'))
        runner._write_json(directory/'result.json',dict(state='complete',elapsed_ms=0,transport_id=transport_id))
        return ChatResponse(provider='zhipu',model=model,content=None,finish_reason='tool_calls',
            usage=TokenUsage(20,10),tool_calls=(ToolCall(id='OFFLINE',name=tool,arguments=args),))
    parent_bridge.run_child = child
    monkeypatch.setattr(observed, 'isolated_bridge', lambda **kwargs:parent_bridge)
    settings = lambda model:NS(model=model,api_key='OFFLINE',base_url='https://open.bigmodel.cn/api/paas/v4')
    factory = session.factory(generator_settings=settings('glm-5.3-flash'), reviewer_settings=settings('glm-5.3'))

    def native(method, params):
        if fault == 'native_pollution' and turns and turns[0]['id'].endswith('-' + fault_stage):
            (directory/'unexpected.json').write_text('{}')
        if method == 'thread/read':
            return dict(thread=dict(id='synthetic-independent',parentThreadId='synthetic-root',
                source=dict(subAgent=dict(thread_spawn=dict(parent_thread_id='synthetic-root')))))
        assert method == 'thread/turns/list'
        return dict(data=turns, nextCursor=None)
    source = CodexHostReviewEventSource(NS(request=native),plan)

    def judge(path, remaining):
        bound = evidence.read(path)['binding']; stage = bound['stage']; folder = path.parent
        pin = session.publish_task(path)
        required = evidence.read(path)
        def opinion(role):
            reviewer = plan['review_principals'][role]['principal_id']
            accepted = not (fault == 'semantic_reject' and stage == fault_stage and role == 'independent')
            return dict(binding=bound, stage_assessment=dict(stage=stage,stage_sha256=required['stage_sha256'],
                reviewer=reviewer,source_review='OFFLINE fixture, no semantic proof',accepted=accepted,
                defects=[] if accepted else [dict(kind='wrong_correction',detail='OFFLINE defect')]),
                report_assessment=None if stage == 'initial' else dict(report_sha256=bound['report_sha256'],
                    reviewer=reviewer,source_review='OFFLINE fixture',facts_and_sources_correct=True,
                    correct_content_preserved=True,identity_and_goal_preserved=True,true_errors_fixed=True))
        target = session.workspace.answer_path(folder/'task-checkpoint.json',pin)
        answer = dict(binding=bound, review=opinion('independent'))
        with target.open('x',encoding='utf8') as stream:
            json.dump(answer,stream,ensure_ascii=False,indent=2)
        checked = subprocess.run([sys.executable,'-B','-m','scripts.host_review_task_checkpoint','check-answer',
            '--checkpoint',str(folder/'task-checkpoint.json'),'--checkpoint-sha',pin,'--answer-file',str(target)],
            cwd=ROOT,capture_output=True)
        assert checked.returncode == 0, checked.stderr.decode('utf8')
        text = target.read_text(encoding='utf8')
        turn_id = bound['key'].replace(':','-') + '-' + stage
        turns.insert(0,dict(id=turn_id,status='completed',itemsView='full',error=None,items=[
            dict(id='dispatch',type='userMessage',content=[dict(type='text',text=evidence.task(directory,bound['key'],stage))]),
            dict(id='final',type='agentMessage',phase='final_answer',text=text)]))
        if stage == fault_stage:
            if fault == 'pollution': (folder/'answer.json').write_text(text,encoding='utf8')
            if fault == 'author_drift': target.write_text(text+' ',encoding='utf8')  # raw SHA pinned after submit below
            if fault == 'answer_mismatch':
                answer['review']['stage_assessment']['source_review']='CHANGED'
                target.write_text(json.dumps(answer),encoding='utf8')
            if fault == 'checkpoint': pin='0'*64
        notes = opinion('primary'); notes.pop('binding')
        evidence.submit(directory,bound['key'],stage,notes,'synthetic-independent/'+turn_id+'/final',source,pin)
        if stage == fault_stage and fault == 'author_drift': target.write_text(text+'  ',encoding='utf8')
        if stage == fault_stage and fault == 'observation_drift':
            next(session.observations.glob('*/binding.json')).write_text('{}')
        wall.now += 5000
        return evidence.read(folder/'review-submission.json')
    return session,plan,factory,source,judge,sent


def test_complete_three_stages_real_author_io_and_strict_readonly_seal(tmp_path,monkeypatch,controls):
    session,plan,factory,source,judge,sent=setup(tmp_path,monkeypatch,controls)
    result=session.runner.observe(factory,session.directory,plan,event_source=source,adjudicate=judge)
    assert result['scan_completed'],json.dumps(result)
    assert len(sent)==4 and [r.timeout_s for r in sent]==[600,300,350,600]
    before=session.snapshot()
    replay=session.evidence.replay(session.directory,event_source=source)
    assert before==session.snapshot()
    assert len(replay['author_evidence'])==4 and len(replay['body_free_observations'])==4
    assert replay['new_qualification']==0
    session.evidence.seal(session.directory,tmp_path/'seal.json',event_source=source)
    with pytest.raises(FileExistsError): session.evidence.seal(session.directory,tmp_path/'seal.json',event_source=source)
    with pytest.raises(ValueError,match='seal_inside_evidence'):
        session.evidence.seal(session.directory,session.workspace.answers/'seal.json',event_source=source)
    with pytest.raises(ValueError,match='task_path'):
        session.publish_task(tmp_path/'elsewhere/review-required.json')
    (session.observations/'orphan').mkdir()
    with pytest.raises(ValueError,match='orphan_observation'): session.check()


@pytest.mark.parametrize('stage',['initial','revision','final'])
@pytest.mark.parametrize('fault',['pollution','native_pollution','answer_mismatch','author_drift','checkpoint','missing_observation','observation_drift','deadline'])
def test_hard_fault_stops_all_later_sends(tmp_path,monkeypatch,controls,stage,fault):
    session,plan,factory,source,judge,sent=setup(tmp_path,monkeypatch,controls,fault,stage)
    result=session.runner.observe(factory,session.directory,plan,event_source=source,adjudicate=judge)
    assert not result['scan_completed'],result
    assert len(sent)==('initial','revision','final').index(stage)+1,result
    assert result['unexecuted_keys']==plan['sequence'][1:]
    if fault not in ('checkpoint','deadline'):
        with pytest.raises((ValueError,OSError)):
            session.evidence.replay(session.directory,event_source=source)


@pytest.mark.parametrize('stage',['initial','revision','final'])
def test_semantic_rejection_continues_next_independent_case(tmp_path,monkeypatch,controls,stage):
    session,plan,factory,source,judge,sent=setup(tmp_path,monkeypatch,controls,'semantic_reject',stage)
    result=session.runner.observe(factory,session.directory,plan,event_source=source,adjudicate=judge)
    assert result['scan_completed'] and not result['diagnostic_accepted'],result
    assert len(sent)==('initial','revision','final').index(stage)+2
    assert session.evidence.replay(session.directory,event_source=source)['new_qualification']==0


def test_legacy_modules_are_not_mutated(tmp_path):
    from scripts import run_full15_resumption_candidate as old_runner, full15_resumption_evidence as old_evidence
    before=(old_runner.prepare,old_runner.observe,old_evidence.submit,old_evidence.runner)
    FullChainEvidence(directory=tmp_path/'run',answers=tmp_path/'answers',observations=tmp_path/'obs')
    assert before==(old_runner.prepare,old_runner.observe,old_evidence.submit,old_evidence.runner)


def test_preparation_paths_and_frozen_scope_without_execution(tmp_path):
    session=FullChainEvidence(directory=tmp_path/'run',answers=tmp_path/'answers',observations=tmp_path/'obs')
    preflight=session.execution_paths_preflight()
    assert preflight['provider_calls']==0 and not preflight['execution_ready']
    plan=session.prepare(root_thread_id='synthetic-root',independent_thread_id='synthetic-independent')
    assert len(plan['sequence'])==15 and plan['run_id']=='document-full-chain-prospective-v1'
    assert plan['per_case_budget']==dict(max_calls=5,max_tokens=401920,max_active_seconds=900)
    assert not plan['execution_authorized'] and not session.directory.exists()
    session.directory.mkdir()
    legacy=deepcopy(plan);legacy['kind']='legacy'
    session.runner._write_json(session.directory/'plan.json',dict(preparation_plan=legacy,
        plan_sha256=session.runner.canonical_sha(legacy)))
    with pytest.raises(ValueError,match='plan_changed'):session.check()
    assert not (session.directory/'submission-close.lock').exists()
    with pytest.raises(ValueError,match='directory_changed'):session.evidence.load_plan(tmp_path/'other')
    with pytest.raises(ValueError,match='scope'):
        session.prepare(root_thread_id='root',independent_thread_id='child',timing_mode='legacy')
    with pytest.raises(ValueError):
        FullChainEvidence(directory=tmp_path/'run',answers=tmp_path/'run/answers',observations=tmp_path/'obs')
