"""Real receipt plumbing with synthetic model/Host replies; no quality credit."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.providers.models import ChatResponse, ToolCall, TokenUsage
from scripts import full15_resumption_evidence as evidence
from scripts import host_review_task_checkpoint as checkpoint
from scripts import review_independence_contract as identity
from scripts import run_full15_resumption_candidate as runner
from tests.test_coarse_revision_editor import cases, BEFORE, AFTER


@pytest.fixture(scope='module')
def frozen_controls():
    return runner.controls()


@pytest.fixture(autouse=True)
def reuse_frozen_controls(monkeypatch, frozen_controls):
    monkeypatch.setattr(runner, 'controls', lambda root=runner.ROOT: frozen_controls)


class Host:
    def __init__(self, plan, directory, fault=None):
        self.plan, self.directory, self.fault, self.events = plan, directory, fault, {}

    def fetch(self, *, event_id, binding):
        if self.fault == 'unavailable': raise ValueError('synthetic_unavailable')
        return self.events[event_id]

    def adjudicate(self, path, remaining):
        required = evidence.read(path)
        bound = required['binding']
        stage, key = bound['stage'], bound['key']
        folder = path.parent
        task = evidence.task(self.directory, key, stage)
        runner._write_json(folder / 'independent-task.json', json.loads(task))
        sha = checkpoint.publish(folder / 'task-checkpoint.json', folder / 'independent-task.json',
            self.plan['review_principals']['independent']['principal_id'])
        if self.fault == 'abort':
            evidence.abort(self.directory, key, stage, 'reviewer_unavailable')
            raise ValueError('full15_operator_abort')
        reviews = {}
        for name in ('primary', 'independent'):
            accepted = not (self.fault == stage + '_reject' and name == 'independent')
            report = None if stage == 'initial' else dict(report_sha256=bound['report_sha256'],
                reviewer=self.plan['review_principals'][name]['principal_id'],
                source_review='Synthetic plumbing opinion, not source certification.',
                facts_and_sources_correct=True, correct_content_preserved=True,
                identity_and_goal_preserved=True, true_errors_fixed=True)
            review = dict(binding=bound, report_assessment=report,
                stage_assessment=dict(stage=stage, stage_sha256=required['stage_sha256'],
                    reviewer=self.plan['review_principals'][name]['principal_id'],
                    source_review='Synthetic plumbing opinion, not semantic proof.',
                    accepted=accepted, defects=[] if accepted else [dict(kind='wrong_correction', detail='Synthetic defect.')]))
            if self.fault == 'report_flag' and report:
                report['true_errors_fixed'] = False
            if name == 'primary':
                notes = {k: review[k] for k in ('stage_assessment', 'report_assessment')}
            else:
                event_id = 'synthetic-independent/' + key + '/' + stage
                event = dict(schema_version=identity.VERSION, event_kind=identity.EVENT_KIND,
                    state='completed', host_review_evidence_policy=identity.FINAL_POLICY,
                    author_principal_id=self.plan['review_principals'][name]['principal_id'],
                    root_thread_id=self.plan['root_thread_id'], binding=bound,
                    review_sha256=identity.review_digest(review), event_id=event_id,
                    dispatch_id='synthetic-dispatch', raw_event_sha256='a'*64, review=deepcopy(review))
                if self.fault == 'identity': event['author_principal_id'] = 'wrong'
                self.events[event_id] = event
            reviews[name] = review
        if self.fault == 'checkpoint':
            sha = '0'*64
        evidence.submit(self.directory, key, stage, notes, event_id, self, sha)
        return evidence.read(folder / 'review-submission.json')


def setup_run(tmp_path, monkeypatch, fault=None, *, selection='full15'):
    plan = runner.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent',
                          selection=selection)
    runner._write_json(tmp_path / 'plan.json', dict(preparation_plan=plan, plan_sha256=runner.canonical_sha(plan)))
    calls = []
    by_document = {request.messages[1].content: row for row, _, _, request in runner.controls()[1]}
    raw = cases()['claim-scope:4'][3]
    def child(command, request_raw, *, directory, timeout_s, environ, transport_id):
        request = bridge.REQUEST.validate_json(request_raw, strict=True)
        calls.append(request)
        if fault in ('transport', 'progress'):
            if fault == 'progress':
                runner._write_json(directory / 'progress.json', bridge.CapacityBridgeObservation(
                    state='incomplete', input_tokens=20, output_tokens=10).model_dump(mode='json'))
            raise RuntimeError('Synthetic interruption')
        if transport_id == runner.CAPACITY_TRANSPORT_ID:
            args = dict(edits={'block_4': [dict(before=BEFORE, after=AFTER,
                reason='Synthetic necessary replacement.')]} if fault != 'bad_edit' else {'block_4': []})
            model, tool = 'glm-5.3-flash', 'submit_block_edits'
        else:
            # Only the genuine claim-scope:4 fixture takes the edit path. Other
            # wrong-verdict controls terminate semantically without new sends.
            cell = by_document.get(request.messages[1].content)
            args = json.loads(raw) if cell and cell['key'] == 'claim-scope:4' else dict(
                score=96, verdict='pass', issues=[], issue_resolutions=[], advisories=[])
            if fault == 'schema': args['unexpected'] = True
            model, tool = 'glm-5.3', 'submit_report_review'
        runner._write_json(directory / 'result.json', dict(state='complete', elapsed_ms=0, transport_id=transport_id))
        return ChatResponse(provider='zhipu', model=model, content=None, finish_reason='tool_calls',
            usage=TokenUsage(input_tokens=20, output_tokens=10), reasoning_content='PRIVATE_SYNTHETIC_REASONING',
            tool_calls=(ToolCall(id='synthetic', name=tool, arguments=args),))
    monkeypatch.setattr(bridge, 'run_child', child)
    settings = lambda model: SimpleNamespace(model=model, api_key='offline-only', base_url='https://open.bigmodel.cn/api/paas/v4')
    factory = runner.CandidateProviderFactory(generator_settings=settings('glm-5.3-flash'),
        reviewer_settings=settings('glm-5.3'), transport_root=tmp_path / 'transport')
    return plan, factory, calls


def test_complete_receipt_handoff_edit_fresh_and_readonly_seal(tmp_path, monkeypatch):
    plan, factory, calls = setup_run(tmp_path, monkeypatch)
    host = Host(plan, tmp_path)
    checked = []
    result = runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=host.adjudicate,
        before_send=lambda: checked.append(True))
    assert result['scan_completed'], result
    assert len(calls) == result['provider_calls'] == len(checked) == 17
    edited = next(c for c in result['cases'] if c['key'] == 'claim-scope:4')
    assert [s['stage'] for s in edited['stages']] == list(runner.STAGES)
    assert edited['semantic_accepted'] and not result['diagnostic_accepted']
    originals = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    sealed = evidence.replay(tmp_path, event_source=host)
    assert sealed['accounting']['calls'] == 17 and sealed['accounting']['known_tokens'] == 510
    assert sealed['new_qualification'] == 0 and not sealed['original15_qualified']
    assert 'PRIVATE_SYNTHETIC_REASONING' not in json.dumps(sealed)
    assert all(p.read_bytes() == raw for p, raw in originals.items())
    with pytest.raises(ValueError, match='closed'):
        evidence.material(tmp_path, plan['sequence'][0], 'initial')
    output = tmp_path.parent / (tmp_path.name + '-sealed.json')
    evidence.seal(tmp_path, output, event_source=host)
    with pytest.raises(FileExistsError): evidence.seal(tmp_path, output, event_source=host)
    with pytest.raises(ValueError, match='inside_run'): evidence.seal(tmp_path, tmp_path / 'seal.json', event_source=host)


@pytest.mark.parametrize('fault,expected_calls', [('transport', 1), ('schema', 1), ('bad_edit', 3),
    ('identity', 1), ('unavailable', 1), ('checkpoint', 1), ('report_flag', 3), ('abort', 1)])
def test_hard_failure_stops_closes_and_accounts(tmp_path, monkeypatch, fault, expected_calls):
    plan, factory, calls = setup_run(tmp_path, monkeypatch, fault)
    host = Host(plan, tmp_path, fault)
    result = runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=host.adjudicate)
    assert not result['scan_completed'] and result.get('error_type'), result
    assert len(calls) == result['provider_calls'] == expected_calls, result
    assert result['unfinished_keys'] == [result['cases'][-1]['key']]
    assert result['unexecuted_keys'] == plan['sequence'][len(result['cases']):]
    assert (result['unknown_reserved_tokens'] > 0) == (fault == 'transport')
    assert evidence.read(tmp_path / 'result.json') == json.loads(json.dumps(result))
    sealed = evidence.replay(tmp_path, event_source=host)
    assert sealed['accounting']['calls'] == expected_calls
    assert sealed['accounting']['unknown_usage_calls'] == (fault == 'transport')
    assert not sealed['production_admitted']


@pytest.mark.parametrize('stage,expected_calls', [('initial', 15), ('revision', 16), ('final', 17)])
def test_semantic_rejection_stops_dependencies_continues_independent_cases(tmp_path, monkeypatch, stage, expected_calls):
    plan, factory, calls = setup_run(tmp_path, monkeypatch)
    host = Host(plan, tmp_path, stage + '_reject')
    result = runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=host.adjudicate)
    assert result['scan_completed'] and not result['diagnostic_accepted'], result
    assert len(calls) == expected_calls
    evidence.replay(tmp_path, event_source=host)


@pytest.mark.parametrize('artifact', ['source', 'stage', 'result', 'checkpoint', 'native'])
def test_replay_rejects_changed_source_stage_outcome_checkpoint_or_native(tmp_path, monkeypatch, artifact):
    plan, factory, _ = setup_run(tmp_path, monkeypatch)
    host = Host(plan, tmp_path)
    result = runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=host.adjudicate)
    assert result['scan_completed'], result
    arm = tmp_path / plan['sequence'][0].replace(':', '-')
    if artifact == 'native':
        next(iter(host.events.values()))['author_principal_id'] = 'changed'
    else:
        path = {'source': arm / 'source.json', 'stage': arm / 'initial/stage.json',
            'result': tmp_path / 'result.json', 'checkpoint': arm / 'initial/task-checkpoint.json'}[artifact]
        value = evidence.read(path)
        value['changed'] = True
        path.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError): evidence.replay(tmp_path, event_source=host)


def test_pre_send_check_prevents_io_and_create_only_preview(tmp_path, monkeypatch):
    plan, factory, calls = setup_run(tmp_path, monkeypatch)
    host = Host(plan, tmp_path)
    def changed(): raise ValueError('full15_checkout_changed')
    result = runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=host.adjudicate, before_send=changed)
    assert result['provider_calls'] == 0 and not calls
    assert result['error_code'] == 'full15_checkout_changed'
    assert evidence.replay(tmp_path, event_source=host)['accounting']['calls'] == 0


def test_interrupted_stream_usage_is_known_without_releasing_live_reservation(tmp_path, monkeypatch):
    plan, factory, calls = setup_run(tmp_path, monkeypatch, 'progress')
    host = Host(plan, tmp_path)
    result = runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=host.adjudicate)
    assert result['provider_calls'] == len(calls) == 1
    assert result['known_tokens'] == 30 and result['unknown_reserved_tokens'] == 0
    assert result['budget_known_tokens'] == 0 and result['budget_unknown_reserved_tokens'] > 0
    sealed = evidence.replay(tmp_path, event_source=host)
    assert sealed['accounting']['known_tokens'] == 30
    assert sealed['accounting']['unknown_usage_calls'] == 0
    assert not result['scan_completed'] and not sealed['production_admitted']


@pytest.mark.parametrize('field', ['budget_known_tokens', 'budget_unknown_reserved_tokens', 'timing', 'provider_calls'])
def test_interrupted_accounting_or_host_clock_tampering_is_rejected(tmp_path, monkeypatch, field):
    plan, factory, _ = setup_run(tmp_path, monkeypatch, 'transport')
    host = Host(plan, tmp_path)
    result = runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=host.adjudicate)
    if field == 'provider_calls': result[field] = True
    elif field == 'timing': result['timing']['completed_host_waits'] = 1
    else: result[field] += 1
    (tmp_path / 'result.json').write_text(json.dumps(result), encoding='utf-8')
    with pytest.raises(ValueError): evidence.replay(tmp_path, event_source=host)


@pytest.mark.parametrize('fault', ['summary', 'both_bindings'])
def test_host_clock_cannot_lower_final_time_or_rebind_a_wait(tmp_path, monkeypatch, fault):
    plan, factory, _ = setup_run(tmp_path, monkeypatch)
    host = Host(plan, tmp_path, 'abort')
    result = runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=host.adjudicate)
    if fault == 'summary':
        result['timing']['active_elapsed_seconds'] = 0
        result['timing']['wall_elapsed_seconds'] = result['timing']['host_elapsed_seconds']
        (tmp_path / 'result.json').write_text(json.dumps(result), encoding='utf-8')
    else:
        for name in ('0001-waiting.json', '0001-finished.json'):
            path = tmp_path / 'development-host-clock' / name
            receipt = evidence.read(path)
            receipt['binding']['response_sha256'] = '0'*64
            path.write_text(json.dumps(receipt), encoding='utf-8')
    with pytest.raises(ValueError): evidence.replay(tmp_path, event_source=host)


@pytest.mark.parametrize('rejected_stage,expected_calls', [(None, 12), ('initial', 10),
    ('revision', 11), ('final', 12)])
def test_focused_scope_sends_only_selected_cases_and_replays_complete_diagnostic(
        tmp_path, monkeypatch, rejected_stage, expected_calls):
    plan, factory, calls = setup_run(tmp_path, monkeypatch, selection='diagnostic10')
    host = Host(plan, tmp_path, rejected_stage + '_reject' if rejected_stage else None)
    result = runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=host.adjudicate)
    assert result['scan_completed'] and len(result['cases']) == 10, result
    assert [case['key'] for case in result['cases']] == list(runner.DIAGNOSTIC)
    assert len(calls) == expected_calls
    excluded = {row['key'] for row in runner.controls()[0]} - set(plan['sequence'])
    assert all(not (tmp_path / key.replace(':', '-')).exists() for key in excluded)
    sent_documents = {request.messages[1].content for request in calls}
    assert all(request.messages[1].content not in sent_documents
               for row, _, _, request in runner.controls()[1] if row['key'] in excluded)
    sealed = evidence.replay(tmp_path, event_source=host)
    assert sealed['accounting']['calls'] == expected_calls
    assert result['experiment'] == plan['run_id'] != runner.RUN_ID
    assert result['unexecuted_keys'] == [] and not sealed['production_admitted']
    with pytest.raises(ValueError, match='handoff_scope'):
        evidence.material(tmp_path, next(iter(excluded)), 'initial')


@pytest.mark.parametrize('fault,expected_calls', [('identity', 1), ('bad_edit', 5)])
def test_focused_hard_stop_keeps_exact_unexecuted_inventory(tmp_path, monkeypatch, fault, expected_calls):
    plan, factory, calls = setup_run(tmp_path, monkeypatch, fault, selection='diagnostic10')
    host = Host(plan, tmp_path, fault)
    result = runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=host.adjudicate)
    assert not result['scan_completed'] and len(calls) == expected_calls, result
    assert result['unexecuted_keys'] == plan['sequence'][len(result['cases']):]
    assert evidence.replay(tmp_path, event_source=host)['accounting']['calls'] == expected_calls


@pytest.mark.parametrize('change', ['selection', 'budget', 'experiment', 'orphan'])
def test_focused_replay_rejects_scope_budget_run_or_excluded_case_tampering(tmp_path, monkeypatch, change):
    plan, factory, _ = setup_run(tmp_path, monkeypatch, selection='diagnostic10')
    host = Host(plan, tmp_path)
    runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=host.adjudicate)
    if change in ('selection', 'budget'):
        saved = evidence.read(tmp_path / 'plan.json')
        if change == 'selection': saved['preparation_plan']['case_selection'] = 'full15'
        else: saved['preparation_plan']['budget']['max_calls'] += 1
        saved['plan_sha256'] = runner.canonical_sha(saved['preparation_plan'])
        (tmp_path / 'plan.json').write_text(json.dumps(saved), encoding='utf-8')
    elif change == 'experiment':
        result = evidence.read(tmp_path / 'result.json')
        result['experiment'] = runner.RUN_ID
        (tmp_path / 'result.json').write_text(json.dumps(result), encoding='utf-8')
    else:
        (tmp_path / 'claim-scope-3').mkdir()
    with pytest.raises(ValueError): evidence.replay(tmp_path, event_source=host)
