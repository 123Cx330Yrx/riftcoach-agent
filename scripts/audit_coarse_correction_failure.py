"""Reproduce the closed failure's source facts and bindings without Provider IO.

Arithmetic verifies the input facts. The full-context wrong-correction decision
remains the recorded primary/independent human judgment, not a keyword gate.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.evaluation.coarse_role_qualification import frozen_cases
from app.evaluation.golden_role_coarse import RoleCoarseReviewWorkflow
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_journal import write_new_json

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT/'data/evaluation/results/golden_coarse_file_handoff_result_v1.json'
EXPORT_SHA = 'd509d516f40739963ed9ac11679fea757ccd83a902e049cefb5e4110c947b69e'


def audit():
    raw = EXPORT.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPORT_SHA:
        raise ValueError('correction_failure_export_changed')
    saved = json.loads(raw)
    files = saved['public_json_contents']
    arm = 'attribution-1/'
    initial = files[arm+'initial.json']
    source = files[arm+'source.json']
    frozen, original = next((f,s) for f,s in frozen_cases()[0] if f['key'] == 'attribution:1')
    inputs = RoleCoarseReviewWorkflow.build_inputs(original)
    if source['input_json'] != inputs.data_json or source['report'] != original.report:
        raise ValueError('correction_failure_source_changed')
    journal = initial['journal']
    if initial['report'] != original.report or journal['input_sha256'] != digest(inputs.data_json):
        raise ValueError('correction_failure_input_changed')
    parsed = journal['parsed_review']
    response = files['transport/attribution-1/review/response-001.json']
    if response['tool_calls'][0]['arguments'] != parsed:
        raise ValueError('correction_failure_public_response_changed')
    payload, wire, rebuilt = RoleCoarseReviewWorkflow.validate_review(journal['raw'], inputs)
    if wire.model_dump(mode='json') != parsed or parsed['score'] != 75:
        raise ValueError('correction_failure_review_changed')
    primary = files[arm+'primary-initial-review.json']
    independent = files[arm+'independent-initial-review.json']
    attribution_responses = [p for p in files if p.startswith('transport/attribution-1/')
                             and '/response-' in p]
    if attribution_responses != ['transport/attribution-1/review/response-001.json'] or arm+'revision.json' in files:
        raise ValueError('correction_failure_unexpected_later_call')
    for decision in (primary, independent):
        if decision['accepted'] or decision['target_and_correction_valid']:
            raise ValueError('correction_failure_rejection_changed')
    rows = json.loads(inputs.data_json)['facts_and_provenance']['facts']
    matches = [rows['facts:recent_match:%02d' % i] for i in range(5)]
    mean = lambda group, metric: sum(Decimal(str(r[metric])) for r in group)/len(group)
    winners = [r for r in matches if r['win']]
    mid_losses = [r for r in matches if not r['win'] and r['role']=='MIDDLE']
    losses = [r for r in matches if not r['win']]
    contrasts = {}
    for metric in ('cs_per_min', 'damage_per_min', 'gold_per_min'):
        win, mid, mixed = (mean(g, metric) for g in (winners, mid_losses, losses))
        contrasts[metric] = {k: str(v) for k,v in dict(win_mean=win,
            mid_loss_mean=mid, mixed_loss_mean=mixed, within_mid_gap=win-mid,
            added_by_support=mid-mixed, mixed_gap=win-mixed).items()}
    return dict(kind='coarse_correction_failure_audit_v1', closed_export_sha256=EXPORT_SHA,
        key=frozen['key'], input_sha256=frozen['input_sha256'],
        source_catalog_sha256=rebuilt['source_catalog_sha256'],
        public_review=parsed, recomputed_contrasts=contrasts,
        first_divergence='issues[0].suggested_correction: expansion to economic attribution',
        primary_judgment=primary['defects'], independent_judgment=independent['defects'],
        semantic_judgment_scope='Preserved independent full-context decisions; arithmetic alone is not a semantic validator.',
        unchanged_original_report=True, revision_sent=False, fresh_review_controls_qualified=False,
        actual_product_task_qualified=False, production_admitted=False, provider_requests=0)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args=parser.parse_args()
    result=audit()
    if args.output:
        write_new_json(args.output,result)
    print(compact(dict(provider_requests=0, key=result['key'],
        recomputed_contrasts=result['recomputed_contrasts'],
        output=str(args.output) if args.output else None)))
