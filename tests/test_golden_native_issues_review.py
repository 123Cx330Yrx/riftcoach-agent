"""Native result obligations and complete input; scripted judgments are not quality proof."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from app.evaluation import golden_native_issues_review as candidate
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
from app.evaluation.golden_review_experiment import compact, digest
from app.harness.steps import RevisionRequest
from app.providers.errors import ProviderResponseError
from tests.test_golden_integrated_review import ReplayProvider
from tests.test_golden_semantic_review import (
    evaluation_request, retrieved_knowledge, source_id, request_data,
)


def opinion(inputs, *, block=None):
    issues = [] if block is None else [dict(block=block, source_ids=[source_id(inputs)],
        severity='medium', category='fact_error', explanation='合成问题：提供的官方来源与报告不一致。',
        suggested_correction='按原始官方来源修订。')]
    return dict(score=95 if block is None else 70, verdict='pass' if block is None else 'needs_revision',
        issues=issues, issue_resolutions=[])


def flow_with(replies, *, clock=None):
    provider = ReplayProvider(lambda _, n: replies[n - 1])
    sender = BudgetedReviewSender(provider, clock=clock)
    return candidate.NativeBusinessReviewWorkflow(sender), provider, sender


def test_full_report_and_sources_are_still_present_without_rewritten_passed_paragraphs():
    req = evaluation_request('## 数据已证明长期能力\n\n正确前句。错误尾句。[K1]', knowledge=retrieved_knowledge())
    inputs = candidate.build_inputs(req)
    data = request_data(candidate.request(inputs))
    assert data['source_index']['blocks'] == candidate.strict_json(inputs.data_json)['source_index']['blocks']
    assert '错误尾句' in compact(data) and '数据已证明长期能力' in compact(data)
    assert data['user_utterance'] == req.user_utterance
    assert req.deterministic_report in candidate.request(inputs).messages[2].content
    # No synthetic accepted-paragraph claims are invented by host.
    result, _, journal = candidate.validate(compact(opinion(inputs)), inputs)
    assert result.verdict == 'pass' and journal['selected_sources'] == []
    assert not journal['semantic_approval']


@pytest.mark.parametrize('block', [1, 2])
def test_title_and_body_findings_bind_whole_original_text_and_real_source(block):
    req = evaluation_request('## 已证明防抓能力\n\n前句和尾句都属于报告。')
    inputs = candidate.build_inputs(req)
    value = opinion(inputs, block=block)
    payload, _, journal = candidate.validate(compact(value), inputs)
    assert payload.issues[0].quote == inputs.source.blocks[block - 1][1]
    source = journal['selected_sources'][0]['selected_sources'][0]
    assert source['key'] == 'source/official_patch' and source['value']['patch_version'] == '16.17'


@pytest.mark.parametrize('mutation', ['unknown_block', 'bool_block', 'unknown_source', 'duplicate_source', 'pass_with_issue', 'revision_without_issue', 'old_reviews'])
def test_final_contract_rejects_bad_targets_sources_verdicts_and_legacy_output(mutation):
    inputs = candidate.build_inputs(evaluation_request())
    value = opinion(inputs, block=1)
    if mutation == 'unknown_block': value['issues'][0]['block'] = 2
    if mutation == 'bool_block': value['issues'][0]['block'] = True
    if mutation == 'unknown_source': value['issues'][0]['source_ids'] = [999]
    if mutation == 'duplicate_source': value['issues'][0]['source_ids'] *= 2
    if mutation == 'pass_with_issue': value['verdict'] = 'pass'
    if mutation == 'revision_without_issue': value['issues'] = []
    if mutation == 'old_reviews': value['reviews'] = []
    with pytest.raises(ValueError): candidate.validate(compact(value), inputs)


def test_multiple_different_issues_on_same_block_are_preserved():
    inputs = candidate.build_inputs(evaluation_request())
    value = opinion(inputs, block=1)
    second = dict(value['issues'][0], explanation='同一段另有独立的无依据外推问题。', category='causality')
    value['issues'].append(second)
    payload, _, journal = candidate.validate(compact(value), inputs)
    assert len(payload.issues) == len(journal['selected_sources']) == 2


@pytest.mark.parametrize('disposition', ['retained', 'replaced', 'withdrawn'])
def test_first_findings_have_explicit_disposition_and_source_binding(disposition):
    inputs = candidate.build_inputs(evaluation_request())
    before = opinion(inputs, block=1)
    value = deepcopy(before)
    if disposition == 'withdrawn': value = opinion(inputs)
    if disposition == 'replaced': value['issues'][0]['explanation'] = '用实际来源更正旧问题。'
    with pytest.raises(ValueError, match='native_issue_resolution_inventory'):
        candidate.validate(compact(value), inputs, previous_raw=compact(before))
    value['issue_resolutions'] = [dict(previous_id=1, disposition=disposition,
        final_issue=None if disposition == 'withdrawn' else 1, source_ids=[source_id(inputs)],
        explanation='脚本处置见证，需要真实模型语义验证。')]
    _, _, journal = candidate.validate(compact(value), inputs, previous_raw=compact(before))
    assert journal['previous_issues'][0]['block'] == 1
    assert journal['previous_issues'][0]['issue'] == before['issues'][0]
    if disposition == 'retained':
        value['issues'][0]['block'] = 2
        with pytest.raises(ValueError): candidate.validate(compact(value), inputs, previous_raw=compact(before))


def test_no_source_problem_is_explicit_and_does_not_fabricate_an_id():
    inputs = candidate.build_inputs(evaluation_request())
    value = opinion(inputs, block=1)
    value['issues'][0]['source_ids'] = []
    _, _, journal = candidate.validate(compact(value), inputs)
    assert journal['selected_sources'][0]['selected_sources'] == []


def test_malformed_first_and_legacy_findings_are_not_silently_dropped():
    inputs = candidate.build_inputs(evaluation_request())
    first = {'reviews': [{'block': 1, 'issues': 'malformed original finding'}], 'issues': [{'block': 1, 'source_ids': []}]}
    assert len(candidate.prior_issues(first)) == 2
    value = opinion(inputs)
    with pytest.raises(ValueError, match='native_issue_resolution_inventory'):
        candidate.validate(compact(value), inputs, previous_raw=compact(first))
    assert request_data(candidate.request(inputs, previous_raw=compact(first)))['previous_review'] == first


@pytest.mark.parametrize('report,knowledge', [('建议无编号。', retrieved_knowledge()), ('建议[K999]。', retrieved_knowledge())])
def test_pass_still_requires_real_knowledge_citations(report, knowledge):
    inputs = candidate.build_inputs(evaluation_request(report, knowledge=knowledge))
    with pytest.raises(ValueError, match='knowledge_citation'):
        candidate.validate(compact(opinion(inputs)), inputs)


@pytest.mark.parametrize('fault', ['high_injection', 'conflict', 'truncation'])
def test_terminal_responses_do_not_spend_a_reassessment(fault):
    req = evaluation_request(); value = opinion(candidate.build_inputs(req), block=1)
    if fault == 'high_injection': value['issues'][0].update(category='prompt_injection', severity='high')
    raw = compact(value)
    if fault == 'conflict': raw = '{"score":0,' + raw[1:]
    if fault == 'truncation': raw = raw[:-1]
    flow, provider, _ = flow_with([raw])
    with pytest.raises(ValueError): flow.evaluate(req)
    assert flow.stopped and len(provider.requests) == 1


def test_complete_response_uses_one_call_and_tail_gets_one_full_reassessment():
    req = evaluation_request(); raw = compact(opinion(candidate.build_inputs(req)))
    flow, provider, _ = flow_with([raw]); assert flow.evaluate(req).verdict.value == 'pass'
    assert len(provider.requests) == 1
    bad = raw + '\nUnstructured commentary'
    flow, provider, _ = flow_with([bad, raw]); assert flow.evaluate(req).verdict.value == 'pass'
    data = request_data(provider.requests[1])
    assert len(provider.requests) == 2 and data['previous_non_json_suffix'] == '\nUnstructured commentary'
    assert flow.last_journal['previous_raw'] == bad and data['previous_raw_sha256'] == digest(bad)


@pytest.mark.parametrize('field', ['summary', 'passed_checks'])
def test_unrequested_fact_narratives_are_rejected_not_discarded(field):
    req = evaluation_request(); inputs = candidate.build_inputs(req)
    value = opinion(inputs)
    wrong = '错误来源或胜负事实。'
    value[field] = wrong if field == 'summary' else [wrong]
    raw = compact(value)
    with pytest.raises(ValueError): candidate.validate(raw, inputs)
    flow, provider, _ = flow_with([raw, compact(opinion(inputs))])
    result = flow.evaluate(req)
    assert request_data(provider.requests[1])['previous_review'][field] == value[field]
    assert flow.last_journal['previous_raw'] == raw
    assert result.summary == '模型未发现需要修订的问题。'
    assert not result.passed_checks
    # Repeated bad output must stop; no silent field removal or third attempt.
    flow, provider, _ = flow_with([raw, raw])
    with pytest.raises(ValueError): flow.evaluate(req)
    assert flow.stopped and len(provider.requests) == 2


def test_actual_wrong_summary_is_preserved_and_cannot_be_reclassified_as_pass(monkeypatch):
    from tests.test_golden_native_reassessment import recorded_failure
    original_open = Path.open
    def committed_only(path, *args, **kwargs):
        assert 'data/runs/' not in path.as_posix(), 'replay must not depend on ignored local runs'
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', committed_only)
    artifact = candidate.strict_json(Path('data/evaluation/results/golden_native_review_result_42a5fc0.json').read_text(encoding='utf-8'))
    raw = artifact['raw']
    # Reconstruct from committed fixtures only; CI has no ignored local runs.
    _, req = recorded_failure()
    controls = candidate.strict_json(Path('data/evaluation/datasets/golden_observed_review_controls_v1.json').read_text(encoding='utf-8'))
    req = replace(req, report=controls['cases'][0]['report'], user_utterance=controls['user_utterance'])
    inputs = candidate.build_inputs(req)
    assert digest(inputs.data_json) == artifact['receipt']['input_sha256']
    assert '辅助1局0负' in raw and not artifact['manual_semantic_acceptance']
    with pytest.raises(ValueError): candidate.validate(raw, inputs)
    correction = request_data(candidate.request(inputs, previous_raw=raw))
    assert correction['previous_review'] == candidate.strict_json(raw)
    assert correction['previous_raw_sha256'] == digest(raw)
    # The test asserts rejection/preservation, not semantic correction by a model.


def test_problem_and_failed_status_summaries_only_describe_the_review_outcome():
    inputs = candidate.build_inputs(evaluation_request())
    value = opinion(inputs, block=1)
    payload, _, _ = candidate.validate(compact(value), inputs)
    assert payload.summary == '模型提出 1 项问题，需要修订后复评。'
    assert payload.issues[0].explanation == value['issues'][0]['explanation']
    assert not payload.passed_checks
    value['verdict'] = 'fail'
    payload, _, _ = candidate.validate(compact(value), inputs)
    assert payload.summary == '模型评估未通过，停止自动修订。'


def test_actual_markdown_tail_can_reach_one_full_reassessment_without_being_trimmed_to_pass():
    from tests.test_golden_native_reassessment import recorded_failure
    artifact = candidate.strict_json(Path('data/evaluation/results/golden_native_review_result_a04df23.json').read_text(encoding='utf-8'))
    _, req = recorded_failure()
    controls = candidate.strict_json(Path('data/evaluation/datasets/golden_observed_review_controls_v1.json').read_text(encoding='utf-8'))
    req = replace(req, report=controls['cases'][0]['report'], user_utterance=controls['user_utterance'])
    inputs = candidate.build_inputs(req)
    assert digest(inputs.data_json) == artifact['receipt']['input_sha256']
    raw = artifact['raw']
    with pytest.raises(ValueError): candidate.validate(raw, inputs)
    flow, provider, _ = flow_with([raw, compact(opinion(inputs))])
    result = flow.evaluate(req)
    data = request_data(provider.requests[1])
    assert '[K1]' in data['previous_non_json_suffix']
    assert data['previous_raw_sha256'] == digest(raw)
    assert flow.last_journal['previous_raw'] == raw
    assert len(provider.requests) == 2 and result.verdict.value == 'pass'
    # The second response is scripted; this proves reachability, not live repair.
    flow, provider, _ = flow_with([raw, raw])
    with pytest.raises(ValueError): flow.evaluate(req)
    assert flow.stopped and len(provider.requests) == 2


@pytest.mark.parametrize('changed', ['summary', 'report', 'utterance'])
def test_recheck_is_bound_to_revised_text_same_facts_and_original_user(changed):
    from app.report_validation import COACH_REPORT_HEADINGS
    text = '\n\n'.join(COACH_REPORT_HEADINGS) + '\n\n官方补丁16.17。'
    req = evaluation_request(text); revised = text + '\n\n已修改。'
    inputs = candidate.build_inputs(req)
    first = opinion(inputs, block=len(inputs.source.blocks))
    flow, provider, _ = flow_with([compact(first), revised])
    result = flow.evaluate(req)
    draft = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, result))
    recheck = replace(req, report=draft.report)
    if changed == 'summary':
        summary = deepcopy(req.player_summary)
        summary['player']['riot_id'] = 'Different#KR1'
        recheck = replace(recheck, player_summary=summary)
    if changed == 'report': recheck = replace(recheck, report=draft.report + '不同内容')
    if changed == 'utterance': recheck = replace(recheck, user_utterance='其他请求')
    with pytest.raises(ValueError, match='source_changed'): flow.evaluate(recheck)
    assert len(provider.requests) == 2


def test_budget_still_rejects_before_provider_and_does_not_retry():
    req = evaluation_request(); inputs = candidate.build_inputs(req)
    flow, provider, sender = flow_with([compact(opinion(inputs))])
    sender.budget.calls = 5
    with pytest.raises(ProviderResponseError): flow.evaluate(req)
    assert flow.stopped and not provider.requests


def test_oversized_previous_opinion_is_rejected_without_truncation_or_call():
    req = evaluation_request(); inputs = candidate.build_inputs(req)
    first = opinion(inputs)
    first['untrusted_extra'] = '完整保留' * 20000
    flow, provider, _ = flow_with([compact(first)])
    with pytest.raises(ValueError): flow.evaluate(req)
    assert flow.stopped and len(provider.requests) == 1


def test_reassessment_cannot_erase_or_change_a_retained_legacy_finding():
    inputs = candidate.build_inputs(evaluation_request())
    old_issue = dict(source_ids=[source_id(inputs)], severity='medium', category='fact_error',
        explanation='原问题原值', suggested_correction='原建议')
    before = {'reviews': [{'block': 1, 'issues': [old_issue]}]}
    value = opinion(inputs, block=1)
    value['issue_resolutions'] = [dict(previous_id=1, disposition='retained', final_issue=1,
        source_ids=[source_id(inputs)], explanation='错误声称完全保留。')]
    with pytest.raises(ValueError, match='native_retained_issue_changed'):
        candidate.validate(compact(value), inputs, previous_raw=compact(before))
    value['issue_resolutions'][0]['disposition'] = 'replaced'
    _, _, journal = candidate.validate(compact(value), inputs, previous_raw=compact(before))
    assert journal['previous_issues'][0]['issue'] == old_issue
