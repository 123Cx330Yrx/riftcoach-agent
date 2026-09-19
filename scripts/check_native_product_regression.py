"""Reproduce the saved attribution miss and input sizes without Provider I/O.

This measures protocol acceptance, not semantic correctness. Both full reports
keep the original sources; source-binding repairs have separate pipeline tests.
"""
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from decimal import Decimal

from app.evaluation import golden_native_issues_review as native
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from app.evaluation.golden_review_experiment import digest
from app.harness.steps import EvaluationRequest, KnowledgeEvidence, KnowledgeCitation
from app.harness.steps import RevisionRequest
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from app.providers.models import ChatResponse, TokenUsage
from scripts.run_golden_native_review import prepare_attribution, prepare_scope
from scripts.check_golden_native_issues_review import scripted

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / 'data/evaluation/datasets/golden_native_product_attribution_controls_v1.json'
SCOPE_DATASET = ROOT / 'data/evaluation/datasets/golden_native_scope_resolution_controls_v1.json'


def inspect_scope_controls():
    """Full-report scope contrasts; expected meanings remain analyst labels."""
    import hashlib
    data = json.loads(SCOPE_DATASET.read_text(encoding='utf-8'))
    assert hashlib.sha256((ROOT / data['parent_dataset']).read_bytes()).hexdigest() == data['parent_sha256']
    _, original = prepare_attribution(2)
    baseline = native.request_data(native.build_inputs(original))['computed_evidence']
    baseline.pop('source_digest')
    rows = []
    for number, case in enumerate(data['cases'], 1):
        assert digest(case['report']) == case['report_sha256']
        assert case['report'].count(case['target']) == 1
        req = replace(original, report=case['report'])
        loaded_case, loaded_req = prepare_scope(number)
        assert loaded_case == case and loaded_req == req
        inputs = native.build_inputs(req)
        request = native.request(inputs)
        sent = native.strict_json(request.messages[1].content.split('[UNTRUSTED DATA]\n', 1)[1].rsplit('\n[END UNTRUSTED DATA]', 1)[0])
        calculated = sent['computed_evidence']
        calculated.pop('source_digest')
        assert calculated == baseline
        assert [(b['block'], b['text']) for b in sent['source_index']['blocks']] == [
            (i, text) for i, (_, text) in enumerate(inputs.source.blocks, 1)]
        assert 'analyst_rationale' not in sent and 'expected_report' not in sent
        rows.append(dict(id=case['id'], report_sha256=case['report_sha256'],
            expected_report=case['expected_report'], input_ceiling=estimate_runtime_request_input_ceiling(request),
            blocks=len(inputs.source.blocks), complete_report_and_original_sources=True,
            fresh_model_judgment=False))
    return dict(scope='offline_scope_discrimination_controls_not_model_semantics',
        dataset_sha256=hashlib.sha256(SCOPE_DATASET.read_bytes()).hexdigest(), cases=rows,
        same_computed_values_across_all_reports=True, labels_sent_to_model=False,
        new_provider_calls=0, semantic_fix_proven=False)


def inspect():
    import hashlib
    data = json.loads(DATASET.read_text(encoding='utf-8'))
    artifact = ROOT / data['origin_artifact']
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == data['origin_artifact_sha256']
    original = json.loads(artifact.read_text(encoding='utf-8'))
    sources = {}
    for item in data['source_files']:
        path = ROOT / item['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
        sources[path.name] = path.read_text(encoding='utf-8')
    summary = json.loads(sources['player_summary.json'])
    raw = json.loads(sources['retrieval_evidence.json'])
    knowledge = KnowledgeEvidence(context=raw['context'], source_ids=tuple(raw['source_ids']),
        citations=tuple(KnowledgeCitation(**c) for c in raw['citations']), abstained=raw['abstained'])
    rows = summary['matches']
    mean = lambda values: sum(values) / Decimal(len(values))
    wins = mean([Decimal(str(r['damage_per_min'])) for r in rows if r['win']])
    losses = mean([Decimal(str(r['damage_per_min'])) for r in rows if not r['win']])
    mid_losses = mean([Decimal(str(r['damage_per_min'])) for r in rows if not r['win'] and r['role'] == 'MIDDLE'])
    # This independent arithmetic contradicts the original 'mainly support' claim.
    assert wins-mid_losses > (wins-losses)*Decimal('0.95')
    cases = []
    requests, opinions = [], []
    for number, case in enumerate(data['cases'], 1):
        assert digest(case['report']) == case['report_sha256']
        assert case['report'].count(case['target']) == 1
        req = EvaluationRequest(summary, sources['deterministic_report.md'], knowledge,
                                case['report'], data['user_utterance'])
        inputs = native.build_inputs(req)
        loaded_case, loaded_req = prepare_attribution(number)
        assert loaded_case == case and loaded_req == req
        block = next(n for n, (_, text) in enumerate(inputs.source.blocks, 1) if case['target'] in text)
        requests.append(req)
        opinions.append(scripted(inputs, block=block if case['expected_report'] == 'reject' else None))
        ceiling = estimate_runtime_request_input_ceiling(native.request(inputs))
        assert ceiling <= 63936
        # Preserve and reproduce the observed false negative. Never relabel it
        # as a semantic pass just because the response satisfies the wire schema.
        observed = native.validate(original['responses'][-1]['content'], inputs)[0]
        cases.append(dict(id=case['id'], input_ceiling=ceiling, expected_report=case['expected_report'],
                          original_review_wire_verdict=observed.verdict,
                          fresh_model_judgment=False))
    def workflow_path(recovery):
        first, correct = deepcopy(opinions[0]), deepcopy(opinions[1])
        replies = [compact(first), requests[1].report, compact(correct)]
        if recovery:
            malformed = dict(first, score='70')
            first['issue_resolutions'] = [dict(previous_id=1, disposition='retained', final_issue=1,
                source_ids=first['issues'][0]['source_ids'], explanation='离线保留原问题见证。')]
            replies = [compact(malformed), compact(first), requests[1].report,
                       compact(correct)+'\nUnstructured ending', compact(correct)]
        issued = []
        def send(request):
            issued.append(request)
            response = ChatResponse(content=replies[len(issued)-1], model='glm-5.3-flash', provider='zhipu',
                finish_reason='stop', usage=TokenUsage(input_tokens=10, output_tokens=10))
            return Exchange(request, response, hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
        flow = native.NativeBusinessReviewWorkflow(send)
        initial = flow.evaluate(requests[0])
        draft = flow.revise(RevisionRequest(requests[0].player_summary, requests[0].deterministic_report,
            requests[0].knowledge, requests[0].report, initial))
        final = flow.evaluate(replace(requests[0], report=draft.report))
        assert final.verdict.value == 'pass' and flow.revisions == 1
        return [dict(phase=r.metadata['review_phase'], input_ceiling=estimate_runtime_request_input_ceiling(r),
                     output_reservation=r.max_tokens) for r in issued]
    normal, five = workflow_path(False), workflow_path(True)
    computed = native.request_data(native.build_inputs(requests[0]))['computed_evidence']
    return dict(scope='offline_saved_false_negative_and_regression_inputs', cases=cases,
        normal_three_call_path=normal, maximum_five_call_path=five,
        full_output_reservation=sum(r['input_ceiling']+r['output_reservation'] for r in five),
        shared_total_budget=401920, actual_usage_plus_next_reservation_authoritative=True,
        role_contrasts=computed['role_contrasts'],
        damage_gap_all=str(wins-losses), damage_gap_mid=str(wins-mid_losses),
        removed_support_change=str(mid_losses-losses), semantic_fix_proven=False,
        new_provider_calls=0, labels_sent_to_model=False)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope-controls', action='store_true')
    args = parser.parse_args()
    print(json.dumps(inspect_scope_controls() if args.scope_controls else inspect(), ensure_ascii=False, indent=2))
