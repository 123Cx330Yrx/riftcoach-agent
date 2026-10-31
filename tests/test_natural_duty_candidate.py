"""Real product assembly with scripted models, local retrieval, no network."""
from dataclasses import replace
import json
from pathlib import Path
import re
import socket

import pytest

from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.natural_duty_contract import CONTRACT, MODEL, VERSION, NaturalDutyProvider, request_sha
from app.evaluation.natural_duty_contract import make_request, request_bytes, role_for_request
from app.evaluation.golden_native_issues_review import build_inputs
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.coach_contract import ROLE_COACH_CONTRACT, require_coach_contract
from app.product.natural_duty_candidate import build_natural_duty_candidate
from app.product.recent_review import RecentReviewProductRequest
from app.product.run_receipts import FileRunReceiptStore
from app.product.recent_review_service import RecentReviewApplicationError
from app.providers.models import ChatResponse, ToolCall, TokenUsage
from app.providers.errors import ProviderResponseError
from app.providers.zhipu_profiles import ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.store import RuntimeTraceStore
from app.runtime.dispatch_control import bind_dispatch_guard, DispatchStopped
from scripts import review_duty_composition as duty
from tests.test_native_editor_product_budget import ScriptedProductProvider, SummaryBuilder
from tests.test_coarse_revision_editor import cases, BEFORE, AFTER


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*a, **k):
        raise AssertionError('natural duty tests cannot connect')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)


class Responses(ScriptedProductProvider):
    def __init__(self, *, reviewer=False, mode='repair', extra_round=False, fault=None):
        super().__init__(recover=False, charge_ceiling=False)
        self.req = cases()['claim-scope:4'][0]
        self.mode, self.extra_round, self.fault = mode, extra_round, fault
        if reviewer:
            self.model_name = 'glm-5.3'
            self.thinking_profile_id = ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE.profile_id

    def chat(self, request):
        self.requests.append(request)
        marker = request.metadata.get(duty.MARKER)
        if marker is None:
            iteration = request.metadata['agent_loop_iteration']
            rounds = 2 if self.extra_round else 1
            if iteration <= rounds:
                queries = ('早期死亡', '补刀与经济', '避免伪精确目标',
                    '可执行性 训练计划 可观察目标 观察周期 复盘方式',
                    '证据分层 比赛统计 时间线 录像 事实 相关性 复盘假设') if iteration==1 else ('补刀',)
                calls = tuple(ToolCall(id=f'knowledge-{iteration}-{n}', name='knowledge.search',
                    arguments={'query': q, 'top_k':1}) for n,q in enumerate(queries))
                response = ChatResponse(provider='zhipu', model=self.model_name, content=None,
                    tool_calls=calls, finish_reason='tool_calls', usage=TokenUsage(input_tokens=10,output_tokens=10))
            else:
                assert any(m.role.value == 'tool' for m in request.messages)
                response = ChatResponse(provider='zhipu', model=self.model_name, content=self.req.report,
                    finish_reason='stop', usage=TokenUsage(input_tokens=10,output_tokens=10))
        else:
            if self.fault == 'transport':
                raise ProviderResponseError(provider='zhipu', code='connection_failed')
            value = dict(score=95, verdict='pass', issues=[], issue_resolutions=[], advisories=[])
            if marker['stage']=='initial':
                value['repairs']=[]
                if self.mode!='pass' and marker['duty']=='facts':
                    data = next(m.content for m in request.messages if (m.content or '').startswith('[UNTRUSTED DATA]\n'))
                    data = json.loads(data.split('\n',1)[1].rsplit('\n[END UNTRUSTED DATA]',1)[0])
                    root = data['source_roots']['roots'][0][0]
                    bad_after = BEFORE.replace('15', '99') if self.mode == 'bad_semantic' else AFTER
                    value.update(score=70, verdict='needs_revision', issues=[dict(block=4,source_ids=[root],
                        severity='medium',category='fact_error',explanation='Scripted diagnostic only.',
                        suggested_correction='Scripted exact repair.')], repairs=[dict(issue_ids=[1],edits={
                        'block_4':[dict(before=BEFORE if self.mode!='bad_anchor' else 'missing synthetic anchor',
                        after=bad_after,reason='Scripted diagnostic only.')]})])
                    if self.mode == 'empty_source_ids':
                        value['issues'][0]['source_ids'] = []
                    elif self.mode == 'wrong_target_block':
                        block = build_inputs(self.req).source.blocks[5][1]
                        value['repairs'][0]['edits'] = {'block_6': [dict(before=block,
                            after=block+' OFFLINE unrelated change.', reason='Scripted wrong target.')]}
                    elif self.mode == 'removed_knowledge_citations':
                        edits = {}
                        for number, (_, block) in enumerate(build_inputs(self.req).source.blocks, 1):
                            after = re.sub(r'\[K\d+\]', '', block).replace(BEFORE, AFTER)
                            if after != block:
                                edits[f'block_{number}'] = [dict(before=block, after=after,
                                    reason='Scripted citation deletion.')]
                        value['repairs'][0]['edits'] = edits
            elif self.mode=='fresh_reject' and marker['duty']=='facts':
                value.update(score=0, verdict='fail')
            response = ChatResponse(provider='zhipu',model=self.model_name,content=None,
                tool_calls=(ToolCall(id='review',name='submit_report_review',arguments=value),),
                finish_reason='tool_calls',usage=TokenUsage(input_tokens=10,output_tokens=10))
        self.last_exchange = Exchange(request,response,request_sha(request))
        if marker and self.fault=='receipt': self.last_exchange=None
        if marker and self.fault=='model': response=replace(response,model='glm-5.3-flash')
        return response


class Factory:
    def __init__(self, **options):
        self.options, self.providers = options, {}
        self.descriptor=self.make()

    def make(self):
        return NaturalDutyProvider(Responses(**self.options), Responses(reviewer=True,**self.options))

    def __call__(self, run_id):
        self.providers[run_id]=self.make()
        return self.providers[run_id]


def application(tmp_path, **options):
    f=Factory(**options)
    app=build_natural_duty_candidate(summary_builder=SummaryBuilder(f.descriptor.generator.req.player_summary),
        provider_factory=f,knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path)
    flows=[]
    original=app._runtime._execution_factory._review_workflow_factory
    def capture(runtime,provider):
        flow=original(runtime,provider); flows.append(flow); return flow
    app._runtime._execution_factory._review_workflow_factory=capture
    return app,f,flows


def run(app):
    return app.review(RecentReviewProductRequest(riot_id='DK ShowMaker#KR1',routing_region='asia',count=5,queue=420),run_id='candidate')


@pytest.mark.parametrize('mode,calls,outcome',[
    ('repair',6,'candidate_repaired_pass_unqualified'),('pass',4,'candidate_initial_pass_unqualified'),
    ('bad_anchor',4,'candidate_execution_failed'),('fresh_reject',5,'fresh_facts_rejected')])
def test_actual_application_chain_and_publication_closed(tmp_path,mode,calls,outcome):
    app,f,flows=application(tmp_path,mode=mode)
    result=run(app)
    assert len(flows)==1, result
    flow=flows[0]
    assert flow.outcome==outcome, (flow.outcome,result)
    assert len(f.providers['candidate'].attempts)==flow.send.provider.calls==calls
    assert result.publication_status.value=='rejected' and (result.output is None or result.output.report is None)
    assert FileRunReceiptStore(tmp_path).read_receipt('candidate').report_available is False
    trace=RuntimeTraceStore(tmp_path,'candidate').read_trace(result.trace_reference)
    assert trace.identity.coach_contract==CONTRACT.snapshot() and trace.identity.provider_model==MODEL
    assert trace.usage.provider_calls_attempted==calls
    assert trace.usage.input_tokens==trace.usage.output_tokens==10*calls
    if mode=='repair':
        assert flow.assembly.report==f.descriptor.generator.req.report.replace(BEFORE,AFTER)
        assert (flow.journal_root/'application.json').exists()
        fresh=[r for r in f.providers['candidate'].reviewer.requests if r.metadata[duty.MARKER]['stage']=='fresh']
        assert len(fresh)==2 and fresh[0].messages[1:]==fresh[1].messages[1:]
        assert all('repairs' not in r.tools[0].input_schema['properties'] for r in fresh)
        assert all('Scripted diagnostic only.' not in str(r.messages) for r in fresh)


def test_extra_tool_round_stops_before_application_or_any_fresh(tmp_path):
    app,f,flows=application(tmp_path,extra_round=True)
    run(app)
    assert flows[0].outcome=='insufficient_fresh_call_slots'
    assert len(f.providers['candidate'].attempts)==5
    assert not (flows[0].journal_root/'application.json').exists()


@pytest.mark.parametrize('fault',['transport','receipt','model'])
def test_failure_preserves_attempts_and_stops_without_retry(tmp_path,fault):
    app,f,flows=application(tmp_path,fault=fault)
    result=run(app)
    assert len(f.providers['candidate'].attempts)==3
    assert flows[0].outcome=='candidate_execution_failed'
    assert result.publication_status.value=='rejected'
    budget=flows[0].send.provider
    assert budget.stopped
    if fault in ('transport','model'): assert budget.reserved_tokens>0


@pytest.mark.parametrize('stop_after',[1,4,5])
def test_real_dispatch_fence_stops_next_send_with_trace(tmp_path,stop_after):
    app,f,flows=application(tmp_path)
    def guard():
        if len(f.providers['candidate'].attempts)>=stop_after: raise DispatchStopped('offline stop')
    with bind_dispatch_guard(guard):
        try:
            result=run(app)
        except RecentReviewApplicationError as error:
            assert error.run_id == 'candidate'
            result = None
    assert len(f.providers['candidate'].attempts)==stop_after
    receipt = FileRunReceiptStore(tmp_path).read_receipt('candidate')
    trace=RuntimeTraceStore(tmp_path,'candidate').read_trace(receipt.trace_reference)
    assert trace.usage.provider_calls_attempted==stop_after
    assert not receipt.report_available
    assert result is None or result.output is None or result.output.report is None
    budget = flows[0].send.provider
    assert budget.calls == stop_after and budget.tokens == 20 * stop_after
    assert budget.reserved_tokens == 0 and budget.stopped
    outcome_path = flows[0].journal_root/'outcome.json'
    if outcome_path.exists():
        outcome = json.loads(outcome_path.read_bytes())
        assert outcome['calls'] == stop_after
        assert outcome['known_tokens'] == 20 * stop_after
        assert outcome['unknown_reserved_tokens'] == 0


def budget_fixture(clock=lambda: 0):
    provider = Factory().make()
    request = make_request(build_inputs(provider.generator.req), 'facts', 'fresh')
    return CoachBudgetedProvider(provider, coach_contract=CONTRACT, clock=clock), provider, request


def test_seventh_call_rejected_before_send():
    budget, provider, request = budget_fixture()
    for _ in range(6):
        budget.chat(request)
    with pytest.raises(ProviderResponseError, match='external_call_budget_exhausted'):
        budget.chat(request)
    assert budget.calls == len(provider.attempts) == 6
    assert budget.tokens == 120 and budget.reserved_tokens == 0


def test_whole_task_deadline_clamps_then_refuses():
    now = [0]
    budget, provider, request = budget_fixture(lambda: now[0])
    now[0] = 850
    budget.chat(request)
    assert provider.reviewer.requests[0].timeout_s == 50
    now[0] = 900
    with pytest.raises(ProviderResponseError, match='timeout'):
        budget.chat(request)
    assert len(provider.attempts) == budget.calls == 1


@pytest.mark.parametrize('field', ['tokens', 'reserved_tokens'])
def test_known_and_unknown_usage_both_limit_admission(field):
    budget, provider, request = budget_fixture()
    setattr(budget, field, 401919)
    with pytest.raises(ProviderResponseError, match='token_budget_exhausted'):
        budget.chat(request)
    assert not provider.attempts and budget.calls == 0
    assert getattr(budget, field) == 401919


def test_identity_and_old_time600_cannot_mix():
    from app.evaluation.document_review_timing_adapter import METADATA
    from scripts import review_duty_direct_patch as direct
    budget, provider, request = budget_fixture()
    with pytest.raises(ValueError): ROLE_COACH_CONTRACT.require_provider(provider)
    with pytest.raises(ValueError): require_coach_contract(replace(CONTRACT, version='1.5.0'))
    with pytest.raises(ValueError): request_bytes(replace(request, timeout_s=600))
    with pytest.raises(ValueError): request_bytes(replace(request, metadata={**request.metadata, METADATA: {}}))
    with pytest.raises(ValueError): request_bytes(direct.review_request(build_inputs(provider.generator.req), 'facts'))
    with pytest.raises(ValueError): role_for_request(replace(request, metadata={'agent_loop_iteration': True, 'evaluation_policy_id': VERSION}))
    with pytest.raises(ValueError): request_bytes(request, transport_id='old-transport')
    assert not provider.attempts


def test_terminal_workflow_cannot_reopen_or_rewrite_evidence(tmp_path):
    app, f, flows = application(tmp_path, mode='pass')
    run(app)
    flow = flows[0]
    before = {p.name:p.read_bytes() for p in flow.journal_root.iterdir()}
    with pytest.raises(ValueError): flow.evaluate(f.descriptor.generator.req)
    with pytest.raises(ValueError): flow.revise(None)
    with pytest.raises(ValueError): flow.stop('pretend_success')
    assert before == {p.name:p.read_bytes() for p in flow.journal_root.iterdir()}
    assert len(f.providers['candidate'].attempts) == 4


@pytest.mark.parametrize('mode', ['bad_semantic', 'empty_source_ids', 'wrong_target_block',
                                  'removed_knowledge_citations'])
def test_structurally_valid_semantic_gaps_stay_unqualified_after_both_fresh_pass(tmp_path, mode):
    app, f, flows = application(tmp_path, mode=mode)
    result = run(app)
    flow = flows[0]
    assert flow.outcome == 'candidate_repaired_pass_unqualified'
    assert flow.assembly.report != flow.original.source.report
    assert result.publication_status.value == 'rejected'
    assert result.output is None or result.output.report is None
    assert len(f.providers['candidate'].attempts) == 6
    assert not FileRunReceiptStore(tmp_path).read_receipt('candidate').report_available
    outcome = json.loads((flow.journal_root/'outcome.json').read_bytes())
    assert not outcome['host_semantics_verified'] and not outcome['publication_allowed']
    fresh = [r for r in f.providers['candidate'].reviewer.requests
             if r.metadata[duty.MARKER]['stage'] == 'fresh']
    assert len(fresh) == 2
    for name, request in zip(duty.DUTIES, fresh):
        assert request.messages == make_request(flow.expected_fresh, name, 'fresh').messages
    if mode == 'bad_semantic':
        assert BEFORE.replace('15', '99') in flow.assembly.report
    elif mode == 'wrong_target_block':
        assert BEFORE in flow.assembly.report and AFTER not in flow.assembly.report
    elif mode == 'removed_knowledge_citations':
        assert re.search(r'\[K\d+\]', flow.original.source.report)
        assert not re.search(r'\[K\d+\]', flow.assembly.report)
    else:
        raw = json.loads((flow.journal_root/'facts-initial.json').read_bytes())['raw']
        assert json.loads(raw)['issues'][0]['source_ids'] == []


def test_corrupt_program_manifest_stops_before_provider(tmp_path, monkeypatch):
    import shutil
    import app.product.natural_duty_candidate as candidate
    from app.prompt_program.catalog import PromptProgramCatalogError
    assets = tmp_path/'assets'
    shutil.copytree(candidate.ASSETS, assets)
    skill = assets/'skills/recent-form-review/SKILL.md'
    skill.write_text(skill.read_text(encoding='utf-8')+'\nChanged policy.\n', encoding='utf-8')
    monkeypatch.setattr(candidate, 'ASSETS', assets)
    with pytest.raises(PromptProgramCatalogError): application(tmp_path)
    assert not (tmp_path/'candidate').exists()


@pytest.mark.parametrize('tamper', ['revision_report', 'revision_source', 'fresh_report'])
def test_changed_report_or_source_cannot_reach_fresh_send(tmp_path, tamper):
    app, f, flows = application(tmp_path)
    factory = app._runtime._execution_factory
    original_factory = factory._review_workflow_factory
    def intercepted(runtime, provider):
        flow = original_factory(runtime, provider)
        revise = flow.revise
        def changed(request):
            if tamper == 'revision_report':
                request = replace(request, report=request.report+' changed')
            if tamper == 'revision_source':
                request = replace(request, deterministic_report=request.deterministic_report+' changed')
            draft = revise(request)
            return replace(draft, report=draft.report+' changed') if tamper == 'fresh_report' else draft
        flow.revise = changed
        return flow
    factory._review_workflow_factory = intercepted
    result = run(app)
    assert result.publication_status.value == 'rejected'
    assert len(f.providers['candidate'].attempts) == 4
    assert flows[0].outcome in ('candidate_application_failed', 'candidate_execution_failed')


def test_trace_rejects_forged_candidate_snapshot(tmp_path):
    from app.runtime.models import RuntimeTrace
    from pydantic import ValidationError
    app, _, _ = application(tmp_path, mode='pass')
    result = run(app)
    trace = RuntimeTraceStore(tmp_path, 'candidate').read_trace(result.trace_reference)
    value = trace.model_dump(mode='json')
    for key in ('identity', 'policy'):
        value[key]['coach_contract']['sha256'] = '0'*64
    with pytest.raises(ValidationError, match='trusted contract'):
        RuntimeTrace.model_validate(value)
