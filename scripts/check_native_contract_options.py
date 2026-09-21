"""Offline contract comparison using immutable public responses and full reports.

All new judgments/edits are analyst witnesses, never new model observations.
No credential loading or live Provider construction occurs here.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_integrated_runtime import Exchange, BudgetedReviewSender, ReceiptedStreamProvider
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_semantic_sources import source_catalog
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.harness.steps import EvaluationRequest, KnowledgeEvidence, KnowledgeCitation, RevisionRequest
from app.providers.models import ChatResponse, TokenUsage
from app.providers.errors import ProviderResponseError
from scripts.check_native_claim_scope import load_controls
from scripts.check_golden_native_issues_review import scripted
from scripts.native_contract_options import (OfflineEditorWorkflow, anchored_request, validate_anchors,
    editor_request, validate_editor, body)

ROOT = Path(__file__).resolve().parents[1]
ACTUAL = ROOT/'data/evaluation/results/golden_native_claim_scope_result_354d752.json'
PASS = compact(dict(score=95, verdict='pass', issues=[], issue_resolutions=[]))


def fixture_request(filename):
    saved = json.loads((ROOT/'tests/fixtures'/filename).read_text(encoding='utf-8'))
    raw = saved['evaluation_request']
    k = raw['knowledge']
    knowledge = KnowledgeEvidence(context=k['context'], source_ids=tuple(k['source_ids']),
        citations=tuple(KnowledgeCitation(**c) for c in k['citations']), abstained=k['abstained'])
    return EvaluationRequest(raw['player_summary'], raw['deterministic_report'], knowledge,
        raw['report'], raw['user_utterance']), saved


def actual_case(index):
    _, requests, _ = load_controls()
    saved = next(c for c in json.loads(ACTUAL.read_text(encoding='utf-8'))['cases'] if c['index'] == index)
    req = requests[index-1]
    assert saved['original_report'] == req.report
    for r in saved['responses']:
        assert digest(r['content']) == r['content_sha256']
    return req, saved


def computed_root(inputs):
    return next(i for i, entry in source_catalog(inputs, include_role_contrasts=True,
        computed_layout='statistic_series').items() if entry.key == 'derived/computed_evidence')


def editor_value(inputs, review_raw, report, dispositions, explanations=None):
    source = computed_root(inputs)
    return dict(review_sha256=digest(review_raw), decisions=[dict(issue_id=n,
        disposition=choice, source_ids=[source], explanation=(explanations[n-1] if explanations else
            '分析者构造的合同见证；不是模型裁决或语义成功证据。'))
        for n, choice in enumerate(dispositions, 1)], report=report)


def corrected_case3():
    req, saved = actual_case(3)
    inputs = native.build_inputs(req)
    original = '将所选全部 5 局（包括辅助局）合并计算后，胜局与败局的平均补刀/分钟也基本持平。'
    # Change the sole explicitly wrong comparison, preserving every other byte.
    correct = ('将所选全部 5 局（包括辅助局）合并计算后，胜局补刀均值为 8.805/分钟，'
               '败局约为 6.45/分钟，两组并非基本持平。')
    revised = req.report.replace(original, correct)
    assert req.report.count(original) == 1
    raw = saved['responses'][0]['content']
    value = editor_value(inputs, raw, revised, ['apply', 'withdraw'], [
        '原block6明确合并五局，胜败补刀均值约8.8与6.45，并非基本持平；修正此比较。',
        'block4泛指均值，未声称所有指标均下降；block13/14已分指标说明方向。首评补入全称，故撤销该误报，保留block4。'])
    return req, raw, value


class OfflineResponses(ReceiptedStreamProvider):
    """Use the real shared budget/receipt boundary with scripted responses only."""
    def __init__(self, responses, *, charge_ceiling=False):
        self.responses, self.requests = list(responses), []
        self.charge_ceiling, self.last_exchange = charge_ceiling, None

    def chat(self, request):
        self.requests.append(request)
        if len(self.requests) > len(self.responses):
            raise AssertionError('unexpected_scripted_call')
        usage = TokenUsage(input_tokens=size(request) if self.charge_ceiling else 10,
                           output_tokens=request.max_tokens if self.charge_ceiling else 10)
        response = ChatResponse(content=self.responses[len(self.requests)-1], provider=self.provider_name,
            model=self.model_name, usage=usage, finish_reason='stop')
        self.last_exchange = Exchange(request, response,
            hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
        return response


def path(req, responses, *, charge_ceiling=False):
    provider = OfflineResponses(responses, charge_ceiling=charge_ceiling)
    sender = BudgetedReviewSender(provider)
    flow = OfflineEditorWorkflow(sender)
    initial = flow.evaluate(req)
    draft = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, initial))
    final = flow.evaluate(replace(req, report=draft.report))
    assert final.verdict.value == 'pass' and flow.revisions == 1
    assert flow.editor_journal['semantic_approval'] is False
    return flow, provider, sender


def recovery_responses(inputs, first, edited):
    malformed = json.loads(first)
    malformed['score'] = str(malformed['score'])
    fixed = json.loads(first)
    fixed['issue_resolutions'] = [dict(previous_id=n, disposition='replaced', final_issue=n,
        source_ids=issue['source_ids'], explanation='分析者见证：修正score类型并显式对应每个旧问题。')
        for n, issue in enumerate(fixed['issues'], 1)]
    recovered = compact(fixed)
    value = deepcopy(edited)
    value['review_sha256'] = digest(recovered)
    return [compact(malformed), recovered, compact(value), PASS+'\nUnstructured ending', PASS]


def sizes(requests):
    return [dict(phase=r.metadata['review_phase'], input_ceiling=size(r), output_reservation=r.max_tokens)
            for r in requests]


def reservation(rows):
    return sum(row['input_ceiling']+row['output_reservation'] for row in rows)


def assert_complete(request, inputs):
    sent = body(request)
    expected = native.request_data(inputs)
    deterministic = expected.pop('deterministic_source_facts')
    assert all(sent[k] == v for k, v in expected.items())
    assert deterministic in request.messages[2].content
    assert not {'targets', 'expected_report', 'analyst_rationale'}.intersection(sent)


def audit():
    data, requests, _ = load_controls()
    req, first, edited = corrected_case3()
    inputs = native.build_inputs(req)
    anchored = json.loads(first)
    for issue in anchored['issues']:
        issue['claim'] = inputs.source.blocks[issue['block']-1][1]
        issue['context'] = [dict(block=n, text=inputs.source.blocks[n-1][1]) for n in (13, 14)]
    validate_anchors(compact(anchored), inputs)
    shapes = []
    for case, request in zip(data['cases'], requests, strict=True):
        current = native.build_inputs(request)
        a = anchored_request(current)
        assert_complete(a, current)
        shapes.append(dict(id=case['id'], report_sha256=digest(request.report),
            native_input_ceiling=size(native.request(current)), anchored_input_ceiling=size(a)))

    edit_request = editor_request(inputs, first)
    assert_complete(edit_request, inputs)
    assert body(edit_request)['proposed_review'] == json.loads(first)
    assert 'accepted_review' not in body(edit_request)
    wire, journal = validate_editor(compact(edited), inputs, first)
    revised_blocks = native.build_inputs(replace(req, report=wire.report)).source.blocks
    changed = [n for n, (a, b) in enumerate(zip(inputs.source.blocks, revised_blocks, strict=True), 1) if a != b]
    assert changed == [6]
    normal = sizes(path(req, [first, compact(edited), PASS], charge_ceiling=True)[1].requests)
    five = sizes(path(req, recovery_responses(inputs, first, edited), charge_ceiling=True)[1].requests)

    negatives = []
    _, saved = actual_case(3)
    for name, report, dispositions in [
        ('withdraw_true_problem', req.report, ['withdraw', 'withdraw']),
        ('apply_without_fixing_problem', req.report+'\n', ['apply', 'withdraw']),
        ('apply_false_positive', saved['revised_report'], ['apply', 'apply']),
        ('withdraw_but_edit_false_positive', saved['revised_report'], ['apply', 'withdraw']),
    ]:
        wrong = editor_value(inputs, first, report, dispositions)
        _, counter = validate_editor(compact(wrong), inputs, first)
        negatives.append(dict(id=name, protocol_valid=True, semantic_acceptance=False,
            raw_sha256=digest(compact(wrong)), editor_output=wrong,
            semantic_approval=counter['semantic_approval']))

    # Use the committed full historical request, not claim sources substituted
    # into a different report. Identity equivalence is checked locally separately.
    historic, fixture = fixture_request('native_heading_recheck_failure.json')
    historical_data = json.loads((ROOT/'data/evaluation/datasets/golden_observed_review_controls_v1.json').read_text(encoding='utf-8'))
    history_shapes = []
    history_requests = []
    for case in historical_data['cases']:
        assert digest(case['report']) == case['report_sha256']
        current = replace(historic, report=case['report'], user_utterance=historical_data['user_utterance'])
        history_requests.append(current)
        built = native.build_inputs(current)
        history_shapes.append(dict(id=case['id'], report_sha256=digest(current.report),
            anchored_input_ceiling=size(anchored_request(built))))
    old_negative = history_requests[1]
    old_inputs = native.build_inputs(old_negative)
    target = historical_data['cases'][1]['target']
    block = next(i for i, (_, t) in enumerate(old_inputs.source.blocks, 1) if target in t)
    old_first = compact(scripted(old_inputs, block=block))
    old_edit = editor_value(old_inputs, old_first, history_requests[0].report, ['apply'])
    historic_responses = recovery_responses(old_inputs, old_first, old_edit)
    old_five = sizes(path(old_negative, historic_responses)[1].requests)
    # Verify the real gate with saturated synthetic usage as well as arithmetic.
    saturated = OfflineResponses(historic_responses, charge_ceiling=True)
    budget = BudgetedReviewSender(saturated)
    flow = OfflineEditorWorkflow(budget)
    initial = flow.evaluate(old_negative)
    draft = flow.revise(RevisionRequest(old_negative.player_summary, old_negative.deterministic_report,
        old_negative.knowledge, old_negative.report, initial))
    try:
        flow.evaluate(replace(old_negative, report=draft.report))
    except ProviderResponseError as error:
        assert error.code == 'token_budget_exhausted'
    else:
        raise AssertionError('saturated historical budget must reject fifth call')
    assert len(saturated.requests) == 4 and flow.stopped
    tail_artifact = json.loads((ROOT/'data/evaluation/results/golden_native_review_result_a04df23.json').read_text(encoding='utf-8'))
    assert digest(native.build_inputs(history_requests[0]).data_json) == tail_artifact['receipt']['input_sha256']
    # Full-output reservation is a conservative measurement; actual usage plus
    # the next reservation governs execution. Do not silently raise the budget.
    long = anchored_request(native.build_inputs(historic), previous_raw=fixture['raw'],
        diagnostics=[{'code': 'legacy_bad_envelope'}])
    assert body(long)['previous_review'] == native.previous.provisional_review(fixture['raw'])[0]
    assert body(long)['previous_non_json_suffix'] == native.previous.provisional_review(fixture['raw'])[1]
    attribution = json.loads((ROOT/'data/evaluation/datasets/golden_native_product_attribution_controls_v1.json').read_text(encoding='utf-8'))
    attribution_shapes = []
    for case in attribution['cases']:
        a_req = replace(requests[0], report=case['report'], user_utterance=attribution['user_utterance'])
        built = native.build_inputs(a_req)
        attribution_shapes.append(dict(id=case['id'], report_sha256=digest(a_req.report),
            anchored_input_ceiling=size(anchored_request(built))))

    return dict(evidence_kind='offline_contract_comparison_not_model_semantics', provider_calls=0,
        semantic_fix_proven=False, production_admitted=False,
        source_artifact_sha256=hashlib.sha256(ACTUAL.read_bytes()).hexdigest(),
        actual_failed_review_sha256=digest(first), actual_failure_preserved=True,
        option_a=dict(false_positive_still_protocol_valid=True, anchored_counterexample=anchored,
            claim_shapes=shapes, history_shapes=history_shapes, attribution_shapes=attribution_shapes,
            complete_historical_reassessment_input_ceiling=size(long)),
        option_b=dict(analyst_editor_witness=edited, changed_blocks=changed,
            unaffected_block6_prefix_preserved=wire.report.split('将所选全部 5 局',1)[0] == req.report.split('将所选全部 5 局',1)[0],
            original_review_retained=journal['review_raw']==first, editor_input_ceiling=size(edit_request),
            normal_three_call_path=normal, maximum_five_call_path=five,
            five_call_full_reservation=reservation(five), historical_five_call_path=old_five,
            historical_full_reservation=reservation(old_five), total_budget=401920,
            historical_full_reservation_fits=reservation(old_five)<=401920,
            historical_saturated_budget=dict(completed_calls=len(saturated.requests),
                stop_reason='token_budget_exhausted', sixth_call_possible=False,
                usage_kind='synthetic_ceiling_not_actual_model_usage', total_usage=budget.budget.tokens),
            semantically_wrong_but_structurally_valid=negatives),
        decision='A_not_a_standalone_fix_B_offline_candidate_only',
        limitations=['All newly supplied judgments and edited reports are analyst authored.',
            'Valid source IDs and dispositions do not prove entailment or correct edits.',
            'Initial false positives remain failures even if an editor repairs them.',
            'Product generation and elapsed runtime need separate shared-budget checks.',
            'Development unadjudicated-finding guard and both live blocks remain active.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = audit()
    if args.output:
        write_new_json(args.output, result)
    print(compact({k:v for k,v in result.items() if k not in ('option_a', 'option_b')}))
    print(compact(dict(editor_input=result['option_b']['editor_input_ceiling'],
        five=result['option_b']['five_call_full_reservation'],
        historic_five=result['option_b']['historical_full_reservation'])))
