"""Authored offline repairs; no provider result or Host semantic endorsement."""
from copy import deepcopy
from dataclasses import replace
import json
import re
import socket

from jsonschema import Draft202012Validator
import pytest

from app.evaluation import document_review_timing_adapter as timing
from app.evaluation.golden_review_experiment import compact
from app.evaluation.source_patch_editor import report_inputs
from scripts import review_duty_direct_patch as direct
from scripts import review_duty_composition as duty
from tests.test_coarse_revision_editor import cases, BEFORE, AFTER

PASS = dict(score=95, verdict='pass', issues=[], issue_resolutions=[], advisories=[], repairs=[])


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError('offline prototype cannot connect')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


@pytest.fixture(scope='module')
def sample():
    _, inputs, _, raw = cases()['claim-scope:4']
    return inputs, json.loads(raw)


def repaired(value, after=AFTER):
    result = deepcopy(value)
    result['repairs'] = [dict(issue_ids=list(range(1, len(result['issues']) + 1)), edits={
        'block_4': [dict(before=BEFORE, after=after, reason='OFFLINE authored replacement.')]})]
    return result


def pair(inputs, value, completion=PASS):
    return [direct.bind(inputs, 'facts', compact(value)),
            direct.bind(inputs, 'completion', compact(completion))]


def test_request_preserves_full_sources_and_old_duty_schema(sample):
    inputs, value = sample
    for name in duty.DUTIES:
        base = duty.review_request(inputs, name)
        request = direct.review_request(inputs, name)
        assert request.messages[1:] == base.messages[1:]
        schema = request.tools[0].input_schema
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(repaired(value))
        restored = deepcopy(schema)
        restored['properties'].pop('repairs')
        restored['required'].remove('repairs')
        restored['$defs'].pop('DirectPatchReplacement')
        assert restored == base.tools[0].input_schema
        assert request.messages[0].content == base.messages[0].content + direct.PATCH_POLICY
        assert request.metadata[direct.MARKER] == direct.VERSION
        with pytest.raises(ValueError):
            timing.request_bytes(request)
    with pytest.raises(ValueError):
        direct.bind(inputs, 'facts', compact(value))  # No conversion of old opinions.


def test_exact_consumption_and_full_fresh_have_no_paraphrase_step(sample):
    inputs, value = sample
    result = direct.preview(inputs, pair(inputs, repaired(value)))
    assert result.report == inputs.source.report.replace(BEFORE, AFTER)
    assert result.journal['opinions']['facts']['raw'] == compact(repaired(value))
    assert result.journal['operations'][0]['after'] == AFTER
    revised = report_inputs(inputs, result.report)
    for name in duty.DUTIES:
        request = direct.review_request(revised, name, 'fresh')
        assert request.messages == duty.review_request(revised, name, 'fresh').messages
        assert result.journal['fresh_request_sha256'][name] == duty.request_sha(request)
        assert 'repairs' not in request.tools[0].input_schema['properties']
        assert 'OFFLINE authored replacement' not in ''.join(m.content for m in request.messages)
    assert result.journal['preview_only'] and result.journal['full_final_review_required']
    assert not any(result.journal[k] for k in ('semantic_approval', 'production_admitted',
        'native_acceptance_verified', 'semantic_compatibility_verified'))


@pytest.mark.parametrize('title', ['## 6. 训练计划', '## 6. 观摩练习计划'])
def test_task_section_title_survives_exact_preview_and_both_fresh_inputs(sample, title):
    from app.report_validation import COACH_REPORT_HEADINGS
    inputs, value = sample
    raw = repaired(value)
    old = COACH_REPORT_HEADINGS[6]
    if title != old:
        block = next(i for i, (_, text) in enumerate(inputs.source.blocks, 1) if old in text)
        raw['repairs'][0]['edits'][f'block_{block}'] = [dict(before=old, after=title,
            reason='OFFLINE task title witness; no semantic approval.')]
    result = direct.preview(inputs, pair(inputs, raw))
    assert result.report == inputs.source.report.replace(BEFORE, AFTER).replace(old, title)
    revised = report_inputs(inputs, result.report)
    for name in duty.DUTIES:
        request = direct.review_request(revised, name, 'fresh')
        assert title in request.messages[1].content
        assert result.journal['fresh_request_sha256'][name] == duty.request_sha(request)
    assert not result.journal['semantic_approval']


@pytest.mark.parametrize('replacement', [
    '', 'inline ## 6. 观摩练习计划', '```\n## 6. 观摩练习计划\n```',
    '~~~\n## 6. 观摩练习计划\n~~~', '## 6. 观摩练习计划伪造',
    '### 6. 观摩练习计划', '## 6. 观摩练习计划\n\n## 6. 训练计划',
    '## 6. 观摩练习计划\n\n## 6. 观摩练习计划',
])
def test_title_alias_does_not_allow_missing_disguised_or_duplicate_sections(sample, replacement):
    from app.report_validation import COACH_REPORT_HEADINGS
    inputs, value = sample
    old = COACH_REPORT_HEADINGS[6]
    block = next(i for i, (_, text) in enumerate(inputs.source.blocks, 1) if old in text)
    raw = repaired(value)
    raw['repairs'][0]['edits'][f'block_{block}'] = [dict(before=old, after=replacement,
        reason='OFFLINE invalid structure witness.')]
    original = inputs.source.report
    with pytest.raises(ValueError):
        direct.preview(inputs, pair(inputs, raw))
    assert inputs.source.report == original


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'unknown', 'string', 'bool',
    'pass', 'fail', 'extra', 'source', 'resolution'])
def test_issue_mapping_does_not_lose_obligations(sample, fault):
    inputs, value = sample
    raw = repaired(value)
    if fault == 'missing': raw['repairs'] = []
    elif fault == 'duplicate': raw['repairs'].append(deepcopy(raw['repairs'][0]))
    elif fault == 'unknown': raw['repairs'][0]['issue_ids'] = [512]
    elif fault == 'string': raw['repairs'][0]['issue_ids'] = ['1']
    elif fault == 'bool': raw['repairs'][0]['issue_ids'] = [True]
    elif fault in ('pass', 'fail'): raw.update(verdict=fault, issues=[])
    elif fault == 'extra': raw['repairs'][0]['host_accepted'] = True
    elif fault == 'source': raw['issues'][0]['source_ids'] = [99999]
    elif fault == 'resolution': raw['issue_resolutions'] = [dict(previous_id=1,
        disposition='withdrawn', final_issue=None, source_ids=[31], explanation='Synthetic')]
    with pytest.raises(ValueError):
        direct.bind(inputs, 'facts', compact(raw))


@pytest.mark.parametrize('fault', ['bare_key', 'leading_zero', 'unknown_block', 'empty_group',
    'anchor', 'overlap', 'noop', 'citation', 'echo', 'request', 'report', 'input', 'version', 'pair'])
def test_invalid_patch_is_never_repaired_and_source_remains_unchanged(sample, fault):
    inputs, value = sample
    before = inputs.source.report
    raw = repaired(value)
    edits = raw['repairs'][0]['edits']
    if fault in ('bare_key', 'leading_zero', 'unknown_block'):
        edits[dict(bare_key='4', leading_zero='block_04', unknown_block='block_64')[fault]] = edits.pop('block_4')
    elif fault == 'empty_group': edits['block_4'] = []
    elif fault == 'anchor': edits['block_4'][0]['before'] = 'missing anchor'
    elif fault == 'overlap': edits['block_4'].append(deepcopy(edits['block_4'][0]))
    elif fault == 'noop': edits['block_4'][0]['after'] = BEFORE
    elif fault == 'citation': edits['block_4'][0]['after'] += '[K9999]'
    elif fault == 'echo': edits['block_4'][0]['after'] += direct.PATCH_POLICY.strip()
    proposals = pair(inputs, raw)
    if fault in ('request', 'report', 'input'):
        proposals[0] = replace(proposals[0], **{fault + '_sha256': '0' * 64})
    elif fault == 'version': proposals[0] = replace(proposals[0], version='old')
    elif fault == 'pair': proposals[1] = proposals[0]
    with pytest.raises(ValueError):
        direct.preview(inputs, proposals)
    assert inputs.source.report == before


def test_cross_duty_overlap_is_not_silently_deduplicated(sample):
    inputs, value = sample
    raw = repaired(value)
    with pytest.raises(ValueError, match='overlap'):
        direct.preview(inputs, pair(inputs, raw, raw))


def test_summary_and_body_edits_and_multiple_issues_keep_all_other_bytes(sample):
    inputs, value = sample
    raw = repaired(value)
    raw['issues'].append(deepcopy(raw['issues'][0]))
    raw['repairs'][0]['issue_ids'] = list(range(1, len(raw['issues']) + 1))
    block = inputs.source.blocks[5][1]
    raw['repairs'][0]['edits']['block_6'] = [dict(before=block, after=block + ' OFFLINE摘要见证。',
        reason='OFFLINE cross-block expressibility, not semantic acceptance.')]
    result = direct.preview(inputs, pair(inputs, raw))
    assert result.report == inputs.source.report.replace(BEFORE, AFTER).replace(block, block + ' OFFLINE摘要见证。')
    assert len(result.journal['operations']) == 2


def test_repeated_text_can_select_second_block_without_global_guessing(sample):
    inputs, value = sample
    a, b = inputs.source.blocks[3][1], inputs.source.blocks[5][1]
    repeated = 'OFFLINE重复待修句。'
    copied = report_inputs(inputs, inputs.source.report.replace(a, a + repeated).replace(b, b + repeated))
    raw = repaired(value)
    raw['repairs'][0]['edits'] = {'block_6': [dict(before=repeated, after='OFFLINE只改第二处。', reason='Authored test.')]}
    result = direct.preview(copied, pair(copied, raw))
    assert result.report.count(repeated) == 1
    assert result.report == copied.source.report.replace(b + repeated, b + 'OFFLINE只改第二处。')


@pytest.mark.parametrize('after', [
    AFTER + '全样本与中单两口径各仅2局。',
    AFTER + '中单胜场早死均值为9.50。',
    AFTER + '因此减少早死必然导致失败。'])
def test_wrong_reviewer_patch_is_a_counterexample_not_a_false_success(sample, after):
    inputs, value = sample
    result = direct.preview(inputs, pair(inputs, repaired(value, after)))
    assert after in result.report
    assert not result.journal['semantic_approval']
    assert not result.journal['native_acceptance_verified']
    assert result.journal['full_final_review_required']


@pytest.mark.parametrize('boundary', ['empty_source_ids', 'wrong_target_block', 'removed_knowledge_citations'])
def test_structurally_legal_semantic_boundaries_stay_unqualified(sample, boundary):
    inputs, value = sample
    raw = repaired(value)
    if boundary == 'empty_source_ids':
        raw['issues'][0]['source_ids'] = []
    elif boundary == 'wrong_target_block':
        block = inputs.source.blocks[5][1]
        raw['repairs'][0]['edits'] = {
            'block_6': [dict(before=block, after=block + ' OFFLINE错目标段见证。',
                             reason='The issue is structurally mapped but this block is unrelated.')]
        }
    elif boundary == 'removed_knowledge_citations':
        assert re.search(r'\[K\d+\]', inputs.source.report)
        edits = {}
        for number, (_, block) in enumerate(inputs.source.blocks, 1):
            after = re.sub(r'\[K\d+\]', '', block).replace(BEFORE, AFTER)
            if after != block:
                edits[f'block_{number}'] = [dict(before=block, after=after,
                    reason='OFFLINE removes citations while claiming to repair one factual issue.')]
        raw['repairs'][0]['edits'] = edits
    result = direct.preview(inputs, pair(inputs, raw))
    assert result.report != inputs.source.report
    assert not result.journal['semantic_approval']
    assert not result.journal['production_admitted']
    assert result.journal['full_final_review_required']
    if boundary == 'wrong_target_block':
        assert BEFORE in result.report and AFTER not in result.report
        assert {op['block'] for op in result.journal['operations']} == {6}
    elif boundary == 'removed_knowledge_citations':
        assert not re.search(r'\[K\d+\]', result.report)
        assert AFTER in result.report
    else:
        saved = json.loads(result.journal['opinions']['facts']['raw'])
        assert saved['issues'][0]['source_ids'] == []


def test_both_pass_preserves_report_and_terminal_does_not_assemble(sample):
    inputs, _ = sample
    result = direct.preview(inputs, pair(inputs, PASS))
    assert result.report == inputs.source.report and result.journal['operations'] == []
    with pytest.raises(ValueError, match='terminal'):
        direct.preview(inputs, pair(inputs, dict(PASS, verdict='fail', score=0)))


def test_global_patch_cap_spans_both_duties(sample):
    inputs, value = sample
    marks = ''.join(chr(0xE000 + i) for i in range(513))
    block = inputs.source.blocks[3][1]
    copied = report_inputs(inputs, inputs.source.report.replace(block, block + marks, 1))
    facts = repaired(value)
    facts['repairs'][0]['edits']['block_4'] = [dict(before=c, after='a', reason='OFFLINE cap test.') for c in marks[:512]]
    result = direct.preview(copied, pair(copied, facts))
    assert len(result.journal['operations']) == 512
    completion = repaired(value)
    completion['repairs'][0]['edits']['block_4'] = [dict(before=marks[-1], after='b', reason='OFFLINE cap test.')]
    with pytest.raises(ValueError, match='operation_limit'):
        direct.preview(copied, pair(copied, facts, completion))


def test_duplicate_anchor_and_changed_source_reject_even_without_edit(sample):
    inputs, value = sample
    copied = report_inputs(inputs, inputs.source.report.replace(BEFORE, BEFORE + BEFORE))
    with pytest.raises(ValueError, match='anchor_not_unique'):
        direct.preview(copied, pair(copied, repaired(value)))
    proposals = pair(inputs, PASS)
    pack = json.loads(inputs.pack_json)
    pack['facts']['OFFLINE_unexpected'] = 'changed source'
    with pytest.raises(ValueError):
        direct.preview(replace(inputs, pack_json=compact(pack)), proposals)
    duplicate_json = compact(PASS).replace('"repairs":[]', '"repairs":[],"repairs":[]')
    with pytest.raises(ValueError, match='duplicate_key'):
        direct.bind(inputs, 'facts', duplicate_json)


def test_all_fifteen_complete_inputs_fit_without_network_and_counterexamples_remain():
    from scripts.audit_review_duty_direct_patch import audit
    result = audit()
    assert len(result['complete_request_audit']) == 15
    assert max(r['input_ceiling'] for row in result['complete_request_audit']
        for r in row['requests'].values()) <= 64000
    assert len(result['authored_witnesses']) == 4
    assert all(w['literal_replacement_preserved'] and not w['semantic_approval']
        for w in result['authored_witnesses'])
    assert not result['execution_ready'] and not result['product_budget_compatible']
    assert result['natural_task_request_count'] == 6
