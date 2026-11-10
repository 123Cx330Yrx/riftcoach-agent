"""Preview closed history or continue a fixed ledger's untouched controls.

The historical thirteen-case batch is permanently closed. Neither continuation
retries a started case, refunds prior charges, or completes original15 admission.
"""
import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path

from app.evaluation import correction_scope_qualification as qualification
from app.evaluation.golden_review_experiment import digest, compact
from app.evaluation.golden_stream_bridge import REQUEST
from app.evaluation.role_qualification import ROOT
from scripts import run_correction_scope_qualification as prior
from scripts.diagnose_role_context import canonical_sha
from scripts.qualify_role_observations import _seal, inspect_runs
from scripts import role_continuation as continuation

EXPERIMENT = 'correction-scope-unexecuted-v1'
RUN_DIRECTORY = ROOT/'data/runs/role_task_observation'/EXPERIMENT
PREPARATION = ROOT/'data/evaluation/results/golden_correction_scope_unexecuted_preparation_v1.json'
CLOSED_RESULT = ROOT/'data/evaluation/results/golden_correction_scope_unexecuted_result_v1.json'
CLOSED_SHA = '5f22b873a8f2506b46abaaa44fd80a36fb173a5e6df86f2748ba402abaa96309'

POST_HOST_AUDIT_EXPERIMENT = 'correction-scope-post-host-audit-v1'
POST_HOST_AUDIT_RUN_DIRECTORY = ROOT/'data/runs/role_task_observation'/POST_HOST_AUDIT_EXPERIMENT
POST_HOST_AUDIT_PREPARATION = ROOT/'data/evaluation/results/golden_correction_scope_post_host_audit_preparation_v1.json'
POST_HOST_AUDIT_CLOSED_RESULT = ROOT/'data/evaluation/results/golden_correction_scope_post_host_audit_result_v1.json'
# Register the actual immutable export hash when this batch is closed.
POST_HOST_AUDIT_CLOSED_SHA = 'd536cd2a99893c73c3aa022dc613158fdda90574517a732bb1af8ba959a33069'
BUDGET_FIELDS = ('max_calls', 'max_tokens', 'max_seconds')
CAMPAIGN = ROOT/'data/evaluation/manifests/correction_scope_continuation_campaign_v1.json'


def _closed(path, sha, preparation, requests):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError('correction_scope_parent_seal_changed')
    evidence = json.loads(raw)
    saved = evidence['public_json_contents']['plan.json']
    plan = saved['preparation_plan']
    if (plan != json.loads(preparation.read_bytes())
            or canonical_sha(plan) != saved['plan_sha256']
            or evidence['plan_sha256'] != saved['plan_sha256']
            or any(r['key'] not in requests or hashlib.sha256(requests[r['key']]).hexdigest()
                   != r['request_sha256'] for r in plan['cases'])):
        raise ValueError('correction_scope_closed_request_changed')
    return evidence, plan


def _charges(evidence):
    result = evidence['public_json_contents']['result.json']
    fields = {'provider_requests': 'reserved_calls', 'input_tokens': 'input_tokens',
              'output_tokens': 'output_tokens', 'unknown_usage_calls': 'unknown_usage_calls'}
    for exported, accounted in fields.items():
        value = evidence[exported]
        rows = [r['accounting'][accounted] for r in result['cases']]
        if (type(value) is not int or value < 0
                or any(type(v) is not int or v < 0 for v in rows) or sum(rows) != value):
            raise ValueError('correction_scope_parent_accounting_changed')
    elapsed = evidence['actual_batch_elapsed_seconds']
    if (type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0
            or elapsed != result['elapsed_seconds'] or evidence['unknown_usage_calls'] != 0):
        raise ValueError('correction_scope_parent_accounting_changed')
    return dict(max_calls=evidence['provider_requests'],
        max_tokens=evidence['input_tokens'] + evidence['output_tokens'], max_seconds=elapsed)


def _boundary(evidence, plan, *, completed, incomplete, error):
    result = evidence['public_json_contents']['result.json']
    started = completed + incomplete
    if (result.get('error_code') != error or evidence.get('original_error_code') != error
            or result.get('experiment') != plan['experiment'] or result.get('tasks_observed') is not False
            or evidence['completed_keys'] != completed or evidence['incomplete_keys'] != incomplete
            or [r['key'] for r in result['cases']] != started
            or [r['status'] for r in result['cases']] != ['task_observed']*len(completed) + ['failed']
            or evidence['unexecuted_keys'] != [r['key'] for r in plan['cases'][len(started):]]):
        raise ValueError('correction_scope_parent_boundary_changed')


def _parents(current, requests):
    first, original = _closed(prior.CLOSED_RESULT, prior.CLOSED_SHA, prior.PREPARATION, requests)
    second, previous = _closed(CLOSED_RESULT, CLOSED_SHA, PREPARATION, requests)
    keys = [r['key'] for r in current['cases']]
    if (original['identity'] != current['identity'] or original['cases'] != current['cases']
            or original['original15_plan_sha256'] != digest(compact(current))
            or original['original15_keys'] != keys or keys[:3] != ['claim-scope:1', 'claim-scope:4', 'claim-scope:3']):
        raise ValueError('correction_scope_parent_identity_changed')
    _boundary(first, original, completed=['claim-scope:1'], incomplete=['claim-scope:4'],
        error='task_observation_host_deadline')
    _boundary(second, previous, completed=[], incomplete=['claim-scope:3'], error='role_pair_host_rejected')
    first_charge, second_charge = _charges(first), _charges(second)
    budgets = [dict(max_calls=1 if r['expected_initial'] == 'accept' else 3,
        max_tokens=96768 if r['expected_initial'] == 'accept' else 290304,
        max_seconds=300 if r['expected_initial'] == 'accept' else 900) for r in current['cases']]
    if (original['case_budgets'] != budgets
            or {k: original['batch_budget'][k] for k in BUDGET_FIELDS}
            != dict(max_calls=35, max_tokens=3386880, max_seconds=10500)
            or previous['experiment'] != EXPERIMENT
            or previous['identity'] != original['identity'] or previous['cases'] != original['cases'][2:]
            or previous['original15_plan_sha256'] != original['original15_plan_sha256']
            or previous['original15_keys'] != keys or previous['case_budgets'] != budgets[2:]
            or previous['parent_seal_sha256'] != prior.CLOSED_SHA
            or previous['parent_plan_sha256'] != first['plan_sha256']
            or previous['charged_prior_budget'] != first_charge
            or previous['original_batch_budget'] != original['batch_budget']
            or previous['excluded_started_keys'] != keys[:2]
            or any(previous['batch_budget'][k] != sum(b[k] for b in budgets[2:]) for k in BUDGET_FIELDS)
            or second_charge['max_calls'] != 1
            or second['public_json_contents']['result.json']['cases'][0]['stages'] != ['initial']):
        raise ValueError('correction_scope_parent_continuation_changed')
    return first, original, second, previous


def prepare(*, after_host_audit=False):
    current, requests = qualification.prepare_qualification()
    if not after_host_audit:
        _, plan = _closed(CLOSED_RESULT, CLOSED_SHA, PREPARATION, requests)
    elif POST_HOST_AUDIT_CLOSED_SHA is not None or POST_HOST_AUDIT_CLOSED_RESULT.exists():
        _, plan = _closed(POST_HOST_AUDIT_CLOSED_RESULT, POST_HOST_AUDIT_CLOSED_SHA,
            POST_HOST_AUDIT_PREPARATION, requests)
    else:
        first, original, second, _ = _parents(current, requests)
        charges = [_charges(first), _charges(second)]
        charged = {k: sum(c[k] for c in charges) for k in BUDGET_FIELDS[:2]}
        charged['max_seconds'] = float(sum(Decimal(str(c['max_seconds'])) for c in charges))
        budgets = original['case_budgets'][3:]
        totals = {k: sum(b[k] for b in budgets) for k in BUDGET_FIELDS}
        if any(Decimal(str(charged[k])) + Decimal(str(totals[k])) > Decimal(str(original['batch_budget'][k]))
               for k in BUDGET_FIELDS):
            raise ValueError('correction_scope_original_budget_exceeded')
        paths = (*original['source_sha256'], 'scripts/run_correction_scope_unexecuted.py')
        output = totals['max_calls'] * 32768
        estimate = (Decimal(output)*28 + Decimal(totals['max_tokens']-output)*8)/1_000_000
        plan = dict(original, experiment=POST_HOST_AUDIT_EXPERIMENT,
            cases=original['cases'][3:], case_budgets=budgets,
            parent_seal_sha256=prior.CLOSED_SHA, parent_plan_sha256=first['plan_sha256'],
            prior_continuation_seal_sha256=CLOSED_SHA, prior_continuation_plan_sha256=second['plan_sha256'],
            charged_prior_budget=charged, original_batch_budget=original['batch_budget'],
            excluded_started_keys=['claim-scope:1', 'claim-scope:4', 'claim-scope:3'],
            source_sha256={p: digest((ROOT/p).read_text(encoding='utf-8')) for p in paths},
            batch_budget=dict(totals, estimated_uncached_cny=str(estimate), hard_billing_cap=False),
            success_scope='Twelve untouched controls only. Prior strict prefix remains separate; claim-scope:4 and claim-scope:3 stay unqualified. No retry or complete original15/product admission.')
    return plan, {r['key']: requests[r['key']] for r in plan['cases']}


def verify_parent():
    # Only the completed first case is eligible for the unchanged strict gate.
    _, rebuilt, _, accepted, keys, _ = inspect_runs([prior.RUN_DIRECTORY],
        evidence_root=ROOT, closed_exports=[(prior.CLOSED_RESULT, prior.CLOSED_SHA)],
        profile='correction-scope')
    current, _ = qualification.prepare_qualification()
    if rebuilt != current or keys != {'claim-scope:1'} or len(accepted) != 1:
        raise ValueError('correction_scope_parent_prefix_invalid')


def verify_after_host_audit_parents():
    current, requests = qualification.prepare_qualification()
    first, original, second, previous = _parents(current, requests)
    verify_parent()  # Includes the original parent's raw-file seal and full replay.
    _seal(RUN_DIRECTORY.resolve(), CLOSED_RESULT, CLOSED_SHA, ROOT)
    for directory, evidence, plan in ((prior.RUN_DIRECTORY, first, original), (RUN_DIRECTORY, second, previous)):
        for name in ('plan.json', 'result.json'):
            if json.loads((directory/name).read_bytes()) != evidence['public_json_contents'][name]:
                raise ValueError('correction_scope_parent_raw_projection_changed')
        for row in plan['cases']:
            if (directory/(row['key'].replace(':', '-')+'-prepared-request.json')).read_bytes() != requests[row['key']]:
                raise ValueError('correction_scope_parent_raw_request_changed')
    # Prepared requests precede execution; case/transport/handoff artifacts
    # are evidence of starting and may belong only to claim-scope:3.
    case_id = 'claim-scope-3'
    allowed = {'plan.json', 'result.json'} | {r['key'].replace(':', '-')+'-prepared-request.json' for r in previous['cases']}
    allowed |= {'handoff/'+case_id+'-ready.json', 'handoff/'+case_id+'-ready-required.json'}
    prefixes = (case_id+'/', 'transport/'+case_id+'/')
    if any(name not in allowed and not name.startswith(prefixes) for name in second['original_file_sha256']):
        raise ValueError('correction_scope_parent_started_boundary_changed')
    for row in previous['cases'][1:]:
        untouched = row['key'].replace(':', '-')
        if (RUN_DIRECTORY/untouched).exists() or (RUN_DIRECTORY/'transport'/untouched).exists():
            raise ValueError('correction_scope_parent_started_boundary_changed')
    transport = RUN_DIRECTORY/'transport'/case_id
    calls = qualification.read_calls(transport)
    summary = qualification.summarize_role_calls(transport)
    outcome = second['public_json_contents']['result.json']['cases'][0]
    if (len(calls) != 1 or not calls[0]['completed'] or calls[0]['usage'] is None
            or calls[0]['binding']['role'] != 'review'
            or any(outcome['accounting'].get(k) != v for k, v in summary.items())
            or any((RUN_DIRECTORY/case_id/name).exists() for name in ('revision.json', 'final.json', 'case-completed.json'))):
        raise ValueError('correction_scope_parent_raw_accounting_changed')
    prepared = REQUEST.validate_json(requests['claim-scope:3'], strict=True)
    issued = calls[0]['request']
    metadata = dict(issued.metadata)
    metadata.pop('coach_budget_contract', None)
    if replace(issued, timeout_s=prepared.timeout_s, metadata=metadata) != prepared or issued.timeout_s > prepared.timeout_s:
        raise ValueError('correction_scope_parent_actual_request_changed')


def run(args):
    if getattr(args, 'campaign', False):
        if getattr(args, 'after_host_audit', False):
            raise ValueError('role_continuation_campaign_mode_conflict')
        expected_sha = getattr(args, 'campaign_sha', None)
        if args.execute and expected_sha is None:
            raise ValueError('role_continuation_campaign_hash_required')
        campaign, sha = continuation.load_campaign(CAMPAIGN, expected_sha=expected_sha, root=ROOT)
        paths = continuation.require_unstarted_target(campaign, root=ROOT)
        plan, requests = continuation.prepare_campaign(CAMPAIGN, expected_sha=sha, root=ROOT)
        result = prior.execute_prepared(args, plan, requests,
            directory=paths['run_directory'], preparation=paths['preparation'])
        if not args.execute:
            result.update(campaign_sha256=sha, charged_prior_budget=plan['charged_prior_budget'],
                keys=[r['key'] for r in plan['cases']], excluded_started_keys=plan['excluded_started_keys'])
        return result
    if getattr(args, 'campaign_sha', None) is not None:
        raise ValueError('role_continuation_campaign_mode_required')
    after = getattr(args, 'after_host_audit', False)
    if args.execute and not after:
        raise ValueError('correction_scope_unexecuted_closed_or_exists')
    directory = POST_HOST_AUDIT_RUN_DIRECTORY if after else RUN_DIRECTORY
    closed = POST_HOST_AUDIT_CLOSED_RESULT if after else CLOSED_RESULT
    preparation = POST_HOST_AUDIT_PREPARATION if after else PREPARATION
    if args.execute and (POST_HOST_AUDIT_CLOSED_SHA is not None or directory.exists() or closed.exists()):
        raise ValueError('correction_scope_post_host_audit_closed_or_exists')
    plan, requests = prepare(after_host_audit=after)
    if args.execute:
        verify_after_host_audit_parents()
    return prior.execute_prepared(args, plan, requests, directory=directory, preparation=preparation)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', action='store_true', help='Use the canonical closed-parent ledger.')
    parser.add_argument('--campaign-sha', help='Bind execution to the current canonical campaign file.')
    parser.add_argument('--after-host-audit', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file', type=Path)
    args = parser.parse_args()
    result = run(args)
    print(compact(result), flush=True)
    if args.execute and not result['tasks_observed']:
        raise SystemExit(1)
