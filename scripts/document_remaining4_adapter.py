"""Prepare only the four never-sent cases; closed runs and native gates stay frozen.

No paid execution is implied by preparation. The prior eight-case batch is not
restarted, and its readable but unimportable observed:1 final receives no credit.
"""
import importlib.util
import json
from pathlib import Path
import sys

ADAPTER_SOURCE = 'scripts/document_remaining4_adapter.py'
KEYS = ('observed:2', 'observed:3', 'observed:4', 'observed:5')
SELECTION = 'remaining4'
RUN_ID = 'document-remaining4-time600-20261011'
PREVIOUS_SEAL = 'data/evaluation/results/golden_document_remaining8_time600_result_20261011.json'
PREVIOUS_SHA = '75c8c04dbb6f045de4e24993cae0fa28d192f510fb6726bf68ca99f494ec2bf8'

spec = importlib.util.spec_from_file_location('scripts._remaining4_adapter',
    Path(__file__).with_name('document_remaining8_adapter.py'))
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
runner, evidence = base.runner, base.evidence
old_keys = base.KEYS
old_prior = base.prior
old_source = base.ADAPTER_SOURCE
old_selected = base.selected_controls


def prior(root=runner.ROOT):
    # The earlier full15 proof remains mandatory, including its frozen sources.
    full_plan = old_prior(root)
    path = root / PREVIOUS_SEAL
    if runner._sha(path) != PREVIOUS_SHA:
        raise ValueError('remaining4_prior_seal_changed')
    sealed = json.loads(path.read_bytes())
    result = sealed['execution_result']
    plan = sealed['public_json_contents']['plan.json']['preparation_plan']
    if (plan['sequence'] != list(old_keys) or plan['timing_mode'] != 'time600'
            or result['experiment'] != 'document-remaining8-time600-20261010'
            or result['error_code'] != 'full15_operator_abort'
            or result['provider_calls'] != 6 or result['unexecuted_keys'] != list(KEYS)
            or result['unfinished_keys'] != ['observed:1']
            or result['scan_completed'] is not False or sealed['new_qualification'] != 0
            or [c['key'] for c in result['cases']] != list(old_keys[:4])):
        raise ValueError('remaining4_prior_inventory_changed')
    for source, digest in plan['source_sha256'].items():
        if runner._sha(root / source) != digest:
            raise ValueError('remaining4_frozen_program_changed')
    expected = {row['key']: row for row in full_plan['cells']}
    if plan['cells'] != [expected[key] for key in old_keys]:
        raise ValueError('remaining4_prior_requests_changed')
    return plan


def selected_controls(selection=SELECTION, root=runner.ROOT, *, timing_mode='time600'):
    if selection != SELECTION or timing_mode != 'time600':
        raise ValueError('remaining4_selection_or_timing')
    plan = prior(root)
    rows, variants = old_selected(root=root)
    by_key = {row['key']: row for row in rows}
    by_variant = {variant[0]['key']: variant for variant in variants}
    frozen = {row['key']: row for row in plan['cells']}
    if any(by_key[key] != frozen[key] for key in KEYS):
        raise ValueError('remaining4_frozen_requests_changed')
    return [by_key[key] for key in KEYS], [by_variant[key] for key in KEYS]


def prepare(*, root_thread_id, independent_thread_id, root=runner.ROOT,
            selection=SELECTION, timing_mode='time600'):
    # Reuse the established budget calculation without changing base globals;
    # temporarily changing KEYS would weaken its prior-inventory verification.
    from decimal import Decimal
    plan = base._prepare(root_thread_id=root_thread_id,
        independent_thread_id=independent_thread_id, root=root,
        selection=selection, timing_mode=timing_mode)
    edits = sum(row['expected_initial'] == 'reject' for row in plan['cells'])
    roles = {'glm-5.3': len(KEYS) + edits, 'glm-5.3-flash': edits}
    prices = runner.DOCUMENT_REVIEW_COACH_CONTRACT.pricing_profiles
    cost = sum(count * (Decimal(64000) * prices['zhipu', model].input_cost_per_million
        + Decimal(32768) * prices['zhipu', model].output_cost_per_million) / 1_000_000
        for model, count in roles.items())
    plan['budget'].update(role_calls=roles, max_calls=sum(roles.values()),
        max_tokens=sum(roles.values()) * 96768, max_active_seconds=len(KEYS) * 900,
        estimated_uncached_cny=str(cost))
    plan.update(previous_closed_seal=PREVIOUS_SEAL, previous_closed_seal_sha256=PREVIOUS_SHA,
        previous_run_not_restarted=True, previously_sent_cases_excluded=True,
        previous_unreviewed_cases=[dict(key='claim-scope:2', repeated=False, credit=0),
            dict(key='observed:1', repeated=False, credit=0)],
        success_scope='Four never-sent cases only; no combined original15 qualification.',
        recovery_dispatch_policy='One NEW_TASK per native turn. Recover the same checkpoint with MESSAGE only; never followup_task an active/interrupted turn.',
        source_sha256={**plan['source_sha256'], old_source: runner._sha(root / old_source),
            ADAPTER_SOURCE: runner._sha(root / ADAPTER_SOURCE)})
    return plan


runner.RUN_IDS = {**runner.RUN_IDS, SELECTION: 'document-remaining4-20261011'}
runner.TIMED_RUN_IDS = {**runner.TIMED_RUN_IDS, SELECTION: RUN_ID}
runner.selected_controls, runner.prepare = selected_controls, prepare


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('run', 'handoff'):
        raise SystemExit('usage: document_remaining4_adapter {run|handoff} [arguments]')
    action = sys.argv.pop(1)
    if action == 'run':
        sys.argv.extend(['--selection', SELECTION, '--timing-mode', 'time600'])
        runner.main()
    else:
        evidence.main()


if __name__ == '__main__':
    main()
