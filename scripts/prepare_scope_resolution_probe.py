"""Offline feasibility only: reuse existing reassessment, never send a request.

The historical opinion is explicitly an untrusted diagnostic input, not a new
initial review or original-fifteen qualification. Expected labels stay outside
requests. No product registration or automatic issue filtering is implemented.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from app.evaluation import review_bound_qualification as backend
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import validate_request, REVIEW_MODEL_TRANSPORT_ID

ROOT = Path(__file__).resolve().parents[1]
SEAL = 'data/evaluation/results/golden_review_bound_original15_result_20261008.json'
SEAL_SHA = 'c1c3bfdab165fb106522f82008f950283aca18ed27b66af9aaf31d726d3ed525'


def prepare(root=ROOT):
    raw = (root / SEAL).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SEAL_SHA:
        raise ValueError('scope_probe_original_seal_changed')
    public = json.loads(raw)['public_json_contents']
    saved = public['claim-scope-3/source.json']
    old = public['transport/claim-scope-3/review/response-001.json']['tool_calls'][0]['arguments']
    previous_raw = public['claim-scope-3/initial-journal.json']['raw']
    if json.loads(previous_raw) != old or [i['block'] for i in old['issues']] != [4, 6]:
        raise ValueError('scope_probe_initial_opinion_changed')
    source = next(s for f, s in backend.frozen_cases(root=root)[0] if f['key'] == 'claim-scope:3')
    if source.report != saved['report']:
        raise ValueError('scope_probe_report_changed')
    original = '早期死亡在胜败样本间几乎相同'
    explicit = '中单早期死亡在中单胜败样本间几乎相同'
    if source.report.count(original) != 1:
        raise ValueError('scope_probe_counterfactual_anchor')
    cells = []
    for name, synthetic, src in (
        ('actual-mixed', False, source),
        ('explicit-middle-counterfactual', True,
         replace(source, report=source.report.replace(original, explicit, 1))),
    ):
        inputs = backend.Workflow.build_inputs(src)
        if not synthetic and (inputs.data_json != saved['input_json']
                              or digest(inputs.data_json) != saved['input_sha256']):
            raise ValueError('scope_probe_complete_input_changed')
        request = backend.Workflow.make_request(inputs, previous_raw=previous_raw)
        encoded = validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)
        # Verify expressibility, not semantic truth: these are authored fixtures.
        answer = deepcopy(old)
        if synthetic:
            answer['issues'][0]['explanation'] = '原文明确指中单；来源中单早死胜局2.5、败局0.5，不是几乎相同。'
            answer['issue_resolutions'] = [dict(previous_id=i, disposition='replaced',
                final_issue=i, source_ids=[31, 32], explanation='明确中单早死错误与全样本补刀错误仍须修复。')
                for i in (1, 2)]
        else:
            answer.update(score=84, issues=[answer['issues'][1]], issue_resolutions=[
                dict(previous_id=1, disposition='withdrawn', final_issue=None, source_ids=[31, 32],
                     explanation='第14块明确全样本早死2.5/2.67，完整上下文支持原断言。'),
                dict(previous_id=2, disposition='replaced', final_issue=1, source_ids=[31, 32],
                     explanation='全样本补刀8.8/6.45并不持平，保留真实问题。')])
        _, wire, _ = backend.Workflow.validate_review(compact(answer), inputs, previous_raw=previous_raw)
        malformed = deepcopy(answer)
        malformed['issue_resolutions'] = malformed['issue_resolutions'][:1]
        try:
            backend.Workflow.validate_review(compact(malformed), inputs, previous_raw=previous_raw)
        except ValueError:
            pass
        else:
            raise AssertionError('missing_prior_issue_mapping_accepted')
        cells.append(dict(key=name, synthetic_report=synthetic,
            report_sha256=digest(src.report), previous_raw_sha256=digest(previous_raw),
            input_sha256=digest(inputs.data_json), request_sha256=hashlib.sha256(encoded).hexdigest(),
            request=json.loads(encoded),
            host_only_expected_issue_blocks=[4, 6] if synthetic else [6],
            host_only_expected_dispositions=[r.disposition for r in wire.issue_resolutions],
            authored_fixture_validation=True, missing_mapping_rejected=True))
    if cells[0]['request']['messages'][0] != cells[1]['request']['messages'][0]:
        raise AssertionError('counterfactual_changed_policy')
    return dict(kind='scope_resolution_offline_feasibility_v1', source_seal=SEAL,
        source_seal_sha256=SEAL_SHA, mechanism='existing_previous_raw_and_issue_resolutions',
        historical_initial_injection=True, provider_requests=0, execution_enabled=False,
        paid_plan_frozen=False, model_quality_proven=False, production_admitted=False,
        limitations=['Authored fixture validation is not a model response.',
                    'This full reassessment is not a narrow issue-only adjudicator.',
                    'No automatic retry, original15 continuation, or product integration.',
                    'A new paid plan needs execution review, CI and separate authorization.'], cells=cells)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = prepare()
    if args.output:
        write_new_json(args.output, result)
    print(compact(dict(cells=len(result['cells']), provider_requests=0,
        existing_mapping_supported=True, paid_plan_frozen=False)))


if __name__ == '__main__':
    main()
