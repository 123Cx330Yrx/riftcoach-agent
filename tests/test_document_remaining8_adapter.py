"""Unsent inventory and real handoff/replay plumbing; models/Host are synthetic."""
from copy import deepcopy
import json
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.document_review_timed_transport import TimedDocumentProviderFactory
from app.providers.models import ChatResponse, ToolCall, TokenUsage
from scripts import document_remaining8_adapter as adapter
from scripts import full15_resumption_evidence as old_evidence
from scripts import run_full15_resumption_candidate as old_runner
from tests import test_full15_resumption_evidence as fixtures


@pytest.fixture(scope='module')
def controls():
    return adapter.selected_controls()


def test_remaining8_exact_unsent_inventory_requests_and_isolated_modules(controls):
    rows, variants = controls
    previous = adapter.prior()
    old_rows = {r['key']: r for r in previous['cells']}
    assert [r['key'] for r in rows] == list(adapter.KEYS)
    assert all(row == old_rows[row['key']] for row in rows)
    assert len(rows) == len(variants) == 8
    assert adapter.runner is not old_runner
    assert adapter.evidence is not old_evidence
    assert old_evidence.runner is old_runner
    assert 'remaining8' not in old_runner.RUN_IDS
    assert adapter.evidence.runner is adapter.runner


def test_frozen_case_or_legacy_timing_cannot_enter_remaining8(controls, monkeypatch):
    for selection, timing in [('full15', 'time600'), ('remaining8', 'legacy')]:
        with pytest.raises(ValueError, match='selection_or_timing'):
            adapter.selected_controls(selection, timing_mode=timing)
    changed = deepcopy(adapter.prior())
    changed['cells'][7]['candidate_request_sha256'] = '0' * 64
    monkeypatch.setattr(adapter, 'prior', lambda root=adapter.runner.ROOT: changed)
    with pytest.raises(ValueError, match='frozen_requests_changed'):
        adapter.selected_controls()


@pytest.mark.parametrize('fault', [None, 'edit', 'abort', 'checkpoint'])
def test_remaining8_native_handoff_and_strict_replay_without_old_credit(
        tmp_path, monkeypatch, controls, fault):
    runner, evidence = adapter.runner, adapter.evidence
    monkeypatch.setattr(runner, 'selected_controls', lambda *args, **kwargs: controls)
    # Inputs are immutable public fixtures. Avoid rebuilding all fifteen source
    # catalogs at every replay; no validation or receipt boundary is patched.
    monkeypatch.setattr(runner, 'controls', lambda root=runner.ROOT: controls)
    monkeypatch.setattr(fixtures, 'runner', runner)
    monkeypatch.setattr(fixtures, 'evidence', evidence)
    plan = adapter.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-child')
    assert plan['budget']['role_calls'] == {'glm-5.3': 13, 'glm-5.3-flash': 5}
    assert plan['budget']['max_calls'] == 18
    assert plan['budget']['max_tokens'] == 1741824
    assert plan['budget']['max_active_seconds'] == 7200
    assert plan['previous_unreviewed_case'] == dict(key='claim-scope:2', repeated=False, credit=0)
    runner._write_json(tmp_path / 'plan.json', dict(preparation_plan=plan, plan_sha256=runner.canonical_sha(plan)))
    calls = []
    historical = json.loads((runner.ROOT / 'data/evaluation/results/golden_document_remaining11_scan_result_20261009.json').read_bytes())
    fixture_review = historical['public_json_contents']['claim-scope-6/response.json']['tool_calls'][0]['arguments']
    edit_inputs = next(v[2] for v in controls[1] if v[0]['key'] == 'claim-scope:6')
    before = edit_inputs.source.blocks[5][1]
    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        request = bridge.REQUEST.validate_json(raw)
        calls.append(request)
        args = dict(score=96, verdict='pass', issues=[], issue_resolutions=[], advisories=[])
        model, tool = 'glm-5.3', 'submit_report_review'
        if fault == 'edit' and request.metadata['review_phase'] == 'native_business_revision':
            model, tool = 'glm-5.3-flash', 'submit_block_edits'
            # Exercise the full assembly/checkpoint/fresh path, explicitly not
            # semantic certification of a genuine repair.
            args = dict(edits={'block_6': [dict(before=before, after=before + ' 合成修改标记。',
                                               reason='Synthetic plumbing only.')]})
        elif fault == 'edit' and len(calls) == 2:
            args = fixture_review
        runner._write_json(directory / 'result.json', dict(state='complete', elapsed_ms=0,
                                                         transport_id=transport_id))
        return ChatResponse(provider='zhipu', model=model, finish_reason='tool_calls', content=None,
            usage=TokenUsage(20, 10), tool_calls=(ToolCall(id='synthetic', name=tool, arguments=args),))
    monkeypatch.setattr(bridge, 'run_child', child)
    settings = lambda model: NS(model=model, api_key='OFFLINE_FIXTURE', base_url='https://open.bigmodel.cn/api/paas/v4')
    factory = TimedDocumentProviderFactory(generator_settings=settings('glm-5.3-flash'),
        reviewer_settings=settings('glm-5.3'), transport_root=tmp_path / 'transport')
    host = fixtures.Host(plan, tmp_path, fault if fault != 'edit' else None)
    result = runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=host.adjudicate)
    assert not result.get('accounting_error_type'), result
    if fault in (None, 'edit'):
        edited = int(fault == 'edit')
        assert result['scan_completed'] and len(calls) == 8 + 2 * edited
        assert sum(c['semantic_accepted'] for c in result['cases']) == 3 + edited
        assert sum(c.get('semantic_failure') == 'initial_unexpected_verdict' for c in result['cases']) == 5 - edited
        if edited:
            assert [s['stage'] for s in result['cases'][1]['stages']] == ['initial', 'revision', 'final']
        # Semantic rejection of an independent case does not stop later cases.
        assert result['unexecuted_keys'] == []
    else:
        assert not result['scan_completed'] and len(calls) == 1
        assert result['unexecuted_keys'] == list(adapter.KEYS[1:])
    assert not (tmp_path / 'claim-scope-2').exists()
    assert result['new_qualification'] == 0
    if fault != 'checkpoint':
        rebuilt = evidence.replay(tmp_path, event_source=host)
        assert rebuilt['accounting']['calls'] == len(calls)
        assert rebuilt['new_qualification'] == 0
        output = tmp_path.parent / (tmp_path.name + '-seal.json')
        evidence.seal(tmp_path, output, event_source=host)
        with pytest.raises(FileExistsError):
            evidence.seal(tmp_path, output, event_source=host)


def test_prior_seal_digest_failure_stops_preparation_before_provider(monkeypatch):
    monkeypatch.setattr(adapter.runner, '_sha', lambda path: '0' * 64)
    with pytest.raises(ValueError, match='prior_seal_changed'):
        adapter.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-child')
