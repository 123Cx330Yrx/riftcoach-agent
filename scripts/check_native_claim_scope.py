"""Committed full-report scope diagnostics; scripted paths are not model quality."""
import argparse
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.harness.steps import EvaluationRequest, KnowledgeCitation, KnowledgeEvidence, RevisionRequest
from app.providers.models import ChatResponse, TokenUsage

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / 'data/evaluation/datasets/golden_native_claim_scope_controls_v1.json'


def load_controls():
    data = json.loads(DATASET.read_text(encoding='utf-8'))
    for name, hash_key in [('parent_dataset', 'parent_sha256'), ('origin_result', 'origin_result_sha256')]:
        if hashlib.sha256((ROOT / data[name]).read_bytes()).hexdigest() != data[hash_key]:
            raise ValueError('claim_scope_origin_changed')
    parent = json.loads((ROOT / data['parent_dataset']).read_text(encoding='utf-8'))
    if data['source_files'] != parent['source_files'] or data['user_utterance'] != parent['user_utterance']:
        raise ValueError('claim_scope_sources_changed')
    # The committed actual-request fixture makes this audit reproducible without
    # ignored local run files, credentials, a Provider, or a synthetic source.
    saved = json.loads((ROOT / 'tests/fixtures/native_missing_block_reassessment.json').read_text(encoding='utf-8'))
    raw = saved['evaluation_request']
    k = raw['knowledge']
    knowledge = KnowledgeEvidence(context=k['context'], source_ids=tuple(k['source_ids']),
        citations=tuple(KnowledgeCitation(**c) for c in k['citations']), abstained=k['abstained'])
    original = EvaluationRequest(raw['player_summary'], raw['deterministic_report'], knowledge,
        raw['report'], raw['user_utterance'])
    if digest(native.build_inputs(original).data_json) != saved['source_input_sha256']:
        raise ValueError('claim_scope_request_source_changed')
    if original.user_utterance != data['user_utterance']:
        raise ValueError('claim_scope_user_changed')
    if len({c['id'] for c in data['cases']}) != len(data['cases']):
        raise ValueError('claim_scope_duplicate_case')
    requests = []
    for case in data['cases']:
        if digest(case['report']) != case['report_sha256'] or any(case['report'].count(t) != 1 for t in case['targets']):
            raise ValueError('claim_scope_report_changed')
        if case['expected_report'] not in ('accept', 'reject'):
            raise ValueError('claim_scope_label_invalid')
        requests.append(replace(original, report=case['report']))
    return data, requests, original


def scripted_path(req, responses):
    issued = []
    def send(request):
        issued.append(request)
        if len(issued) > len(responses):
            raise AssertionError('unexpected extra call')
        reply = ChatResponse(content=responses[len(issued)-1], provider='zhipu', model='glm-5.3-flash',
            finish_reason='stop', usage=TokenUsage(input_tokens=10, output_tokens=10))
        return Exchange(request, reply, hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
    workflow = native.NativeBusinessReviewWorkflow(send)
    initial = workflow.evaluate(req)
    revision = workflow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, initial))
    final = workflow.evaluate(replace(req, report=revision.report))
    return final, issued


def audit_reassessment():
    """Preserve the numeric failure independently from the new wire contract."""
    data, requests, _ = load_controls()
    fixture = json.loads((ROOT / 'tests/fixtures/native_claim_scope_retained_changed.json').read_text(encoding='utf-8'))
    origin = ROOT / fixture['origin_result']
    assert hashlib.sha256(origin.read_bytes()).hexdigest() == fixture['origin_result_sha256']
    original = json.loads(origin.read_text(encoding='utf-8'))['cases'][3]
    req = requests[3]
    inputs = native.build_inputs(req)
    assert fixture['source_input_sha256'] == digest(inputs.data_json)
    assert fixture['report_sha256'] == digest(req.report)
    assert fixture['responses'] == original['responses']
    for saved in fixture['responses']:
        assert digest(saved['content']) == saved['content_sha256']
    first, second = [r['content'] for r in fixture['responses']]
    try:
        native.validate_legacy_v31(second, inputs, previous_raw=first)
    except ValueError as error:
        assert str(error) == 'native_retained_issue_changed'
    else:
        raise AssertionError('historical failure lost')

    # Counterexample: resolving only the disposition does not repair semantics.
    relabelled = json.loads(second)
    relabelled['issue_resolutions'][0]['disposition'] = 'replaced'
    _, _, journal = native.validate(compact(relabelled), inputs, previous_raw=first)
    assert '纯中单口径均值 33.5' in journal['parsed_review']['issues'][0]['explanation']
    rows = req.player_summary['matches']
    middle = [r for r in rows if r['role'] == 'MIDDLE' and r['included_in_aggregate']]
    values = sorted(Decimal(str(r['vision_score'])) for r in middle)
    avg = lambda rs, metric: sum(Decimal(str(r[metric])) for r in rs) / len(rs)
    means = dict(cohort_mean=avg(middle, 'vision_score'),
        cohort_median=(values[1]+values[2])/2,
        win_mean=avg([r for r in middle if r['win']], 'vision_score'),
        loss_mean=avg([r for r in middle if not r['win']], 'vision_score'))
    assert means == dict(cohort_mean=Decimal('33.75'), cohort_median=Decimal('33.5'),
                         win_mean=Decimal('33.5'), loss_mean=Decimal('34'))
    assert avg(middle, 'deaths_before_15') == Decimal('1.5')
    sent = native.request_data(inputs)['computed_evidence']
    metric_index = sent['metrics'].index('vision_score')
    for key, expected in means.items():
        assert Decimal(sent['cohorts']['MIDDLE'][key][metric_index]) == expected
    from app.evaluation.golden_semantic_sources import source_catalog
    catalog = source_catalog(inputs, include_role_contrasts=True, computed_layout='statistic_series')
    source = next(n for n, entry in catalog.items() if entry.key == 'derived/computed_evidence')
    assert native.resolve_refs(inputs, [source])[0]['value'] == sent

    # A separately labelled analyst correction, never a mutation of model raw.
    corrected = deepcopy(relabelled)
    corrected['issues'][0].update(source_ids=[source],
        explanation='原文把所选五局每一指标都说成被辅助局拉低；视野分中单全组均值33.75、辅助90、合并45，早死中单1.5、辅助7、合并2.6，均为抬高，故全称断言错误。',
        suggested_correction='分别说明各指标方向；视野分与15分钟前死亡均值被辅助局抬高，不能声称每一个指标都被拉低。')
    corrected['issue_resolutions'][0].update(source_ids=[source],
        explanation='分析者构造的接口见证：当前问题接替旧问题，并按完整来源纠正评估自身的中单全组均值；不是模型修复证明。')
    sentence = ('视野分的中单全组均值为 33.75、中位数为 33.5，胜局均值为 33.5、败局均值为 34；'
        '辅助局为 90、合并五局均值为 45。15 分钟前死亡的中单均值为 1.5、辅助为 7、合并均值为 2.6，'
        '这两个指标均被辅助局抬高，应按位置分开解读。')
    target = data['cases'][3]['targets'][0]
    correct_report = req.report.replace(target, sentence)
    assert correct_report != req.report and target not in correct_report
    final = compact(dict(score=95, verdict='pass', issues=[], issue_resolutions=[]))
    accepted, issued = scripted_path(req, [first, compact(corrected), correct_report, final+'\nUnstructured ending', final])
    assert accepted.verdict.value == 'pass' and len(issued) == 5
    assert all(size(r) <= 63936 for r in issued)
    reserved = sum(size(r)+r.max_tokens for r in issued)
    assert reserved <= 401920
    controls = []
    for name, expected, report in [
        ('explicit_statistic_bindings', 'accept', correct_report),
        ('winning_mean_as_whole_cohort', 'reject', correct_report.replace('全组均值为 33.75', '全组均值为 33.5')),
        ('whole_mean_as_winning_group', 'reject', correct_report.replace('胜局均值为 33.5', '胜局均值为 33.75')),
        ('whole_mean_as_median', 'reject', correct_report.replace('中位数为 33.5', '中位数为 33.75')),
    ]:
        built = native.request(native.build_inputs(replace(req, report=report)))
        body = json.loads(built.messages[1].content.split('[UNTRUSTED DATA]\n', 1)[1].split('\n[END UNTRUSTED DATA]', 1)[0])
        assert not {'expected_report', 'analyst_rationale'}.intersection(body)
        assert len(body['source_index']['blocks']) == len(inputs.source.blocks)
        controls.append(dict(id=name, expected_report=expected, report=report,
            report_sha256=digest(report), input_ceiling=size(built)))
    return dict(evidence_kind='offline_engineering_and_analyst_controls', provider_calls=0,
        semantic_fix_proven=False, production_admitted=False,
        original_input_sha256=fixture['source_input_sha256'],
        original_failure='native_retained_issue_changed',
        disposition_only_counterexample=dict(protocol_valid=True, numeric_statement_correct=False),
        vision_from_original_rows={k:str(v) for k,v in means.items()},
        original_middle_values=[str(v) for v in values],
        computed_source_id=source, full_report_controls=controls,
        scripted_corrected_review=corrected,
        scripted_five_call_path=[dict(phase=r.metadata['review_phase'],input_ceiling=size(r)) for r in issued],
        full_output_reservation=reserved, total_budget=401920,
        limitations=['Raw model responses remain rejected; replacing a disposition alone leaves the wrong mean.',
                    'The analyst-authored full reports and recovery only prove contracts and capacity.',
                    'Live reassessment must independently support every numeric statement and actual revision.'])


def audit():
    data, requests, original = load_controls()
    shapes = []
    for case, req in zip(data['cases'], requests, strict=True):
        inputs = native.build_inputs(req)
        request = native.request(inputs)
        sent = json.loads(request.messages[1].content.split('[UNTRUSTED DATA]\n', 1)[1].split('\n[END UNTRUSTED DATA]', 1)[0])
        expected = native.request_data(inputs)
        deterministic = expected.pop('deterministic_source_facts')
        assert sent == expected and deterministic in request.messages[2].content
        assert not {'expected_report', 'analyst_rationale', 'targets', 'report_sha256'}.intersection(sent)
        assert size(request) <= 63936
        shapes.append(dict(id=case['id'], report_sha256=digest(req.report), blocks=len(inputs.source.blocks), input_ceiling=size(request)))

    result = json.loads((ROOT / data['origin_result']).read_text(encoding='utf-8'))
    failed = next(c for c in result['cases'] if c['index'] == 3)
    failed_req = replace(original, report=failed['original_report'])
    # The semantic failure is still schema-valid. A new policy cannot relabel
    # an already returned opinion or prove that another model run will improve.
    replies = [r['content'] for r in failed['responses']]
    final, issued = scripted_path(failed_req, replies)
    assert final.verdict.value == 'needs_revision' and len(issued) == 3
    repeated_failure = dict(calls=len(issued), final_verdict=final.verdict.value,
        raw_response_hashes=[digest(r) for r in replies], semantic_approval=False)

    # Explicitly analyst-authored interface witness, including both allowed
    # malformed-output reassessments, revision and final review. No live oracle.
    cases_by_id = {case['id']: (case, req) for case, req in zip(data['cases'], requests, strict=True)}
    negative_case, negative = cases_by_id['explicit_combined_population']
    inputs = native.build_inputs(negative)
    target = negative_case['targets'][0]
    block = next(i for i, (_, text) in enumerate(inputs.source.blocks, 1) if target in text)
    from app.evaluation.golden_semantic_sources import source_catalog
    source = next(i for i, v in source_catalog(inputs, include_role_contrasts=True).items() if v.key == 'derived/computed_evidence')
    issue = dict(block=block, severity='medium', category='unsupported_comparison', source_ids=[source],
        explanation='分析者构造的接口见证，非模型意见。', suggested_correction='按完整来源修正明确的合并组断言。')
    bad = dict(score='70', verdict='needs_revision', issues=[issue], issue_resolutions=[])
    fixed = dict(bad, score=70, issue_resolutions=[dict(previous_id=1, disposition='replaced', final_issue=1,
        source_ids=[source], explanation='仅score类型改变，原问题全部字段值保持。')])
    good = compact(dict(score=95, verdict='pass', issues=[], issue_resolutions=[]))
    revised = cases_by_id['conditional_population'][1].report
    final, issued = scripted_path(negative, [compact(bad), compact(fixed), revised, good+'\nUnstructured ending', good])
    assert final.verdict.value == 'pass' and len(issued) == 5
    assert all(size(r) <= 63936 for r in issued)
    reserved = sum(size(r) + r.max_tokens for r in issued)
    assert reserved <= 401920
    return dict(experiment=native.EXPERIMENT_ID, live_status=native.LIVE_STATUS,
        dataset_sha256=hashlib.sha256(DATASET.read_bytes()).hexdigest(), shapes=shapes,
        provider_calls=0, semantic_approval=False, production_admitted=False,
        original_real_semantic_failure_preserved=repeated_failure,
        scripted_five_call_path=[dict(phase=r.metadata['review_phase'], input_ceiling=size(r)) for r in issued],
        full_output_reservation=reserved, total_budget=401920,
        labels_sent_to_model=False,
        limitations=['Scripted paths prove source delivery and budget, not semantic correction.',
                    'Prior review omission on final recheck is not established as the cause; initial false positive also occurs.',
                    'Complete unchanged reports, explicit population and explicit universal-metric negatives still require real manual-reviewed qualification.'])


def audit_unexpected_findings():
    """Reproduce the real false positive and the development-only stop decision."""
    from app.evaluation.golden_integrated_runtime import _result
    from scripts.run_golden_native_review import score_case
    artifact_path = ROOT / 'data/evaluation/results/golden_native_claim_scope_result_354d752.json'
    artifact = json.loads(artifact_path.read_text(encoding='utf-8'))
    dataset, requests, _ = load_controls()
    runs = {case['index']: case for case in artifact['cases']}
    positive = native.build_inputs(requests[0])
    negative = native.build_inputs(requests[2])
    changed = [i for i, (a, b) in enumerate(zip(positive.source.blocks, negative.source.blocks, strict=True), 1) if a != b]
    assert changed == [6] and runs[1]['original_report'] == requests[0].report
    assert runs[3]['original_report'] == requests[2].report
    first = runs[3]['responses'][0]
    assert digest(first['content']) == first['content_sha256']
    payload, wire, _ = native.validate(first['content'], negative)
    signal = score_case(dataset['cases'][2], _result(payload))
    assert [issue.block for issue in wire.issues] == [6, 4]
    assert signal['matched'] and signal['unexpected_issue_indices'] == [2]
    assert signal['manual_adjudication_required'] and not signal['semantic_approval']
    assert runs[3]['result']['automatic_path_pass'] and not runs[3]['manual_semantic_acceptance']
    downstream = runs[3]['responses'][1:]
    return dict(evidence_kind='offline_replay_of_real_public_findings', provider_calls=0,
        artifact_sha256=hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        changed_report_blocks=changed, unchanged_block_newly_flagged=4,
        actual_first_review_sha256=first['content_sha256'], protocol_valid=True,
        development_signal=signal, initial_semantic_failure_preserved=True,
        historical_calls=runs[3]['result']['completed_calls'],
        guarded_calls_verified_by_integration_tests=1,
        historical_downstream_calls_avoidable=2,
        historical_downstream_tokens_avoidable=sum(r['usage']['input_tokens']+r['usage']['output_tokens'] for r in downstream),
        current_policy_sha256=digest(native.POLICY),
        model_policy_changed=False, semantic_fix_proven=False, production_admitted=False,
        limitations=['An unexpected finding is unadjudicated, not automatically false.',
                    'The guard is for labelled development controls; it does not filter production findings.',
                    'Same-block errors, wrong explanations and unsupported selected sources still require manual review.',
                    'The two avoided calls are an offline counterfactual, not refunded or unspent historical usage.',
                    'The stopped run has no implicit resume or fresh paid retry. A real additional problem requires reviewing control coverage.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--reassessment', action='store_true')
    mode.add_argument('--unexpected-findings', action='store_true')
    args = parser.parse_args()
    result = audit_unexpected_findings() if args.unexpected_findings else audit_reassessment() if args.reassessment else audit()
    if args.output:
        write_new_json(args.output, result)
    print(compact(result))
