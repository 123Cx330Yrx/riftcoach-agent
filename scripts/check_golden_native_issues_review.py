"""Unchanged full-report controls and bounded issue-list workflow, fully offline."""
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path

from app.evaluation import golden_native_issues_review as candidate
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_semantic_sources import source_catalog, request_data
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.harness.steps import RevisionRequest
from app.providers.models import ChatResponse, TokenUsage
from scripts.run_golden_native_review import prepare, DATASET


def scripted(inputs, *, block=None):
    root = next(n for n, r in source_catalog(inputs).items() if r.key == 'source/deterministic')
    problems = [] if block is None else [dict(block=block, source_ids=[root], severity='medium',
        category='fact_error', explanation='分析者构造的接口见证；不代表该问题已被模型检出。',
        suggested_correction='按完整来源修正实际问题。')]
    return dict(score=95 if block is None else 70, verdict='pass' if block is None else 'needs_revision',
        issues=problems, issue_resolutions=[])


def audit():
    cases, requests, inputs, values, shapes = [], [], [], [], []
    for n in range(1, 6):
        case, req = prepare(n)
        current = candidate.build_inputs(req)
        block = next(i for i, (_, text) in enumerate(current.source.blocks, 1) if case['target'] in text)
        value = scripted(current, block=block if case['expected_report'] == 'reject' else None)
        candidate.validate(compact(value), current)
        built = candidate.request(current)
        sent = candidate.strict_json(built.messages[1].content.split('[UNTRUSTED DATA]\n', 1)[1].rsplit('\n[END UNTRUSTED DATA]', 1)[0])
        original = request_data(current)
        deterministic = original.pop('deterministic_source_facts')
        assert sent == original and deterministic in built.messages[2].content
        cases.append(case); requests.append(req); inputs.append(current); values.append(value)
        shapes.append(dict(id=case['id'], report_sha256=digest(req.report), blocks=len(current.source.blocks),
            complete_sources_preserved=True, input_ceiling=size(built), scripted_result_chars=len(compact(value))))

    # Normal revision/recheck and both possible corrective calls, same full source.
    def path(replies):
        issued = []
        def send(request):
            issued.append(request)
            response = ChatResponse(content=replies[len(issued)-1], model='glm-5.3-flash', provider='zhipu',
                finish_reason='stop', usage=TokenUsage(input_tokens=10, output_tokens=10))
            return Exchange(request, response, hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
        flow = candidate.NativeBusinessReviewWorkflow(send)
        initial = flow.evaluate(requests[1])
        draft = flow.revise(RevisionRequest(requests[1].player_summary, requests[1].deterministic_report,
            requests[1].knowledge, requests[1].report, initial))
        final = flow.evaluate(replace(requests[1], report=draft.report))
        assert final.verdict.value == 'pass' and flow.revisions == 1
        return [dict(phase=r.metadata['review_phase'], input_ceiling=size(r), output_reservation=r.max_tokens) for r in issued]
    normal = path([compact(values[1]), requests[0].report, compact(values[0])])
    first = deepcopy(values[1]); first['score'] = '70'
    fixed = deepcopy(values[1]); fixed['issue_resolutions'] = [dict(previous_id=1, disposition='retained', final_issue=1,
        source_ids=first['issues'][0]['source_ids'], explanation='脚本原样保留同一问题，不是语义质量证明。')]
    five = path([compact(first), compact(fixed), requests[0].report, compact(values[0])+'\nUnstructured ending', compact(values[0])])

    # Capacity for a prior complete verbose opinion is measured without erasing it.
    fixture = candidate.strict_json(Path('tests/fixtures/native_heading_recheck_failure.json').read_text(encoding='utf-8'))
    replay_inputs = candidate.build_inputs(replace(requests[4], report=fixture['evaluation_request']['report']))
    replay = candidate.request(replay_inputs, previous_raw=fixture['raw'], diagnostics=[{'code':'legacy_bad_envelope'}])
    data = candidate.strict_json(replay.messages[1].content.split('[UNTRUSTED DATA]\n',1)[1].rsplit('\n[END UNTRUSTED DATA]',1)[0])
    assert data['previous_review'] == candidate.previous.provisional_review(fixture['raw'])[0]
    assert data['previous_non_json_suffix'] == '\n``结束。'
    actual = candidate.strict_json(Path('data/evaluation/results/golden_native_review_result_42a5fc0.json').read_text(encoding='utf-8'))
    summary_replay = candidate.request(inputs[0], previous_raw=actual['raw'], diagnostics=[{'code':'extra_forbidden'}])
    summary_data = candidate.strict_json(summary_replay.messages[1].content.split('[UNTRUSTED DATA]\n',1)[1].rsplit('\n[END UNTRUSTED DATA]',1)[0])
    assert summary_data['previous_review'] == candidate.strict_json(actual['raw'])
    tail_artifact = candidate.strict_json(Path('data/evaluation/results/golden_native_review_result_a04df23.json').read_text(encoding='utf-8'))
    assert digest(inputs[0].data_json) == tail_artifact['receipt']['input_sha256']
    tail_replay = candidate.request(inputs[0], previous_raw=tail_artifact['raw'], diagnostics=[{'code':'invalid_json'}])
    tail_data = candidate.strict_json(tail_replay.messages[1].content.split('[UNTRUSTED DATA]\n',1)[1].rsplit('\n[END UNTRUSTED DATA]',1)[0])
    assert tail_data['previous_raw_sha256'] == digest(tail_artifact['raw'])
    assert tail_data['previous_non_json_suffix'] == candidate.previous.provisional_review(tail_artifact['raw'])[1]
    assert '[K1]' in tail_data['previous_non_json_suffix']
    return dict(experiment=candidate.EXPERIMENT_ID, provider_calls=0, semantic_approval=False, production_admitted=False,
        dataset_sha256=hashlib.sha256(DATASET.read_bytes()).hexdigest(), source_controls_and_labels_unchanged=True,
        all_sources_roundtrip=True, shapes=shapes, normal_three_call_path=normal, maximum_five_call_path=five,
        full_output_reservation=sum(r['input_ceiling']+r['output_reservation'] for r in five),
        total_budget=401920, actual_usage_plus_next_reservation_still_authoritative=True,
        legacy_raw_and_semantic_errors_preserved=True, actual_failed_raw_sha256=digest(fixture['raw']),
        actual_failed_response_correction_input_ceiling=size(replay),
        actual_wrong_summary_correction_input_ceiling=size(summary_replay),
        actual_markdown_tail_input_ceiling=size(tail_replay), actual_markdown_tail_preserved=True,
        status_summary_host_generated=True, generated_passed_check_claims=False,
        limitations=['No synthetic result proves issue recall, source relevance or accurate correction.',
            'No generated per-paragraph checklist is treated as proof of semantic coverage.',
            'Historical v2 failures stay failed; removing their output field is not reclassification.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    write_new_json(args.output, result)
    print(compact(result))


if __name__ == '__main__':
    main()
