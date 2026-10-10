"""Never-sent inventory, isolated plumbing and frozen prior rejection; offline only."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.document_review_timed_transport import TimedDocumentProviderFactory
from app.providers.models import ChatResponse, ToolCall, TokenUsage
from scripts import document_remaining4_adapter as adapter
from scripts import document_remaining8_adapter as closed_adapter
from tests import test_full15_resumption_evidence as fixtures


@pytest.fixture(scope='module', autouse=True)
def portable_frozen_hashes():
    manifest = json.loads((adapter.runner.ROOT /
        'tests/fixtures/document_remaining4_frozen_newlines.json').read_bytes())
    sealed = json.loads((adapter.runner.ROOT / adapter.PREVIOUS_SEAL).read_bytes())
    frozen = sealed['public_json_contents']['plan.json']['preparation_plan']['source_sha256']
    assert manifest['previous_closed_seal_sha256'] == adapter.PREVIOUS_SHA
    assert manifest['production_override'] is False
    assert {p: v['frozen_raw_sha256'] for p, v in manifest['source'].items()} == frozen
    original = adapter.runner._sha
    def test_hash(path):
        path = Path(path)
        try:
            relative = path.resolve().relative_to(adapter.runner.ROOT.resolve()).as_posix()
        except ValueError:
            return original(path)
        entry = manifest['source'].get(relative)
        if entry is not None:
            normalized = hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            if normalized == entry['lf_sha256']:
                return entry['frozen_raw_sha256']
        return original(path)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(adapter.runner, '_sha', test_hash)
        yield original


@pytest.fixture(scope='module')
def controls():
    return adapter.selected_controls()


def test_exact_never_sent_four_and_isolated_old_replay(controls):
    rows, variants = controls
    assert [row['key'] for row in rows] == list(adapter.KEYS)
    assert len(rows) == len(variants) == 4
    prior = {r['key']: r for r in adapter.prior()['cells']}
    assert all(row == prior[row['key']] for row in rows)
    assert adapter.runner is not closed_adapter.runner
    assert adapter.evidence is not closed_adapter.evidence
    assert closed_adapter.evidence.runner is closed_adapter.runner
    assert 'remaining4' not in closed_adapter.runner.RUN_IDS
    plan = adapter.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-child')
    assert plan['sequence'] == list(adapter.KEYS)
    assert plan['budget']['role_calls'] == {'glm-5.3': 8, 'glm-5.3-flash': 4}
    assert plan['budget']['max_calls'] == 12
    assert plan['budget']['max_tokens'] == 1161216
    assert plan['budget']['max_active_seconds'] == 3600
    assert plan['previous_unreviewed_cases'] == [
        dict(key='claim-scope:2', repeated=False, credit=0),
        dict(key='observed:1', repeated=False, credit=0)]


@pytest.mark.parametrize('fault', [None, 'edit', 'abort', 'checkpoint'])
def test_four_handoff_edit_fresh_semantic_continue_and_hard_stop(
        tmp_path, monkeypatch, controls, fault):
    runner, evidence = adapter.runner, adapter.evidence
    monkeypatch.setattr(runner, 'selected_controls', lambda *args, **kwargs: controls)
    monkeypatch.setattr(runner, 'controls', lambda root=runner.ROOT: controls)
    monkeypatch.setattr(fixtures, 'runner', runner)
    monkeypatch.setattr(fixtures, 'evidence', evidence)
    plan = adapter.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-child')
    runner._write_json(tmp_path / 'plan.json', dict(preparation_plan=plan,
        plan_sha256=runner.canonical_sha(plan)))
    historical = json.loads((runner.ROOT /
        'data/evaluation/results/golden_document_remaining11_scan_result_20261009.json').read_bytes())
    first_review = historical['public_json_contents']['observed-2/response.json']['tool_calls'][0]['arguments']
    assert first_review['verdict'] == 'needs_revision'
    before = controls[1][0][2].source.blocks[2][1]
    calls = []
    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        request = bridge.REQUEST.validate_json(raw)
        calls.append(request)
        args = dict(score=96, verdict='pass', issues=[], issue_resolutions=[], advisories=[])
        model, tool = 'glm-5.3', 'submit_report_review'
        if fault == 'edit' and len(calls) == 1:
            args = first_review
        elif fault == 'edit' and request.metadata['review_phase'] == 'native_business_revision':
            model, tool = 'glm-5.3-flash', 'submit_block_edits'
            args = dict(edits={'block_3': [dict(before=before,
                after=before + ' 合成接缝标记。', reason='Synthetic plumbing only.')]})
        runner._write_json(directory / 'result.json', dict(state='complete',
            elapsed_ms=0, transport_id=transport_id))
        return ChatResponse(provider='zhipu', model=model, finish_reason='tool_calls', content=None,
            usage=TokenUsage(20, 10), tool_calls=(ToolCall(id='synthetic', name=tool, arguments=args),))
    monkeypatch.setattr(bridge, 'run_child', child)
    settings = lambda model: NS(model=model, api_key='OFFLINE_FIXTURE',
        base_url='https://open.bigmodel.cn/api/paas/v4')
    factory = TimedDocumentProviderFactory(generator_settings=settings('glm-5.3-flash'),
        reviewer_settings=settings('glm-5.3'), transport_root=tmp_path / 'transport')
    host = fixtures.Host(plan, tmp_path, fault if fault != 'edit' else None)
    result = runner.observe(factory, tmp_path, plan, event_source=host, adjudicate=host.adjudicate)
    assert not result.get('accounting_error_type'), result
    if fault in (None, 'edit'):
        assert result['scan_completed'] and len(calls) == 4 + 2 * int(fault == 'edit')
        assert sum(c['semantic_accepted'] for c in result['cases']) == int(fault == 'edit')
        assert result['unexecuted_keys'] == []
        if fault == 'edit':
            assert [s['stage'] for s in result['cases'][0]['stages']] == ['initial', 'revision', 'final']
    else:
        assert not result['scan_completed'] and len(calls) == 1
        assert result['unexecuted_keys'] == list(adapter.KEYS[1:])
    assert not (tmp_path / 'observed-1').exists()
    assert not (tmp_path / 'claim-scope-2').exists()
    assert result['new_qualification'] == 0
    if fault != 'checkpoint':
        rebuilt = evidence.replay(tmp_path, event_source=host)
        assert rebuilt['accounting']['calls'] == len(calls)
        output = tmp_path.parent / (tmp_path.name + '-seal.json')
        evidence.seal(tmp_path, output, event_source=host)
        with pytest.raises(FileExistsError):
            evidence.seal(tmp_path, output, event_source=host)


def test_changed_prior_or_sent_inventory_cannot_enter(monkeypatch):
    original_sha = adapter.runner._sha
    target = (adapter.runner.ROOT / adapter.PREVIOUS_SEAL).resolve()
    monkeypatch.setattr(adapter.runner, '_sha', lambda path:
        '0' * 64 if Path(path).resolve() == target else original_sha(path))
    with pytest.raises(ValueError, match='remaining4_prior_seal_changed'):
        adapter.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-child')
    monkeypatch.setattr(adapter.runner, '_sha', original_sha)
    changed = deepcopy(adapter.prior())
    changed['cells'][-1]['candidate_request_sha256'] = '0' * 64
    monkeypatch.setattr(adapter, 'prior', lambda root=adapter.runner.ROOT: changed)
    with pytest.raises(ValueError, match='remaining4_frozen_requests_changed'):
        adapter.selected_controls()
    with pytest.raises(ValueError, match='remaining4_selection_or_timing'):
        adapter.selected_controls('remaining8')


def test_production_rejects_normalized_sources(tmp_path, monkeypatch, portable_frozen_hashes):
    previous = adapter.prior()
    for seal_name in (adapter.PREVIOUS_SEAL, adapter.base.PREVIOUS_SEAL):
        target = tmp_path / seal_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((adapter.runner.ROOT / seal_name).read_bytes())
    for name in previous['source_sha256']:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((adapter.runner.ROOT / name).read_bytes().replace(b'\r\n', b'\n'))
    monkeypatch.setattr(adapter.runner, '_sha', portable_frozen_hashes)
    with pytest.raises(ValueError, match='frozen_program_changed'):
        adapter.prior(tmp_path)
