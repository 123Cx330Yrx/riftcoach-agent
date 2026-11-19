"""Eight unsent cases from the closed time600 run; no restart or old credit.

The frozen runner and evidence helpers are loaded into isolated module objects.
Only inventory, preparation and the two handoff entrypoints are wired locally.
The original modules and every old raw receipt remain unchanged.
"""
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import sys
import time

KEYS = ('claim-scope:5', 'claim-scope:6', 'claim-scope:7',
        'observed:1', 'observed:2', 'observed:3', 'observed:4', 'observed:5')
SELECTION = 'remaining8'
RUN_ID = 'document-remaining8-time600-20261010'
PREVIOUS_SEAL = 'data/evaluation/results/golden_document_full15_time600_result_20261010.json'
PREVIOUS_SHA = '30f8e336d11fa2bd425434d90c37e8ce77cded74cec534a8c958fb914446f576'
ADAPTER_SOURCE = 'scripts/document_remaining8_adapter.py'


def isolated(name):
    spec = importlib.util.spec_from_file_location(
        'scripts._remaining8_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = isolated('run_full15_resumption_candidate')
evidence = isolated('full15_resumption_evidence')
evidence.runner = runner
_selected_controls = runner.selected_controls
_prepare = runner.prepare


def prior(root=runner.ROOT):
    path = root / PREVIOUS_SEAL
    if runner._sha(path) != PREVIOUS_SHA:
        raise ValueError('remaining8_prior_seal_changed')
    value = json.loads(path.read_bytes())
    result = value['execution_result']
    old_plan = value['public_json_contents']['plan.json']['preparation_plan']
    if (result['experiment'] != 'document-full15-resumption-candidate-20261009-time600'
            or result.get('error_code') != 'full15_operator_abort'
            or result['provider_calls'] != 13 or result['scan_completed'] is not False
            or result['unexecuted_keys'] != list(KEYS)
            or result['unfinished_keys'] != ['claim-scope:2']
            or old_plan['timing_mode'] != 'time600'
            or value['new_qualification'] != 0):
        raise ValueError('remaining8_prior_inventory_changed')
    for path, sha in old_plan['source_sha256'].items():
        if runner._sha(root / path) != sha:
            raise ValueError('remaining8_frozen_program_changed')
    return old_plan


def selected_controls(selection=SELECTION, root=runner.ROOT, *, timing_mode='time600'):
    if selection != SELECTION or timing_mode != 'time600':
        raise ValueError('remaining8_selection_or_timing')
    old_plan = prior(root)
    rows, variants = _selected_controls('full15', root, timing_mode='time600')
    by_key, row_by_key = {v[0]['key']: v for v in variants}, {r['key']: r for r in rows}
    old_rows = {r['key']: r for r in old_plan['cells']}
    if len(by_key) != 15 or len(row_by_key) != 15 or len(old_rows) != 15:
        raise ValueError('remaining8_control_inventory')
    if any(row_by_key[k] != old_rows[k] for k in KEYS):
        raise ValueError('remaining8_frozen_requests_changed')
    return [row_by_key[k] for k in KEYS], [by_key[k] for k in KEYS]


def prepare(*, root_thread_id, independent_thread_id, root=runner.ROOT,
            selection=SELECTION, timing_mode='time600'):
    plan = _prepare(root_thread_id=root_thread_id, independent_thread_id=independent_thread_id,
                    root=root, selection=selection, timing_mode=timing_mode)
    edits = sum(r['expected_initial'] == 'reject' for r in plan['cells'])
    roles = {'glm-5.3': len(KEYS) + edits, 'glm-5.3-flash': edits}
    prices = runner.DOCUMENT_REVIEW_COACH_CONTRACT.pricing_profiles
    cost = sum(n * (Decimal(64000) * prices['zhipu', model].input_cost_per_million
        + Decimal(32768) * prices['zhipu', model].output_cost_per_million) / 1_000_000
        for model, n in roles.items())
    plan['budget'].update(role_calls=roles, max_calls=sum(roles.values()),
        max_tokens=sum(roles.values()) * 96768, max_active_seconds=len(KEYS) * 900,
        estimated_uncached_cny=str(cost))
    plan.update(previous_closed_seal=PREVIOUS_SEAL, previous_closed_seal_sha256=PREVIOUS_SHA,
        previous_run_not_restarted=True, previously_sent_cases_excluded=True,
        previous_unreviewed_case=dict(key='claim-scope:2', repeated=False, credit=0),
        success_scope='Eight previously unsent cases only; no combined original15 qualification.',
        source_sha256={**plan['source_sha256'], ADAPTER_SOURCE: runner._sha(root / ADAPTER_SOURCE)})
    return plan


def wait_reviews(path, remaining):
    path = Path(path)
    required = evidence.read(path.parent / 'review-required.json')
    plan = evidence.read(path.parents[2] / 'plan.json')['preparation_plan']
    task_raw = evidence.task(path.parents[2], required['binding']['key'], required['binding']['stage'])
    task_path = path.parent / 'independent-task.json'
    with task_path.open('x', encoding='utf-8') as stream:
        stream.write(task_raw + '\n')
    checkpoint_path = path.parent / 'task-checkpoint.json'
    sha = runner.publish_checkpoint(checkpoint_path, task_path,
        plan['review_principals']['independent']['principal_id'])
    from scripts.host_review_task_checkpoint import dispatch
    with (path.parent / 'dispatch.txt').open('x', encoding='utf-8') as stream:
        stream.write(dispatch(checkpoint_path, sha) + '\n')
    deadline = time.monotonic() + remaining
    while time.monotonic() < deadline:
        abort_path = path.parent / 'operator-abort.json'
        if abort_path.exists():
            runner.validate_abort(evidence.read(abort_path), required['binding'])
            raise ValueError('full15_operator_abort')
        submission_path = path.parent / 'review-submission.json'
        if submission_path.exists():
            runner.read_checkpoint(checkpoint_path, sha)
            value = evidence.read(submission_path)
            evidence.validate_checkpoint(path.parent, value, json.loads(task_raw), plan, required['binding'])
            return value
        time.sleep(0.25)
    raise ValueError('full15_host_deadline')


def write_submission(folder, submission):
    folder = Path(folder)
    directory = folder.parents[1]
    plan = evidence.load_plan(directory)
    bound = evidence.read(folder / 'review-required.json')['binding']
    expected = json.loads(evidence.task(directory, bound['key'], bound['stage'], closed=True))
    evidence.validate_checkpoint(folder, submission, expected, plan, bound)
    runner._write_json(folder / 'host-reviews.json', submission)


runner.RUN_IDS = {**runner.RUN_IDS, SELECTION: 'document-remaining8-20261010'}
runner.TIMED_RUN_IDS = {**runner.TIMED_RUN_IDS, SELECTION: RUN_ID}
runner.selected_controls, runner.prepare = selected_controls, prepare
runner.wait_reviews, runner._write_submission = wait_reviews, write_submission


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('run', 'handoff'):
        raise SystemExit('usage: document_remaining8_adapter {run|handoff} [arguments]')
    action = sys.argv.pop(1)
    if action == 'run':
        # The inherited runner's defaults are legacy/full15; this adapter only
        # permits its exact eight-case time600 selection.
        sys.argv.extend(['--selection', SELECTION, '--timing-mode', 'time600'])
        runner.main()
    else:
        evidence.main()


if __name__ == '__main__':
    main()
