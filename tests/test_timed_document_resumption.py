"""New timing through existing native/checkpoint/replay core, offline only."""
import json
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation import document_review_timing_adapter as timing
from app.evaluation.document_review_timed_transport import TimedDocumentProviderFactory
from app.providers.models import ChatResponse, ToolCall, TokenUsage
from scripts import run_full15_resumption_candidate as runner
from scripts import full15_resumption_evidence as evidence
from scripts.role_development_host_clock import DevelopmentHostClock
from tests.test_full15_resumption_evidence import Host
from tests.test_coarse_revision_editor import cases, BEFORE, AFTER


@pytest.fixture(scope='module')
def original_controls():
    return runner.controls()


def setup(tmp_path, monkeypatch, original_controls, fault=None):
    rows, variants = original_controls
    wanted = ['claim-scope:4', next(r['key'] for r in rows if r['expected_initial'] == 'accept')]
    by_key = {v[0]['key']: v for v in variants}
    selected = [by_key[k] for k in wanted]
    monkeypatch.setattr(runner, 'controls', lambda root=runner.ROOT: ([v[0] for v in selected], selected))
    # Small public subset for engineering evidence, never a live plan or quality sample.
    plan = runner.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent', timing_mode='time600')
    runner._write_json(tmp_path / 'plan.json', dict(preparation_plan=plan, plan_sha256=runner.canonical_sha(plan)))
    wall = NS(now=0)
    monkeypatch.setattr(runner, 'DevelopmentHostClock', lambda directory, **kwargs:
        DevelopmentHostClock(directory, wall_clock=lambda: wall.now, **kwargs))
    calls = []
    initial = json.loads(cases()['claim-scope:4'][3])
    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        request = bridge.REQUEST.validate_json(raw)
        calls.append(request)
        phase = request.metadata['review_phase']
        if fault == 'transport':
            wall.now += 600
            raise RuntimeError('Synthetic unavailable transport')
        if fault == 'progress':
            wall.now += 450
            runner._write_json(directory / 'progress.json', bridge.TimedReviewBridgeObservation(
                state='incomplete', elapsed_ms=450000, input_tokens=20, output_tokens=10).model_dump(mode='json'))
            raise RuntimeError('Synthetic interrupted transport with usage')
        if phase == 'native_business_revision':
            model, tool = 'glm-5.3-flash', 'submit_block_edits'
            args = dict(edits={'block_4': [dict(before=BEFORE, after=AFTER, reason='Synthetic necessary replacement')]})
            wall.now += 100
        else:
            model, tool = 'glm-5.3', 'submit_report_review'
            args = initial if len(calls) == 1 else dict(score=96, verdict='pass', issues=[], issue_resolutions=[], advisories=[])
            wall.now += 450 if len(calls) == 1 else 200
        if fault == 'late' and len(calls) == 3:
            wall.now += 151
        runner._write_json(directory / 'result.json', dict(state='complete', elapsed_ms=0, transport_id=transport_id))
        return ChatResponse(provider='zhipu', model=model, finish_reason='tool_calls', content=None,
            usage=TokenUsage(20,10), tool_calls=(ToolCall(id='fixture', name=tool, arguments=args),))
    monkeypatch.setattr(bridge, 'run_child', child)
    settings = lambda model: NS(model=model, api_key='OFFLINE_FIXTURE', base_url='https://open.bigmodel.cn/api/paas/v4')
    factory = TimedDocumentProviderFactory(generator_settings=settings('glm-5.3-flash'),
        reviewer_settings=settings('glm-5.3'), transport_root=tmp_path / 'transport')
    host = Host(plan, tmp_path, fault if fault in ('checkpoint', 'identity', 'abort', 'final_reject') else None)
    def judge(path, remaining):
        wall.now += 5000
        task = json.loads(evidence.task(tmp_path, evidence.read(path)['binding']['key'], evidence.read(path)['binding']['stage']))
        assert timing.TIMED_MARKER in task['instructions'] or timing.TIMED_IDENTITY in task['instructions'] or 'VERIFIED BUSINESS-POLICY' in task['instructions']
        return host.adjudicate(path, remaining)
    return plan, factory, host, judge, calls


def test_timed_plan_has_separate_identity_and_original_sources(original_controls, monkeypatch):
    monkeypatch.setattr(runner, 'controls', lambda root=runner.ROOT: original_controls)
    legacy = runner.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent')
    new = runner.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent', timing_mode='time600')
    assert new['run_id'] != legacy['run_id'] and new['sequence'] == legacy['sequence']
    assert new['request_timing_identity'] == timing.TIMED_IDENTITY
    assert new['per_case_budget'] == dict(max_calls=5, max_tokens=401920, max_active_seconds=900)
    assert new['budget']['max_active_seconds'] == 13500
    assert new['budget']['max_calls'] == 45 and new['budget']['max_tokens'] == legacy['budget']['max_tokens']
    assert new['execution_authorized'] is new['execution_ready'] is False
    for a, b in zip(legacy['cells'], new['cells'], strict=True):
        assert {k:v for k,v in a.items() if k != 'candidate_request_sha256'} == {k:v for k,v in b.items() if k != 'candidate_request_sha256'}
        assert a['candidate_request_sha256'] != b['candidate_request_sha256']


@pytest.mark.parametrize('fault', [None, 'final_reject', 'transport', 'progress', 'checkpoint', 'identity', 'abort', 'late'])
def test_timed_native_checkpoint_case_clocks_and_strict_replay(tmp_path, monkeypatch, original_controls, fault):
    plan, factory, host, judge, calls = setup(tmp_path, monkeypatch, original_controls, fault)
    result = runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=judge)
    assert not result.get('accounting_error_type'), result
    rebuilt = evidence.replay(tmp_path, event_source=host)
    assert rebuilt['new_qualification'] == 0
    if fault in (None, 'final_reject'):
        assert result['scan_completed'] and len(calls) == 4
        assert [r.timeout_s for r in calls] == [600,300,350,600]
        assert result['case_budgets'][0]['finished_active_seconds'] - result['case_budgets'][0]['started_active_seconds'] == 750
        assert result['case_budgets'][1]['calls'] == 1
        assert result['timing']['host_elapsed_seconds'] == 20000
        assert result['diagnostic_accepted'] is (fault is None)
        assert 'claim-scope-4/final/send-start.json' in rebuilt['public_json_contents']
    else:
        assert not result['scan_completed'] and result['unexecuted_keys'] == plan['sequence'][1:]
        assert len(calls) == (3 if fault == 'late' else 1)
        if fault == 'progress':
            assert rebuilt['accounting']['known_tokens'] == 30 and rebuilt['accounting']['unknown_usage_calls'] == 0
            assert result['budget_unknown_reserved_tokens'] > 0
    output = tmp_path.parent / (tmp_path.name + '-sealed.json')
    evidence.seal(tmp_path, output, event_source=host)
    with pytest.raises(FileExistsError): evidence.seal(tmp_path, output, event_source=host)
    with pytest.raises(ValueError, match='closed'): evidence.material(tmp_path, plan['sequence'][0], 'initial')


@pytest.mark.parametrize('tamper', ['case_budget', 'timeout', 'plan_identity', 'clock'])
def test_timed_replay_rejects_budget_reset_and_identity_changes(tmp_path, monkeypatch, original_controls, tamper):
    plan, factory, host, judge, _ = setup(tmp_path, monkeypatch, original_controls)
    runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=judge)
    if tamper == 'case_budget':
        path = tmp_path / 'result.json'; value = evidence.read(path)
        value['case_budgets'][0]['calls'] = 0
    elif tamper == 'timeout':
        path = tmp_path / 'claim-scope-4/final/send-start.json'; value = evidence.read(path)
        value['case_started_active_seconds'] = 550
    elif tamper == 'clock':
        path = tmp_path / 'claim-scope-4/case-budget-finished.json'; value = evidence.read(path)
        value['finished_active_seconds'] = 0
    else:
        path = tmp_path / 'plan.json'; value = evidence.read(path)
        value['preparation_plan'].pop('timing_mode')
        value['plan_sha256'] = runner.canonical_sha(value['preparation_plan'])
    path.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError): evidence.replay(tmp_path, event_source=host)


def test_timed_receipt_reader_cannot_supply_arbitrary_roles_or_widen_legacy_observation(tmp_path):
    from app.evaluation.role_qualification import read_role_calls
    with pytest.raises(ValueError, match='diagnostic_contract_invalid'):
        read_role_calls(tmp_path, role_contract={}, request_role=timing.role_for_request,
            observation_type=bridge.TimedReviewBridgeObservation)
    with pytest.raises(ValueError, match='diagnostic_contract_invalid'):
        read_role_calls(tmp_path, observation_type=bridge.TimedReviewBridgeObservation)


def test_timed_presend_identity_stop_seals_zero_calls(tmp_path, monkeypatch, original_controls):
    plan, factory, host, judge, calls = setup(tmp_path, monkeypatch, original_controls)
    def unavailable():
        raise ValueError('synthetic_presend_identity_stop')
    result = runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=judge, before_send=unavailable)
    assert result['provider_calls'] == 0 and not calls
    assert result['case_budgets'][0]['calls'] == 0
    assert evidence.replay(tmp_path, event_source=host)['accounting']['calls'] == 0
