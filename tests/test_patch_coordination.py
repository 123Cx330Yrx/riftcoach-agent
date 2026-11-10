"""Offline assembly/accounting checks; synthetic approvals are not semantic proof."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import socket

import pytest

from app.evaluation import sol_original15_session as engine
from app.evaluation.golden_review_experiment import compact
from app.evaluation.source_patch_editor import report_inputs
from scripts import review_duty_direct_patch as direct
from tests.test_review_duty_direct_patch import sample, repaired, pair, PASS, BEFORE, AFTER


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('coordination checks cannot connect')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)


def selection(inventory, choose=None):
    rows = {op['id']: op for op in inventory['operations']}
    resolutions = []
    for component in inventory['conflicts']:
        ids = component['operation_ids']
        chosen = choose or [ids[0]]
        issues = sorted({(rows[i]['duty'], issue) for i in ids for issue in rows[i]['issue_ids']})
        resolutions.append(dict(component=component['component'], selected_operation_ids=chosen,
            issue_coverage=[dict(duty=duty, issue_id=issue, selected_operation_ids=chosen,
                reason='Synthetic coverage claim; full native review must judge its truth.')
                for duty, issue in issues]))
    return dict(version=direct.COORDINATION_VERSION, inventory_sha256=direct.inventory_sha(inventory),
        resolutions=resolutions)


def test_real_observed3_accepted_opinions_can_form_literal_unapproved_preview():
    _, inputs = engine.case_for('observed:3')
    path = Path('data/evaluation/results/sol_original15_observed3_initials_accepted_20261028.json')
    original = json.loads(path.read_bytes())
    proposals = [direct.bind(inputs, s['stage'].removesuffix('-initial'), compact(s['provider_opinion']))
                 for s in original['accepted_stages']]
    inventory = direct.conflict_inventory(inputs, proposals)
    assert len(inventory['operations']) == 2 and len(inventory['conflicts']) == 1
    assert inventory['original_report_sha256'] == original['accepted_stages'][0]['original_report_sha256']
    with pytest.raises(ValueError, match='overlap'):
        direct.preview(inputs, proposals)
    for op in inventory['operations']:
        result = direct.preview(inputs, proposals, coordination=selection(inventory, [op['id']]))
        assert result.report == inputs.source.report.replace(op['before'], op['after'], 1)
        assert len(result.journal['operations']) == 2
        assert len(result.journal['selected_operations']) == 1
        assert not result.journal['coordination_semantics_verified']
        assert not result.journal['semantic_approval']
        assert result.journal['full_final_review_required']
        revised = report_inputs(inputs, result.report)
        for duty in ('facts', 'completion'):
            assert result.journal['fresh_request_sha256'][duty] == direct.duty.request_sha(
                direct.review_request(revised, duty, 'fresh'))


@pytest.mark.parametrize('same_after', [True, False])
def test_identical_and_different_edits_need_explicit_selection(sample, same_after):
    inputs, value = sample
    facts, completion = repaired(value), repaired(value, AFTER if same_after else AFTER+' OFFLINE.')
    proposals = pair(inputs, facts, completion)
    inventory = direct.conflict_inventory(inputs, proposals)
    with pytest.raises(ValueError, match='overlap'):
        direct.preview(inputs, proposals)
    chosen = selection(inventory)
    result = direct.preview(inputs, proposals, coordination=chosen)
    assert result.report == inputs.source.report.replace(BEFORE, AFTER)
    assert {(x['duty'], x['issue_id']) for x in chosen['resolutions'][0]['issue_coverage']} == {
        ('facts', 1), ('completion', 1)}
    assert result.journal['coordination'] == chosen
    chosen['resolutions'].clear()
    assert result.journal['coordination']['resolutions']


@pytest.mark.parametrize('fault', ['inventory', 'missing_component', 'unknown_component',
    'bool_component', 'missing_issue', 'wrong_duty', 'bool_issue', 'duplicate_issue',
    'empty_reason', 'unselected_ref', 'duplicate_ref', 'unknown_choice', 'duplicate_choice',
    'empty_choice', 'overlap', 'extra'])
def test_invalid_choice_or_lost_obligation_is_rejected(sample, fault):
    inputs, value = sample
    proposals = pair(inputs, repaired(value), repaired(value))
    inventory = direct.conflict_inventory(inputs, proposals)
    chosen = selection(inventory)
    row = chosen['resolutions'][0]
    coverage = row['issue_coverage'][0]
    if fault == 'inventory': chosen['inventory_sha256'] = '0'*64
    elif fault == 'missing_component': chosen['resolutions'] = []
    elif fault == 'unknown_component': row['component'] = 99
    elif fault == 'bool_component': row['component'] = True
    elif fault == 'missing_issue': row['issue_coverage'].pop()
    elif fault == 'wrong_duty': coverage['duty'] = 'other'
    elif fault == 'bool_issue': coverage['issue_id'] = True
    elif fault == 'duplicate_issue': row['issue_coverage'][1] = deepcopy(coverage)
    elif fault == 'empty_reason': coverage['reason'] = ' '
    elif fault == 'unselected_ref': coverage['selected_operation_ids'] = ['op_2']
    elif fault == 'duplicate_ref': coverage['selected_operation_ids'] *= 2
    elif fault == 'unknown_choice': row['selected_operation_ids'] = ['op_99']
    elif fault == 'duplicate_choice': row['selected_operation_ids'] *= 2
    elif fault == 'empty_choice': row['selected_operation_ids'] = []
    elif fault == 'overlap': chosen = selection(inventory, ['op_1', 'op_2'])
    elif fault == 'extra': chosen['accepted'] = True
    with pytest.raises(ValueError, match='coordination'):
        direct.preview(inputs, proposals, coordination=chosen)


@pytest.mark.parametrize('change', ['source', 'opinion', 'operation', 'request'])
def test_selection_bound_to_full_original_inventory(sample, change):
    inputs, value = sample
    proposals = pair(inputs, repaired(value), repaired(value))
    inventory = direct.conflict_inventory(inputs, proposals)
    chosen = selection(inventory)
    if change == 'source':
        block = inputs.source.blocks[5][1]
        inputs = report_inputs(inputs, inputs.source.report.replace(block, block+' OFFLINE.'))
        proposals = [direct.bind(inputs, p.duty, p.raw) for p in proposals]
    elif change in ('opinion', 'operation'):
        raw = json.loads(proposals[0].raw)
        if change == 'opinion': raw['issues'][0]['explanation'] += ' OFFLINE.'
        else: raw['repairs'][0]['edits']['block_4'][0]['after'] += ' OFFLINE.'
        proposals[0] = direct.bind(inputs, 'facts', compact(raw))
    else:
        proposals[0] = replace(proposals[0], request_sha256='0'*64)
    with pytest.raises(ValueError):
        direct.preview(inputs, proposals, coordination=chosen)


def test_connected_partial_overlap_and_nonoverlap_operations(sample):
    inputs, value = sample
    facts = repaired(value)
    completion = repaired(value)
    edits = facts['repairs'][0]['edits']['block_4']
    a, b, c = BEFORE[:10], BEFORE[5:20], BEFORE[15:]
    edits[:] = [dict(before=a, after='OFFLINE A', reason='fixture'),
                dict(before=c, after='OFFLINE C', reason='fixture')]
    completion['repairs'][0]['edits']['block_4'] = [dict(before=b, after='OFFLINE B', reason='fixture')]
    block = inputs.source.blocks[5][1]
    facts['repairs'][0]['edits']['block_6'] = [dict(before=block, after=block+' OFFLINE preserved.', reason='fixture')]
    proposals = pair(inputs, facts, completion)
    inventory = direct.conflict_inventory(inputs, proposals)
    assert len(inventory['conflicts']) == 1
    assert set(inventory['conflicts'][0]['operation_ids']) == {'op_1', 'op_2', 'op_4'}
    result = direct.preview(inputs, proposals, coordination=selection(inventory, ['op_1', 'op_2']))
    assert len(result.journal['selected_operations']) == 3  # Includes nonoverlap block_6.
    assert block+' OFFLINE preserved.' in result.report


def test_nonoverlap_path_keeps_original_journal_shape(sample):
    inputs, value = sample
    proposals = pair(inputs, repaired(value), PASS)
    assert not direct.conflict_inventory(inputs, proposals)['conflicts']
    result = direct.preview(inputs, proposals)
    assert 'coordination' not in result.journal and result.report == inputs.source.report.replace(BEFORE, AFTER)
    with pytest.raises(ValueError):
        direct.preview(inputs, proposals, coordination=selection(direct.conflict_inventory(inputs, proposals)))
