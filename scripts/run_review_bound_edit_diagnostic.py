"""Prospective three-stage diagnostic, never replaying failed responses as success."""
import argparse
from functools import partial
import hashlib
import json
from pathlib import Path
from decimal import Decimal, ROUND_CEILING

from app.evaluation import review_bound_editor as editor
from scripts import run_coarse_edit_diagnostic as base
from scripts.review_independence_contract import freeze_v2_identity

EXPERIMENT = 'review-bound-edit-diagnostic-20261001'
PRIOR_SEALS = {
    'golden_coarse_edit_diagnostic_result_20261001.json':
        'a344b5f00b0e8ed4277a2adba08beea4a257af055ee99cbacb20494ed9f53500',
    'golden_coarse_inline_edit_result_20261001.json':
        '9d349e66b13c4f89126443a4b6317a5d05b7d1262002499e9dff7a312ecb1911',
}


def prepare(*, root_thread_id, independent_thread_id):
    prior_calls = prior_tokens = 0
    prior_seconds = Decimal(0)
    prior_cost = Decimal(0)
    prior = []
    for name, expected in PRIOR_SEALS.items():
        path = base.ROOT/'data/evaluation/results'/name
        if base.sha(path) != expected:
            raise ValueError('review_bound_prior_seal')
        saved = json.loads(path.read_bytes())
        result = saved['execution_result']
        if (result['diagnostic_accepted'] or result['unknown_reserved_tokens']
                or result['calls'] != 1 or len(result['attempts']) != 1):
            raise ValueError('review_bound_prior_accounting')
        prior_calls += result['calls']
        prior_tokens += result['known_tokens']
        prior_seconds += Decimal(str(result['timing']['active_elapsed_seconds']))
        prior_cost += Decimal(saved['estimated_uncached_known_cny'])
        prior.append(dict(path=path.relative_to(base.ROOT).as_posix(), sha256=expected))
    plan = base.prepare(root_thread_id=root_thread_id, independent_thread_id=independent_thread_id)
    controls = base.controls(revision_adapter=editor)
    cells = []
    for old, (row, inputs, accepted, request) in zip(plan['cells'], controls, strict=True):
        cells.append(dict(old, request_sha256=hashlib.sha256(base.validate_request(
            request, transport_id=base.CAPACITY_TRANSPORT_ID)).hexdigest(), input_reservation=base.size(request)))
        baseline = base.Current.make_request(inputs, accepted=accepted)
        if request.messages[1:] != baseline.messages[1:]:
            raise ValueError('review_bound_full_context_changed')
    plan.update(experiment=EXPERIMENT, adapter=editor.VERSION, cells=cells,
        prior_closed_diagnostics=prior,
        provenance_contract='Host binds review source context; no per-edit source selection or semantic certification.',
        cumulative_with_closed=dict(max_calls=prior_calls+plan['budget']['max_calls'],
            max_tokens=prior_tokens+plan['budget']['max_tokens'],
            max_active_seconds=int((prior_seconds+Decimal(plan['budget']['max_active_seconds'])).to_integral_value(rounding=ROUND_CEILING)),
            estimated_uncached_cny=str(prior_cost+Decimal(plan['budget']['estimated_uncached_cny']))),
        success_decision='Capability evidence only; assess same-contract original15 and natural Agent integration before any product admission.',
        failure_decision='Stop at earliest failure and close; no automatic prompt variant, retry, model switch or qualification.')
    for name in (__file__, editor.__file__, 'app/providers/zhipu.py',
                 'scripts/run_golden_inference_development.py', 'scripts/run_role_coach_development.py'):
        path = Path(name) if Path(name).is_absolute() else base.ROOT/name
        plan['source_sha256'][path.relative_to(base.ROOT).as_posix()] = base.sha(path)
    for row in prior:
        plan['source_sha256'][row['path']] = row['sha256']
    return freeze_v2_identity(plan, root_thread_id=root_thread_id, primary_id=root_thread_id,
                              independent_id=independent_thread_id)


def run(args):
    plan = prepare(root_thread_id=args.root_thread_id, independent_thread_id=args.independent_thread_id)
    if not args.execute:
        if args.output: base.write_new_json(args.output, plan)
        return dict(plan_sha256=base.canonical_sha(plan), preparation=plan, provider_calls=0)
    return base.execute_plan(args, plan, observer=partial(base.observe, revision_adapter=editor))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root-thread-id', required=True)
    parser.add_argument('--independent-thread-id', required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--preparation', type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--codex-executable', type=Path)
    result = run(parser.parse_args())
    print(base.compact(result), flush=True)
    if 'diagnostic_accepted' in result and not result['diagnostic_accepted']:
        raise SystemExit(1)
