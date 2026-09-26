"""Offline strict admission of sealed observations to the original review gate.

No Provider is constructed. A caller supplies each closed export's independently
recorded SHA256. Raw files stay in place; new host records bind accepted primary
and independent source inspections to the unchanged qualification replay. The
observer's task_outcome/reviewer_quality flags never determine acceptance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation import role_qualification as qualification
from app.evaluation.role_task_outcome import ReportAssessment, StageAssessment, VERSION, stage_identity

CHECKS = ('facts_and_sources_correct', 'correct_content_preserved',
          'identity_and_goal_preserved', 'true_errors_fixed')
IDENTITY_FIELDS = ('key', 'suite', 'index', 'id', 'manifest_sha256', 'input_sha256',
                   'report_sha256', 'expected_initial', 'request_sha256', 'first_input_ceiling')
EXPORT_KIND = 'role_task_observation_public_result_v1'


def _fail(code):
    raise ValueError('role_observation_' + code)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path):
    return qualification._read(path)


def _canonical_sha(value):
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             allow_nan=False, separators=(',', ':')))


def _within(root, value):
    return qualification._within(root, value)


def _count(value, cap=None):
    if type(value) is not int or value < 0 or (cap is not None and value > cap):
        _fail('budget_invalid')
    return value


def _seconds(value, cap):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= cap:
        _fail('elapsed_budget_invalid')
    return value


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _accepted(value):
    if value.get('accepted') is not True or value.get('defects') != []:
        _fail('stage_rejected')


def _seal(run, export_path, expected_sha, evidence_root):
    if not isinstance(expected_sha, str) or not re.fullmatch('[0-9a-f]{64}', expected_sha):
        _fail('closed_export_hash_required')
    if _sha(export_path) != expected_sha:
        _fail('closed_export_hash_mismatch')
    export = _json(export_path)
    named = export.get('run_directory')
    if (export.get('kind') != EXPORT_KIND or not isinstance(named, str)
            or run not in {(evidence_root / named).resolve(), (qualification.ROOT / named).resolve()}):
        _fail('closed_export_run_mismatch')
    hashes = export.get('original_file_sha256')
    if not isinstance(hashes, dict) or not hashes:
        _fail('closed_export_inventory_missing')
    actual = {p.relative_to(run).as_posix() for p in run.rglob('*') if p.is_file()}
    if actual != set(hashes):
        _fail('sealed_file_inventory_mismatch')
    for name, sha in hashes.items():
        path = _within(run, name)
        if (path.relative_to(run).as_posix() != name or not isinstance(sha, str)
                or not re.fullmatch('[0-9a-f]{64}', sha) or _sha(path) != sha):
            _fail('sealed_file_hash_mismatch')
    # Public projections can omit private response fields, so their JSON is
    # never substituted for original response bytes or their transport hash.
    return hashes


def _report(value, sha):
    report = ReportAssessment.model_validate(value)
    if report.report_sha256 != sha or not all(getattr(report, key) for key in CHECKS):
        _fail('report_assessment_rejected')
    return report


def _stage(arm, expected, row, candidate_sha, source_sha, call, transport, *, pending_host=None):
    name = expected['stage']
    path = arm / (name + '.json')
    saved = _json(path)
    report_sha = digest(expected['report'])
    if saved != dict(expected, key=row['key'], report_sha256=report_sha):
        _fail('stage_replay_mismatch')
    sha, semantic_sha = _sha(path), stage_identity(expected)
    host_path = arm / (name + '-host.json')
    primary_path = arm / ('primary-' + name + '-review.json')
    independent_path = arm / ('independent-' + name + '-review.json')
    host = _json(host_path) if pending_host is None else pending_host
    primary, independent = map(_json, (primary_path, independent_path))
    for decision in (host, primary, independent):
        if decision is host:
            _accepted(dict(accepted=host.get('accepted'), defects=host.get('assessment', {}).get('defects')))
        else:
            _accepted(decision)
    assessment = StageAssessment.model_validate(host['assessment'])
    if (assessment.accepted is not True or assessment.stage != name or assessment.stage_sha256 != semantic_sha
            or host.get('response_sha256') != sha or host.get('key') != row['key']
            or host.get('input_sha256') != row['input_sha256'] or host.get('candidate_sha256') != candidate_sha
            or primary.get('stage_sha256') != sha or primary.get('report_sha256') != report_sha
            or primary.get('independent_file') != independent_path.name
            or primary.get('independent_sha256') != _sha(independent_path)
            or primary.get('reason') != assessment.source_review
            or not _text(primary.get('reason'))):
        _fail('host_primary_binding_mismatch')
    required = dict(stage=name, stage_sha256=semantic_sha, response_sha256=sha,
        report_sha256=report_sha, input_sha256=row['input_sha256'], key=row['key'], source_file_sha256=source_sha)
    if (any(independent.get(k) != v for k, v in required.items())
            or not _text(independent.get('reviewer')) or not _text(independent.get('source_review'))):
        _fail('independent_binding_mismatch')
    binding = call['binding']
    response_path = transport / binding['raw_directory'] / f"response-{binding['ordinal']:03d}.json"
    optional = dict(provider_response_sha256=_sha(response_path), request_sha256=binding['request_sha256'])
    if expected['journal'] is not None:
        optional['final_input_sha256'] = expected['journal']['input_sha256']
    if any(key in independent and independent[key] != value for key, value in optional.items()):
        _fail('independent_raw_binding_mismatch')
    if name == 'initial' and row['expected_initial'] == 'reject':
        if any(d.get('target_and_correction_valid') is not True for d in (host, primary, independent)):
            _fail('initial_correction_not_accepted')
    else:
        report = _report(host.get('final_report'), report_sha)
        _report(independent.get('final_report'), report_sha)
        if (primary.get('final_report_checks') != {k: True for k in CHECKS}
                or primary.get('report_reason') != report.source_review):
            _fail('primary_report_binding_mismatch')
    # The stdin decision and the executor's saved host copy must be identical.
    decision_path = arm / ('decision-' + name + '.json')
    if _json(decision_path) != host:
        _fail('decision_host_mismatch')
    if name != 'revision' and _json(arm / (name + '-journal.json')) != expected['journal']:
        _fail('journal_replay_mismatch')
    return dict(stage=name, source_review=assessment.source_review,
        independent_source_review=independent['source_review'],
        files={p.name: _sha(p) for p in (path, host_path, primary_path, independent_path, decision_path)
            if p != host_path or pending_host is None})


def _case(run, row, budget, outcome, source, current, candidate_sha, requests, *, backend=qualification):
    key, case_id = row['key'], row['key'].replace(':', '-')
    arm, transport = run / case_id, run / 'transport' / case_id
    fields = IDENTITY_FIELDS + tuple(k for k in ('source_catalog_sha256', 'schema_sha256') if k in current)
    if any(row.get(k) != current[k] for k in fields):
        _fail('case_identity_mismatch')
    if (run / (case_id + '-prepared-request.json')).read_bytes() != requests[key]:
        _fail('prepared_request_mismatch')
    original = _json(arm / 'source.json')
    expected_source = dict(input_json=qualification.review.native.build_inputs(source).data_json,
        report=source.report, input_sha256=row['input_sha256'], report_sha256=row['report_sha256'])
    if original != expected_source:
        _fail('source_mismatch')
    calls = backend.read_role_calls(transport)
    stages = ['initial'] if row['expected_initial'] == 'accept' else ['initial', 'revision', 'final']
    if (len(calls) != len(stages) or not all(c['completed'] and c['usage'] is not None for c in calls)
            or [c['binding']['role'] for c in calls] != (['review'] if len(stages) == 1 else ['review', 'revision', 'review'])):
        _fail('fresh_call_inventory_mismatch')
    if (outcome.get('status') != 'task_observed' or outcome.get('stages') != stages
            or outcome.get('fresh_receipts_verified') is not True
            or outcome.get('continuous_observation_budget_verified') is not True
            or outcome.get('real_generation_included') is not False):
        _fail('continuous_completion_missing')
    if ({p.name for p in arm.glob('*-host.json')} != {name + '-host.json' for name in stages}
            or {p.name for p in arm.glob('primary-*-review.json')} != {'primary-' + name + '-review.json' for name in stages}
            or {p.name for p in arm.glob('independent-*-review.json')} != {'independent-' + name + '-review.json' for name in stages}
            or any(arm.glob('reassessment*'))):
        _fail('stage_inventory_mismatch')
    max_calls = _count(budget.get('max_calls'), 5)
    max_tokens = _count(budget.get('max_tokens'), 401920)
    max_seconds = _seconds(budget.get('max_seconds'), 900)
    elapsed = _seconds(outcome.get('elapsed_seconds'), max_seconds)
    summary = backend.summarize_role_calls(transport)
    if len(calls) > max_calls or summary['input_tokens'] + summary['output_tokens'] > max_tokens:
        _fail('case_budget_exceeded')
    accounting = outcome.get('accounting', {})
    if any(accounting.get(k) != v for k, v in summary.items()):
        _fail('accounting_mismatch')
    # Sealed executor elapsed includes host inspection and accounting. Stream
    # timing alone cannot prove that interval; check both rather than resetting it.
    stream_seconds = 0
    for call in calls:
        b = call['binding']
        terminal = _json(transport / b['raw_directory'] / f"stream-{b['ordinal']:03d}" / 'result.json')
        stream_seconds += _seconds(terminal.get('elapsed_ms'), 300_000) / 1000
    if stream_seconds > elapsed + .01:
        _fail('continuous_elapsed_inconsistent')
    replayed = backend.replay_case(current, source, calls, include_stage_evidence=True)
    if [s['stage'] for s in replayed['stages']] != stages:
        _fail('stage_inventory_mismatch')
    inspections = [_stage(arm, stage, row, candidate_sha, _sha(arm / 'source.json'), call, transport)
        for stage, call in zip(replayed['stages'], calls, strict=True)]
    if outcome.get('final_report_sha256') != replayed['bindings']['final_report_sha256']:
        _fail('final_report_mismatch')
    host = dict(candidate_sha256=candidate_sha, input_sha256=row['input_sha256'],
        initial_request_sha256=calls[0]['binding']['request_sha256'], **replayed['bindings'],
        semantic_acceptance=True, reviewer='Independent strict observation qualification adapter',
        source_review='Every initial, actual edit and final stage was replayed and matched to accepted, defect-free primary and independent full-source inspections.',
        stage_inspections=inspections, source_file_sha256=_sha(arm / 'source.json'),
        sealed_execution_elapsed_seconds=elapsed, receipt_directory=transport.as_posix())
    return host, transport, summary, elapsed


def _completed_prefix(run, plan):
    """Read original durable completions when batch aggregation was lost.

    This does not reconstruct result.json or permit IO to resume. A gap ends
    the accepted prefix; subsequent completions, if any, are contradictory.
    """
    outcomes, batch_elapsed, gap = [], 0.0, False
    for row in plan['cases']:
        arm = run / row['key'].replace(':', '-')
        path = arm / 'case-completed.json'
        if not path.exists():
            gap = True
            continue
        if gap:
            _fail('completion_after_gap')
        receipt = _json(path)
        outcome = receipt.get('outcome', {})
        if (receipt.get('schema_version') != 'role-case-completion-v1'
                or receipt.get('plan_sha256') != _canonical_sha(plan)
                or receipt.get('task_observation_sha256') != _sha(arm / 'task-observation.json')
                or outcome.get('key') != row['key']):
            _fail('completion_receipt_mismatch')
        measured = _seconds(receipt.get('batch_elapsed_seconds'), plan['batch_budget']['max_seconds'])
        case_elapsed = _seconds(outcome.get('elapsed_seconds'), 900)
        if measured < batch_elapsed or measured - batch_elapsed + .01 < case_elapsed:
            _fail('completion_clock_order')
        outcomes.append(outcome)
        batch_elapsed = measured
    if not outcomes:
        _fail('continuous_completion_missing')
    return outcomes, batch_elapsed


def _interrupted_prefix(run, plan, result, *, backend=qualification):
    """Accept only durable completions; charge and retain the failed suffix.

    A failed/missing batch summary does not invalidate earlier completed cases.
    It also cannot hide a started case, refund its calls, or skip over a gap.
    """
    outcomes, completed_elapsed = _completed_prefix(run, plan)
    count = len(outcomes)
    rows, budgets = plan['cases'], plan['case_budgets']
    recorded = [] if result is None else result.get('cases')
    if result is not None:
        if (not isinstance(recorded, list) or not count <= len(recorded) <= count + 1
                or len(recorded) > len(rows) or recorded[:count] != outcomes
                or [r.get('key') for r in recorded] != [r['key'] for r in rows[:len(recorded)]]
                or any(r.get('status') != 'failed' for r in recorded[count:])):
            _fail('failed_batch_prefix_mismatch')
        original_elapsed = _seconds(result.get('elapsed_seconds'), float('inf'))
        if original_elapsed < completed_elapsed:
            _fail('completion_clock_order')
    else:
        original_elapsed = None
    allowed_ids = {r['key'].replace(':', '-') for r in rows}
    transport_root = run / 'transport'
    if any(p.name not in allowed_ids or not p.is_dir() for p in transport_root.iterdir()):
        _fail('unrecorded_transport')
    total_calls = total_tokens = unknown_calls = 0
    tail = []
    for index, (row, budget) in enumerate(zip(rows, budgets, strict=True)):
        case_id = row['key'].replace(':', '-')
        summary = backend.summarize_role_calls(transport_root / case_id)
        started = (run / case_id / 'source.json').exists() or summary['reserved_calls'] > 0
        if started and (index > count or result is not None and index >= len(recorded)):
            _fail('execution_after_incomplete_case')
        if result is not None and index < len(recorded):
            if any(recorded[index].get('accounting', {}).get(k) != v for k, v in summary.items()):
                _fail('accounting_mismatch')
        calls = summary['reserved_calls']
        known_tokens = summary['input_tokens'] + summary['output_tokens']
        if (calls > _count(budget.get('max_calls'), 5)
                or known_tokens > _count(budget.get('max_tokens'), 401920)):
            _fail('case_budget_exceeded')
        # A declared case allowance is not a bound on an already issued
        # unknown call. Charge the actual request's conservative input ceiling
        # and output reservation; a small declaration must not refund it.
        tokens = known_tokens
        if summary['unknown_usage_calls']:
            tokens += sum(qualification.size(call['request']) + call['request'].max_tokens
                for call in backend.read_role_calls(transport_root / case_id) if call['usage'] is None)
        if tokens > budget['max_tokens']:
            _fail('case_budget_exceeded')
        total_calls += calls
        total_tokens += tokens
        unknown_calls += summary['unknown_usage_calls']
        if index >= count and started:
            tail.append(dict(key=row['key'], qualified=False, accounting=summary))
    if (total_calls > _count(plan['batch_budget'].get('max_calls'), 75)
            or total_tokens > _count(plan['batch_budget'].get('max_tokens'), 15 * 401920)):
        _fail('batch_budget_exceeded')
    boundary = dict(batch_result_present=result is not None,
        original_error_code=None if result is None else result.get('error_code'),
        original_error_type=None if result is None else result.get('error_type'),
        accepted_prefix_keys=[r['key'] for r in outcomes], unqualified_started_cases=tail,
        full_batch_reserved_calls=total_calls, full_batch_charged_tokens=total_tokens,
        unknown_usage_calls=unknown_calls, original_elapsed_seconds=original_elapsed)
    # The original result may record a later timeout, including scheduler
    # overrun. Only the already-finished prefix claims to fit the batch clock;
    # preserve the later elapsed/error above without passing the failed tail.
    return outcomes, completed_elapsed, boundary


def inspect_runs(run_directories, *, evidence_root, closed_exports, profile='role'):
    """Read-only full audit, also used when revalidating an issued result."""
    if profile == 'coarse':
        from app.evaluation import coarse_role_qualification as backend
    elif profile == 'role':
        backend = qualification
    else:
        _fail('unknown_qualification_profile')
    evidence_root = Path(evidence_root).resolve()
    runs = [_within(evidence_root, p) for p in run_directories]
    if not runs or len(set(runs)) != len(runs) or len(closed_exports) != len(runs):
        _fail('input_or_output_inventory_invalid')
    exports = []
    for p, sha in closed_exports:
        exports.append((Path(p).resolve(), sha))
    current_plan, requests = backend.prepare_qualification()
    candidate_sha = digest(compact(current_plan['identity']))
    expected = {r['key']: r for r in current_plan['cases']}
    sources = {f['key']: s for f, s in backend.frozen_cases()[0]}
    prepared, used_keys, seals = [], set(), []
    for run, (export_path, export_sha) in zip(runs, exports, strict=True):
        hashes = _seal(run, export_path, export_sha, evidence_root)
        saved = _json(run / 'plan.json')
        plan = saved['preparation_plan']
        if (plan.get('identity') != current_plan['identity']
                or ('original15_plan_sha256' in plan and plan['original15_plan_sha256'] != digest(compact(current_plan)))
                or plan.get('original15_keys') != list(expected)
                or plan.get('observation_version') != VERSION or plan.get('allow_reassessment') is not False
                or saved.get('plan_sha256') != _canonical_sha(plan)
                or not re.fullmatch('[0-9a-f]{40}', str(saved.get('head_sha', '')))
                or not str(saved.get('ci_run', '')).isdigit()):
            _fail('plan_identity_mismatch')
        rows, budgets = plan.get('cases'), plan.get('case_budgets')
        if not isinstance(rows, list) or not rows or not isinstance(budgets, list) or len(rows) != len(budgets):
            _fail('closed_case_inventory_mismatch')
        boundary = None
        result = _json(run / 'result.json') if (run / 'result.json').exists() else None
        if result is not None and result.get('experiment') != plan.get('experiment'):
            _fail('closed_case_inventory_mismatch')
        if result is None or 'error_code' in result or 'error_type' in result:
            outcomes, elapsed, boundary = _interrupted_prefix(run, plan, result, backend=backend)
            rows, budgets = rows[:len(outcomes)], budgets[:len(outcomes)]
            completion_source = ('durable_case_receipts_without_batch_result' if result is None
                else 'durable_case_receipts_before_failed_batch_suffix')
        else:
            outcomes = result.get('cases')
            elapsed = result.get('elapsed_seconds')
            completion_source = 'original_batch_result'
            allowed_ids = {r['key'].replace(':', '-') for r in rows}
            transport_root = run / 'transport'
            if any(p.name not in allowed_ids or not p.is_dir() for p in transport_root.iterdir()):
                _fail('unrecorded_transport')
        if (not isinstance(rows, list) or not rows or not isinstance(budgets, list)
                or not isinstance(outcomes, list) or not len(rows) == len(budgets) == len(outcomes)
                or [r.get('key') for r in rows] != [r.get('key') for r in outcomes]):
            _fail('closed_case_inventory_mismatch')
        batch = plan.get('batch_budget', {})
        elapsed = _seconds(elapsed, _seconds(batch.get('max_seconds'), 15 * 900))
        total_calls = total_tokens = 0
        total_elapsed = 0.0
        for row, budget, outcome in zip(rows, budgets, outcomes, strict=True):
            key = row.get('key')
            if key not in expected or key in used_keys:
                _fail('duplicate_or_unknown_case')
            used_keys.add(key)
            host, transport, summary, case_elapsed = _case(run, row, budget, outcome, sources[key],
                expected[key], candidate_sha, requests, backend=backend)
            host['closed_export'] = dict(path=export_path.as_posix(), sha256=export_sha,
                run_directory=run.relative_to(evidence_root).as_posix())
            host['completion_source'] = completion_source
            prepared.append((expected[key], host, transport))
            total_calls += summary['reserved_calls']
            total_tokens += summary['input_tokens'] + summary['output_tokens']
            total_elapsed += case_elapsed
        if (total_calls > _count(batch.get('max_calls'), 75)
                or total_tokens > _count(batch.get('max_tokens'), 15 * 401920)
                or total_elapsed > elapsed + .01):
            _fail('batch_budget_exceeded')
        seals.append(dict(run_directory=run.relative_to(evidence_root).as_posix(),
            closed_export=export_path.as_posix(), closed_export_sha256=export_sha,
            original_file_sha256=hashes, interruption_boundary=boundary))
    return backend, current_plan, expected, prepared, used_keys, seals


def qualify(run_directories, *, evidence_root, output_directory, closed_exports, profile='role'):
    """Create-only qualification after complete read-only inspection."""
    evidence_root = Path(evidence_root).resolve()
    output = _within(evidence_root, output_directory)
    runs = [_within(evidence_root, p) for p in run_directories]
    if output.exists() or any(output.is_relative_to(run) for run in runs):
        _fail('input_or_output_inventory_invalid')
    backend, current_plan, expected, prepared, used_keys, seals = inspect_runs(runs,
        evidence_root=evidence_root, closed_exports=closed_exports, profile=profile)
    # All evidence is checked before the first write. Create-only output never
    # edits a closed run, even if the final original-gate validator rejects it.
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for row, host, transport in prepared:
        host_path = output / (row['key'].replace(':', '-') + '-host-review.json')
        write_new_json(host_path, host)
        rows.append(dict(row, status='host_accepted',
            transport_directory=transport.relative_to(evidence_root).as_posix(),
            host_review_file=host_path.relative_to(evidence_root).as_posix(), host_review_sha256=_sha(host_path)))
    rows.sort(key=lambda r: list(expected).index(r['key']))
    result = dict(qualification_version=backend.VERSION, identity=current_plan['identity'],
        plan_sha256=digest(compact(current_plan)), cases=rows,
        status='validated_partial', remaining_keys=[key for key in expected if key not in used_keys],
        validated_inputs=len(rows), validated_keys=[r['key'] for r in rows],
        provider_requests=0, review_controls_qualified=False,
        actual_product_task_qualified=False, production_admitted=False, execution_enabled=False)
    if len(rows) == 15:
        result.update(backend.validate_qualification(result, evidence_root=evidence_root))
        result['status'] = 'qualified_original_review_controls'
    write_new_json(output / 'qualification.json', result)
    write_new_json(output / 'source-seals.json', dict(closed_runs=seals))
    write_new_json(output / 'result.json', {k: v for k, v in result.items() if k not in ('identity', 'cases')})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-directory', action='append', type=Path, required=True)
    parser.add_argument('--profile', choices=('role', 'coarse'), default='role')
    parser.add_argument('--closed-export', action='append', nargs=2, metavar=('PATH', 'SHA256'), required=True)
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    result = qualify(args.run_directory, evidence_root=args.evidence_root,
        output_directory=args.output_directory, closed_exports=args.closed_export, profile=args.profile)
    print(compact({k: v for k, v in result.items() if k not in ('identity', 'cases')}))


if __name__ == '__main__':
    main()
