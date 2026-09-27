"""Read-only planning from the complete, versioned closed-campaign ledger.

Accounting includes every started input, independently of strict qualification.
This module never constructs a Provider, writes receipts, or retries a case.
"""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re

from app.evaluation import correction_scope_qualification as qualification
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import REQUEST
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.role_qualification import ROOT
from app.evaluation.role_task_outcome import VERSION as OBSERVATION_VERSION
from app.harness.steps import EvaluationVerdict, RevisionRequest
from scripts.diagnose_role_context import canonical_sha
from scripts.qualify_role_observations import _seal, inspect_runs

VERSION = 'role-continuation-campaign-v1'
BUDGET_FIELDS = ('max_calls', 'max_tokens', 'max_seconds')
SUBMISSION_MODE = 'independent-drafts-v1'
REQUIRED_SOURCES = (
    'scripts/role_continuation.py', 'scripts/run_correction_scope_unexecuted.py',
    'scripts/role_stage_review_drafts.py', 'scripts/write_role_stage_decision.py',
    'scripts/run_role_task_observation.py', 'scripts/qualify_role_observations.py',
)


def _fail(reason):
    raise ValueError('role_continuation_' + reason)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path):
    return json.loads(path.read_bytes())


def _path(root, name):
    if (not isinstance(name, str) or not name or '\\' in name
            or PurePosixPath(name).is_absolute() or ':' in name
            or '..' in PurePosixPath(name).parts or str(PurePosixPath(name)) != name):
        _fail('path_invalid')
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        _fail('path_invalid')
    return path


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        _fail('hash_invalid')
    return value


def _number(value, *, seconds=False):
    types = (int, float) if seconds else (int,)
    if (type(value) not in types or value < 0
            or type(value) is float and not math.isfinite(value)):
        _fail('accounting_invalid')
    return Decimal(str(value)) if seconds else value


def _budget(value):
    if not isinstance(value, dict) or not all(k in value for k in BUDGET_FIELDS):
        _fail('budget_invalid')
    return {k: _number(value[k], seconds=k == 'max_seconds') for k in BUDGET_FIELDS}


def _plain(values):
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in values.items()}


def registered_parent_seals():
    # These independent, already-registered closed hashes cannot disappear by
    # shortening the campaign JSON and changing its frontier in the same edit.
    # Later parents append to the ledger; no new execution branch is needed.
    from scripts import run_correction_scope_qualification as original
    from scripts import run_correction_scope_unexecuted as historical
    return (original.CLOSED_SHA, historical.CLOSED_SHA, historical.POST_HOST_AUDIT_CLOSED_SHA)


def load_campaign(path, *, expected_sha=None, root=ROOT):
    """The runner supplies its canonical path, never a caller-selected ledger."""
    root, path = Path(root).resolve(), Path(path).resolve()
    if not path.is_relative_to(root):
        _fail('path_invalid')
    sha = _sha(path)
    if expected_sha is not None and _hash(expected_sha) != sha:
        _fail('campaign_changed')
    value = _read(path)
    required = {'version', 'profile', 'identity', 'original15_plan_sha256',
        'original_batch_budget', 'parents', 'last_closed_export_sha256',
        'target', 'host_review_submission_mode', 'source_files'}
    if (not isinstance(value, dict) or set(value) != required
            or value['version'] != VERSION or value['profile'] != 'correction-scope'
            or value['host_review_submission_mode'] != SUBMISSION_MODE):
        _fail('campaign_invalid')
    _hash(value['original15_plan_sha256'])
    _budget(value['original_batch_budget'])
    parents = value['parents']
    if not isinstance(parents, list) or not parents:
        _fail('parents_invalid')
    for parent in parents:
        if (not isinstance(parent, dict) or set(parent) != {'run_directory',
                'closed_export', 'closed_export_sha256', 'preparation'}):
            _fail('parents_invalid')
        _hash(parent['closed_export_sha256'])
        for key in ('run_directory', 'closed_export', 'preparation'):
            _path(root, parent[key])
    for key in ('run_directory', 'closed_export', 'closed_export_sha256', 'preparation'):
        if len({p[key] for p in parents}) != len(parents):
            _fail('duplicate_parent')
    anchors = registered_parent_seals()
    if tuple(p['closed_export_sha256'] for p in parents[:len(anchors)]) != anchors:
        _fail('registered_parent_missing')
    if value['last_closed_export_sha256'] != parents[-1]['closed_export_sha256']:
        _fail('parent_frontier_changed')
    target = value['target']
    if (not isinstance(target, dict) or set(target) != {'experiment', 'run_directory',
            'preparation', 'closed_export', 'state', 'closed_export_sha256'}
            or not isinstance(target['experiment'], str)
            or not re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', target['experiment'])):
        _fail('target_invalid')
    if target['state'] != 'unstarted' or target['closed_export_sha256'] is not None:
        _fail('target_closed_or_exists')
    if target['run_directory'] != 'data/runs/role_task_observation/' + target['experiment']:
        _fail('target_invalid')
    for key in ('run_directory', 'closed_export', 'preparation'):
        path_value = _path(root, target[key])
        if any(path_value == _path(root, p[k]) for p in parents
               for k in ('run_directory', 'closed_export', 'preparation')):
            _fail('target_closed_or_exists')
        if key != 'run_directory' and not target[key].startswith('data/evaluation/results/'):
            _fail('target_invalid')
    if len({target[k] for k in ('run_directory', 'closed_export', 'preparation')}) != 3:
        _fail('target_invalid')
    # One immutable target namespace per complete parent frontier. Renaming a
    # target or its export cannot start a second batch against the same ledger.
    generation = len(parents) - len(anchors) + 1
    expected_target = dict(experiment=f'correction-scope-campaign-v{generation}',
        run_directory=f'data/runs/role_task_observation/correction-scope-campaign-v{generation}',
        preparation=f'data/evaluation/results/golden_correction_scope_campaign_preparation_v{generation}.json',
        closed_export=f'data/evaluation/results/golden_correction_scope_campaign_result_v{generation}.json')
    if any(target[k] != v for k, v in expected_target.items()):
        _fail('target_identity_changed')
    sources = value['source_files']
    if (not isinstance(sources, list) or len(sources) != len(set(sources))
            or not set(REQUIRED_SOURCES).issubset(sources)):
        _fail('source_inventory_invalid')
    for name in sources:
        _path(root, name)
    return value, sha


def target_paths(campaign, *, root=ROOT):
    return {k: _path(Path(root), campaign['target'][k])
            for k in ('run_directory', 'preparation', 'closed_export')}


def require_unstarted_target(campaign, *, root=ROOT):
    paths = target_paths(campaign, root=root)
    if paths['run_directory'].exists() or paths['closed_export'].exists():
        _fail('target_closed_or_exists')
    return paths


def _started(run, files, rows):
    """Prepared requests alone are not execution; all other artifacts count."""
    ids = {r['key'].replace(':', '-'): r['key'] for r in rows}
    allowed = {'plan.json', 'result.json'} | {cid + '-prepared-request.json' for cid in ids}
    started = set()
    for name in files:
        if name in allowed:
            continue
        parts = PurePosixPath(name).parts
        if len(parts) >= 2 and parts[0] in ids:
            started.add(ids[parts[0]])
        elif len(parts) >= 3 and parts[0] == 'transport' and parts[1] in ids:
            started.add(ids[parts[1]])
        elif len(parts) == 2 and parts[0] == 'handoff':
            match = next((key for cid, key in ids.items()
                if parts[1] in (cid + '-ready.json', cid + '-ready-required.json')), None)
            if match is None:
                _fail('started_inventory_changed')
            started.add(match)
        else:
            _fail('started_inventory_changed')
    # Empty directories are not present in a file seal; they still cannot hide
    # an attempted case or enable its replay under another directory.
    for child in run.iterdir():
        if child.is_dir() and child.name not in {*ids, 'transport', 'handoff'}:
            _fail('started_inventory_changed')
    for cid, key in ids.items():
        if (run / cid).exists() or (run / 'transport' / cid).exists():
            started.add(key)
    transport = run / 'transport'
    if transport.exists() and any(not p.is_dir() or p.name not in ids for p in transport.iterdir()):
        _fail('started_inventory_changed')
    handoff = run / 'handoff'
    if handoff.exists() and any(not p.is_file() for p in handoff.iterdir()):
        _fail('started_inventory_changed')
    return started


def _links(plan, parents, charged, excluded, original):
    if not parents:
        return
    if (plan.get('excluded_started_keys') != excluded
            or _budget(plan.get('charged_prior_budget')) != charged
            or plan.get('original_batch_budget') != original['batch_budget']):
        _fail('parent_lineage_changed')
    if 'parent_seals' in plan:
        if plan['parent_seals'] != parents:
            _fail('parent_lineage_changed')
    else:
        # Read the two existing legacy formats without adding a case-specific
        # branch for every later interruption.
        references = [('parent_seal_sha256', 'parent_plan_sha256'),
                      ('prior_continuation_seal_sha256', 'prior_continuation_plan_sha256')]
        actual = [(plan[a], plan[b]) for a, b in references if a in plan and b in plan]
        if actual != [(p['closed_export_sha256'], p['plan_sha256']) for p in parents]:
            _fail('parent_lineage_changed')


def rebuild_stage_prefix(source, calls, backend):
    """Pure request/response reconstruction, with no files or quality grant.

    Return (stage dictionaries, initial/final EvaluationResponse mapping).
    Callers bind those values to their own live or sealed stage artifacts.
    """
    if (not 1 <= len(calls) <= 3 or [c['binding']['role'] for c in calls]
            != ['review', 'revision', 'review'][:len(calls)]):
        _fail('parent_call_inventory_changed')
    if not all(c['completed'] and c['response'] is not None for c in calls):
        _fail('parent_unresolved_call')
    iterator = iter(calls)
    def send(prepared):
        call = next(iterator, None)
        if call is None:
            _fail('parent_call_inventory_changed')
        issued = call['request']
        metadata = dict(issued.metadata)
        annotation = metadata.pop('coach_budget_contract', None)
        if (annotation not in (None, 'coach-bounded-review-v2')
                or replace(issued, timeout_s=prepared.timeout_s, metadata=metadata) != prepared
                or not 0 < issued.timeout_s <= prepared.timeout_s):
            _fail('parent_actual_request_changed')
        return Exchange(issued, call['response'], call['binding']['request_sha256'])
    workflow = backend.Workflow(send)
    initial = workflow.evaluate(source)
    evaluations = {'initial': initial}
    stages = [dict(stage='initial', report=source.report, journal=deepcopy(workflow.last_journal))]
    if len(calls) > 1:
        if initial.verdict is not EvaluationVerdict.NEEDS_REVISION:
            _fail('parent_call_inventory_changed')
        edited = workflow.revise(RevisionRequest(source.player_summary, source.deterministic_report,
            source.knowledge, source.report, initial))
        stages.append(dict(stage='revision', report=edited.report, journal=None))
        if len(calls) > 2:
            evaluations['final'] = workflow.evaluate(replace(source, report=edited.report))
            stages.append(dict(stage='final', report=edited.report, journal=deepcopy(workflow.last_journal)))
    if next(iterator, None) is not None:
        _fail('parent_call_inventory_changed')
    return stages, evaluations


def _replay_prefix(run, row, source, calls, backend, *, outcome=None, error_code=None):
    """Bind every actual completed exchange, without accepting its verdict.

    Human rejection grants no qualification. A final/initial semantic rejection
    before stage exposure is supported only with the executor's exact error,
    outcome and journal and no later call. Other missing stages fail closed.
    """
    arm = run / row['key'].replace(':', '-')
    if not (arm / 'source.json').exists():
        _fail('parent_source_missing')
    expected_source = dict(input_json=backend.Workflow.build_inputs(source).data_json,
        report=source.report, input_sha256=row['input_sha256'], report_sha256=row['report_sha256'])
    if _read(arm / 'source.json') != expected_source:
        _fail('parent_source_changed')
    if not calls:
        return
    stages, evaluations = rebuild_stage_prefix(source, calls, backend)
    exposed = []
    for index, stage in enumerate(stages):
        name = stage['stage']
        path = arm / (name + '.json')
        if stage['journal'] is not None and _read(arm / (name + '-journal.json')) != stage['journal']:
            _fail('parent_journal_changed')
        if not path.exists():
            evaluation = evaluations.get(name)
            expected = (EvaluationVerdict.PASS if name == 'final' or row['expected_initial'] == 'accept'
                        else EvaluationVerdict.NEEDS_REVISION)
            minimum = backend.CONTRACT.descriptor()['minimum_score']
            semantic_failure = evaluation is not None and (evaluation.verdict is not expected
                or evaluation.verdict is EvaluationVerdict.PASS and evaluation.score < minimum)
            required_error = {'initial': 'role_pair_initial_semantics_failed',
                              'final': 'role_pair_final_review_failed'}.get(name)
            if (index != len(stages) - 1 or not semantic_failure or error_code != required_error
                    or outcome is None or outcome.get('status') != 'failed'
                    or outcome.get('stages') != exposed
                    or outcome.get(name + '_verdict') != evaluation.verdict.value
                    or outcome.get(name + '_score') != evaluation.score
                    or len(calls) != {'initial': 1, 'final': 3}.get(name)
                    or any((arm / artifact).exists() for artifact in (
                        name + '-host-required.json', name + '-host.json', 'decision-' + name + '.json',
                        'primary-' + name + '-review.json', 'independent-' + name + '-review.json'))):
                _fail('parent_unexplained_missing_stage')
            continue
        expected = dict(stage, key=row['key'], report_sha256=digest(stage['report']))
        if _read(path) != expected:
            _fail('parent_stage_changed')
        exposed.append(name)
    if (outcome is not None and outcome.get('stages') != exposed
            or {name for name in ('initial', 'revision', 'final') if (arm / (name + '.json')).exists()}
            != set(exposed)):
        _fail('parent_stage_inventory_changed')


def _charge_parent(run, export, plan, rows, budgets, requests, backend, sources):
    result = _read(run / 'result.json')
    if (export['public_json_contents'].get('result.json') != result
            or result.get('experiment') != plan['experiment']
            or export.get('original_error_code') != result.get('error_code')):
        _fail('parent_result_changed')
    recorded = result.get('cases')
    if not isinstance(recorded, list) or len(recorded) > len(rows):
        _fail('parent_boundary_changed')
    keys = [r['key'] for r in rows]
    actual = _started(run, export['original_file_sha256'], rows)
    recorded_keys = [r.get('key') for r in recorded]
    if recorded_keys != keys[:len(recorded)] or set(recorded_keys) != actual:
        _fail('parent_boundary_changed')
    statuses = [r.get('status') for r in recorded]
    completed = [r['key'] for r in recorded if r.get('status') == 'task_observed']
    incomplete = [r['key'] for r in recorded if r.get('status') != 'task_observed']
    if (statuses != ['task_observed'] * len(completed) + ['failed'] * len(incomplete)
            or len(incomplete) > 1 or export.get('completed_keys') != completed
            or export.get('incomplete_keys') != incomplete
            or export.get('unexecuted_keys') != keys[len(recorded):]
            or (result.get('tasks_observed') is True and (incomplete or len(recorded) != len(rows)))):
        _fail('parent_boundary_changed')
    totals = dict(provider_requests=0, input_tokens=0, output_tokens=0, unknown_usage_calls=0)
    for row, budget, outcome in zip(rows, budgets, recorded):
        key = row['key']
        transport = run / 'transport' / key.replace(':', '-')
        calls = backend.read_calls(transport)
        summary = backend.summarize_role_calls(transport)
        if any(outcome.get('accounting', {}).get(k) != v for k, v in summary.items()):
            _fail('parent_accounting_changed')
        for field in ('reserved_calls', 'completed_calls', 'input_tokens', 'output_tokens',
                      'unknown_usage_calls', 'observed_unaccepted_calls'):
            _number(outcome['accounting'][field])
        if summary['unknown_usage_calls']:
            _fail('unknown_usage')
        if (summary['reserved_calls'] > budget['max_calls']
                or summary['input_tokens'] + summary['output_tokens'] > budget['max_tokens']):
            _fail('parent_case_budget_exceeded')
        roles = ['review'] if row['expected_initial'] == 'accept' else ['review', 'revision', 'review']
        if [c['binding']['role'] for c in calls] != roles[:len(calls)]:
            _fail('parent_call_inventory_changed')
        if calls:
            prepared = REQUEST.validate_json(requests[key], strict=True)
            issued = calls[0]['request']
            metadata = dict(issued.metadata)
            annotation = metadata.pop('coach_budget_contract', None)
            if (annotation not in (None, 'coach-bounded-review-v2')
                    or replace(issued, timeout_s=prepared.timeout_s, metadata=metadata) != prepared
                    or not 0 < issued.timeout_s <= prepared.timeout_s):
                _fail('parent_actual_request_changed')
        _replay_prefix(run, row, sources[key], calls, backend,
            outcome=outcome, error_code=result.get('error_code'))
        totals['provider_requests'] += _number(summary['reserved_calls'])
        for field in ('input_tokens', 'output_tokens', 'unknown_usage_calls'):
            totals[field] += _number(summary[field])
    if any(_number(export.get(k)) != v for k, v in totals.items()):
        _fail('parent_accounting_changed')
    elapsed = _number(result.get('elapsed_seconds'), seconds=True)
    if _number(export.get('actual_batch_elapsed_seconds'), seconds=True) != elapsed:
        _fail('parent_accounting_changed')
    charge = dict(max_calls=totals['provider_requests'],
        max_tokens=totals['input_tokens'] + totals['output_tokens'], max_seconds=elapsed)
    if any(charge[k] > _budget(plan['batch_budget'])[k] for k in BUDGET_FIELDS[:2]):
        _fail('parent_batch_budget_exceeded')
    return actual, charge, completed


def prepare_campaign(path, *, expected_sha=None, root=ROOT, backend=qualification):
    """Audit every parent; replay only nonempty completed prefixes strictly."""
    root = Path(root).resolve()
    campaign, campaign_sha = load_campaign(path, expected_sha=expected_sha, root=root)
    require_unstarted_target(campaign, root=root)
    current, requests = backend.prepare_qualification()
    if (campaign['identity'] != current['identity']
            or campaign['original15_plan_sha256'] != digest(compact(current))):
        _fail('candidate_changed')
    all_rows = current['cases']
    sources = {row['key']: source for row, source in backend.frozen_cases()[0]}
    keys = [r['key'] for r in all_rows]
    if (len(keys) != len(set(keys))
            or len({r['input_sha256'] for r in all_rows}) != len(keys)):
        _fail('input_alias_changed')
    original = None
    started, completed = set(), set()
    charged = dict(max_calls=0, max_tokens=0, max_seconds=Decimal(0))
    seals, audits, strict = [], [], []
    for item in campaign['parents']:
        run, export_path = _path(root, item['run_directory']), _path(root, item['closed_export'])
        hashes = _seal(run, export_path, item['closed_export_sha256'], root)
        export, saved = _read(export_path), _read(run / 'plan.json')
        plan = saved['preparation_plan']
        if (export['public_json_contents'].get('plan.json') != saved
                or _read(_path(root, item['preparation'])) != plan
                or saved.get('plan_sha256') != canonical_sha(plan)
                or export.get('plan_sha256') != saved['plan_sha256']
                or plan.get('identity') != current['identity']
                or plan.get('original15_plan_sha256') != campaign['original15_plan_sha256']
                or plan.get('original15_keys') != keys
                or plan.get('observation_version') != OBSERVATION_VERSION
                or plan.get('allow_reassessment') is not False):
            _fail('parent_identity_changed')
        expected_rows = [r for r in all_rows if r['key'] not in started]
        if plan.get('cases') != expected_rows:
            _fail('parent_case_inventory_changed')
        if original is None:
            original = plan
            expected_budgets = [dict(max_calls=1 if r['expected_initial'] == 'accept' else 3,
                max_tokens=96768 if r['expected_initial'] == 'accept' else 290304,
                max_seconds=300 if r['expected_initial'] == 'accept' else 900) for r in all_rows]
            if (plan.get('case_budgets') != expected_budgets
                    or _budget(plan['batch_budget']) != _budget(campaign['original_batch_budget'])):
                _fail('original_budget_changed')
            root_budgets = dict(zip(keys, expected_budgets, strict=True))
        budgets = [root_budgets[r['key']] for r in expected_rows]
        for budget in plan.get('case_budgets', []):
            _budget(budget)
        if (plan.get('case_budgets') != budgets
                or _budget(plan['batch_budget']) != {
                    k: sum(b[k] for b in budgets) for k in BUDGET_FIELDS}):
            _fail('parent_budget_changed')
        _links(plan, seals, charged, [k for k in keys if k in started], original)
        for row in expected_rows:
            raw = (run / (row['key'].replace(':', '-') + '-prepared-request.json')).read_bytes()
            if raw != requests[row['key']] or hashlib.sha256(raw).hexdigest() != row['request_sha256']:
                _fail('parent_prepared_request_changed')
        actual, charge, accepted = _charge_parent(run, export, plan, expected_rows,
            budgets, requests, backend, sources)
        if actual & started:
            _fail('input_restarted')
        started.update(actual)
        completed.update(accepted)
        charged = {k: charged[k] + charge[k] for k in BUDGET_FIELDS}
        descriptor = dict(run_directory=item['run_directory'], closed_export=item['closed_export'],
            closed_export_sha256=item['closed_export_sha256'], plan_sha256=saved['plan_sha256'])
        seals.append(descriptor)
        audits.append((run, export_path, item['closed_export_sha256'], hashes, _plain(charge)))
        if accepted:
            strict.append((run, export_path, item['closed_export_sha256']))
        if plan['experiment'] == campaign['target']['experiment']:
            _fail('target_closed_or_exists')
    if strict:
        _, rebuilt, _, inspected, used, _ = inspect_runs([a[0] for a in strict],
            evidence_root=root, closed_exports=[(a[1], a[2]) for a in strict], profile=campaign['profile'])
        if rebuilt != current or used != completed or len(inspected) != len(completed):
            _fail('strict_prefix_changed')
    rows = [r for r in all_rows if r['key'] not in started]
    if not rows:
        _fail('no_unstarted_inputs')
    budgets = [root_budgets[r['key']] for r in rows]
    total = {k: sum(b[k] for b in budgets) for k in BUDGET_FIELDS}
    if any(charged[k] + total[k] > _budget(original['batch_budget'])[k] for k in BUDGET_FIELDS):
        _fail('original_budget_exceeded')
    paths = list(dict.fromkeys((*original['source_sha256'], *campaign['source_files'],
        Path(path).resolve().relative_to(root).as_posix())))
    estimate = (Decimal(total['max_calls'] * 32768) * 28
        + Decimal(total['max_tokens'] - total['max_calls'] * 32768) * 8) / 1_000_000
    plan = dict(original, experiment=campaign['target']['experiment'], cases=rows, case_budgets=budgets,
        campaign_version=VERSION, campaign_sha256=campaign_sha,
        campaign_file=Path(path).resolve().relative_to(root).as_posix(), parent_seals=seals,
        parent_charges=[dict(seal_sha256=a[2], **a[4]) for a in audits],
        charged_prior_budget=_plain(charged), original_batch_budget=original['batch_budget'],
        excluded_started_keys=[k for k in keys if k in started],
        excluded_started_inputs=[dict(key=r['key'], input_sha256=r['input_sha256'],
            request_sha256=r['request_sha256']) for r in all_rows if r['key'] in started],
        previously_qualified_keys=[k for k in keys if k in completed],
        host_review_submission_mode=campaign['host_review_submission_mode'],
        source_sha256={p: digest(_path(root, p).read_text(encoding='utf-8')) for p in paths},
        batch_budget=dict(total, estimated_uncached_cny=str(estimate), hard_billing_cap=False),
        success_scope='Only untouched original inputs. Started inputs never restart; sealed strict prefixes remain separate. No complete original15, generation or product admission.')
    # Recheck the immutable inputs after replay, before any caller can write a plan.
    if _sha(Path(path)) != campaign_sha:
        _fail('campaign_changed')
    for run, export_path, sha, hashes, _ in audits:
        if _seal(run, export_path, sha, root) != hashes:
            _fail('parent_seal_changed')
    return plan, {r['key']: requests[r['key']] for r in rows}
