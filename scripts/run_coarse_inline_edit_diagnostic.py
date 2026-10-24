"""One prospective edit-only diagnostic; only the tool schema representation changes."""
import argparse
from copy import deepcopy
from decimal import Decimal
from functools import partial
import hashlib
import json
from pathlib import Path

from scripts import run_coarse_edit_diagnostic as base
from scripts.review_independence_contract import freeze_v2_identity

EXPERIMENT='coarse-inline-edit-diagnostic-20261001'
PRIOR='data/evaluation/results/golden_coarse_edit_diagnostic_result_20261001.json'
PRIOR_SHA='a344b5f00b0e8ed4277a2adba08beea4a257af055ee99cbacb20494ed9f53500'


def prepare(*,root_thread_id,independent_thread_id):
    if base.sha(base.ROOT/PRIOR)!=PRIOR_SHA:
        raise ValueError('coarse_inline_prior_seal')
    prior=json.loads((base.ROOT/PRIOR).read_bytes())
    public=prior['public_json_contents']
    old=public['necessary-edit/request.json']
    row,inputs,accepted,request=base.controls(inline_schema=True)[0]
    encoded=json.loads(base.validate_request(request,transport_id=base.CAPACITY_TRANSPORT_ID))
    expected=deepcopy(old)
    # The closed receipt is an issued request: the shared budget adds this
    # internal marker. It is not a prompt or SDK field and is re-added on send.
    if expected['metadata'].pop('coach_budget_contract',None)!='coach-bounded-review-v2':
        raise ValueError('coarse_inline_prior_budget_binding')
    schema=expected['tools'][0]['input_schema']
    schema['properties']['edits']['items']=schema.pop('$defs')['TextEdit']
    if encoded!=expected or public['necessary-edit/source.json']!=dict(input_json=inputs.data_json,report=inputs.source.report):
        raise ValueError('coarse_inline_not_schema_only')
    plan=base.prepare(root_thread_id=root_thread_id,independent_thread_id=independent_thread_id)
    pricing=base.CONTRACT.pricing_profiles['zhipu','glm-5.3-flash']
    cost=(Decimal(64000)*pricing.input_cost_per_million+Decimal(32768)*pricing.output_cost_per_million)/1_000_000
    cell=dict(plan['cells'][0],request_sha256=hashlib.sha256(base.validate_request(request,
        transport_id=base.CAPACITY_TRANSPORT_ID)).hexdigest(),input_reservation=base.size(request))
    plan.update(experiment=EXPERIMENT,adapter=base.editor.INLINE_VERSION,cells=[cell],
        role_calls={'glm-5.3-flash':1},historical_initial_inputs=1,sequence=['necessary-edit'],
        budget=dict(max_calls=1,max_tokens=96768,max_active_seconds=300,per_request_output=32768,
            per_request_seconds=300,estimated_uncached_cny=str(cost),hard_billing_cap=False),
        prior_result=dict(path=PRIOR,sha256=PRIOR_SHA),
        changed_variable='Exact local TextEdit schema reference expansion only; all other prepared request fields identical after verifying the shared-budget issued marker.',
        acceptance='One valid source-bound necessary edit, correct complete report and preserved content, accepted by genuine dual host review.',
        diagnostic_scope='Single edit only. No fresh reviewer, keep control, reliability claim or qualification.',
        success_decision='Prepare conditional fresh and correct-keep coverage; do not infer a causal or stable improvement from one output.',
        failure_decision='Close after first failure; reject inline representation as a sufficient fix if required fields still fail; no automatic paid variant.')
    for name in (__file__,'app/providers/zhipu.py','scripts/run_golden_inference_development.py',
                 'scripts/run_role_coach_development.py',PRIOR):
        p=Path(name) if Path(name).is_absolute() else base.ROOT/name
        plan['source_sha256'][p.relative_to(base.ROOT).as_posix()]=base.sha(p)
    # Recompute the registered identity binding after altering the diagnostic plan.
    return freeze_v2_identity(plan,root_thread_id=root_thread_id,primary_id=root_thread_id,
                              independent_id=independent_thread_id)


def run(args):
    plan=prepare(root_thread_id=args.root_thread_id,independent_thread_id=args.independent_thread_id)
    if not args.execute:
        if args.output: base.write_new_json(args.output,plan)
        return dict(plan_sha256=base.canonical_sha(plan),preparation=plan,provider_calls=0)
    return base.execute_plan(args,plan,observer=partial(base.observe,inline_single_edit=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root-thread-id',required=True)
    p.add_argument('--independent-thread-id',required=True)
    p.add_argument('--output',type=Path)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--preparation',type=Path)
    p.add_argument('--plan-sha')
    p.add_argument('--ci-run')
    p.add_argument('--env-file',type=Path)
    p.add_argument('--codex-executable',type=Path)
    result=run(p.parse_args())
    print(base.compact(result),flush=True)
    if 'diagnostic_accepted' in result and not result['diagnostic_accepted']:
        raise SystemExit(1)
