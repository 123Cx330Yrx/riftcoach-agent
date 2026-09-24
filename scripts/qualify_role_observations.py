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


def _stage(arm, expected, row, candidate_sha, source_sha, call, transport):
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
    host, primary, independent = map(_json, (host_path, primary_path, independent_path))
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
        files={p.name: _sha(p) for p in (path, host_path, primary_path, independent_path, decision_path)})


def _case(run, row, budget, outcome, source, current, candidate_sha, requests):
    key, case_id = row['key'], row['key'].replace(':', '-')
    arm, transport = run / case_id, run / 'transport' / case_id
    if any(row.get(k) != current[k] for k in IDENTITY_FIELDS):
        _fail('case_identity_mismatch')
    if (run / (case_id + '-prepared-request.json')).read_bytes() != requests[key]:
        _fail('prepared_request_mismatch')
    original = _json(arm / 'source.json')
    expected_source = dict(input_json=qualification.review.native.build_inputs(source).data_json,
        report=source.report, input_sha256=row['input_sha256'], report_sha256=row['report_sha256'])
    if original != expected_source:
        _fail('source_mismatch')
    calls = qualification.read_role_calls(transport)
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
    summary = qualification.summarize_role_calls(transport)
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
    replayed = qualification.replay_case(current, source, calls, include_stage_evidence=True)
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


def qualify(run_directories, *, evidence_root, output_directory, closed_exports):
    """Create new original-gate rows; only all fifteen invoke its validator.

    closed_exports contains (path, independently recorded SHA256) pairs. Both
    runs and output must lie under evidence_root; the output must be new and
    outside every original run. This function never edits a source artifact.
    """
    evidence_root = Path(evidence_root).resolve()
    runs = [_within(evidence_root, p) for p in run_directories]
    output = _within(evidence_root, output_directory)
    if (not runs or len(set(runs)) != len(runs) or len(closed_exports) != len(runs)
            or output.exists() or any(output.is_relative_to(run) for run in runs)):
        _fail('input_or_output_inventory_invalid')
    exports = []
    for p, sha in closed_exports:
        exports.append((Path(p).resolve(), sha))
    current_plan, requests = qualification.prepare_qualification()
    candidate_sha = digest(compact(current_plan['identity']))
    expected = {r['key']: r for r in current_plan['cases']}
    sources = {f['key']: s for f, s in qualification.frozen_cases()[0]}
    prepared, used_keys, seals = [], set(), []
    for run, (export_path, export_sha) in zip(runs, exports, strict=True):
        hashes = _seal(run, export_path, export_sha, evidence_root)
        saved = _json(run / 'plan.json')
        plan, result = saved['preparation_plan'], _json(run / 'result.json')
        if (plan.get('identity') != current_plan['identity']
                or ('original15_plan_sha256' in plan and plan['original15_plan_sha256'] != digest(compact(current_plan)))
                or plan.get('original15_keys') != list(expected)
                or plan.get('observation_version') != VERSION or plan.get('allow_reassessment') is not False
                or saved.get('plan_sha256') != _canonical_sha(plan)
                or not re.fullmatch('[0-9a-f]{40}', str(saved.get('head_sha', '')))
                or not str(saved.get('ci_run', '')).isdigit()):
            _fail('plan_identity_mismatch')
        rows, budgets, outcomes = plan.get('cases'), plan.get('case_budgets'), result.get('cases')
        if (not isinstance(rows, list) or not rows or not isinstance(budgets, list)
                or not isinstance(outcomes, list) or not len(rows) == len(budgets) == len(outcomes)
                or [r.get('key') for r in rows] != [r.get('key') for r in outcomes]
                or result.get('experiment') != plan.get('experiment')
                or 'error_code' in result or 'error_type' in result):
            _fail('closed_case_inventory_mismatch')
        batch = plan.get('batch_budget', {})
        elapsed = _seconds(result.get('elapsed_seconds'), _seconds(batch.get('max_seconds'), 15 * 900))
        total_calls = total_tokens = 0
        total_elapsed = 0.0
        for row, budget, outcome in zip(rows, budgets, outcomes, strict=True):
            key = row.get('key')
            if key not in expected or key in used_keys:
                _fail('duplicate_or_unknown_case')
            used_keys.add(key)
            host, transport, summary, case_elapsed = _case(run, row, budget, outcome, sources[key],
                expected[key], candidate_sha, requests)
            host['closed_export'] = dict(path=export_path.as_posix(), sha256=export_sha,
                run_directory=run.relative_to(evidence_root).as_posix())
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
            original_file_sha256=hashes))
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
    result = dict(qualification_version=qualification.VERSION, identity=current_plan['identity'],
        plan_sha256=digest(compact(current_plan)), cases=rows,
        status='validated_partial', remaining_keys=[key for key in expected if key not in used_keys],
        validated_inputs=len(rows), validated_keys=[r['key'] for r in rows],
        provider_requests=0, review_controls_qualified=False,
        actual_product_task_qualified=False, production_admitted=False, execution_enabled=False)
    if len(rows) == 15:
        result.update(qualification.validate_qualification(result, evidence_root=evidence_root))
        result['status'] = 'qualified_original_review_controls'
    write_new_json(output / 'qualification.json', result)
    write_new_json(output / 'source-seals.json', dict(closed_runs=seals))
    write_new_json(output / 'result.json', {k: v for k, v in result.items() if k not in ('identity', 'cases')})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-directory', action='append', type=Path, required=True)
    parser.add_argument('--closed-export', action='append', nargs=2, metavar=('PATH', 'SHA256'), required=True)
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    result = qualify(args.run_directory, evidence_root=args.evidence_root,
        output_directory=args.output_directory, closed_exports=args.closed_export)
    print(compact({k: v for k, v in result.items() if k not in ('identity', 'cases')}))


if __name__ == '__main__':
    main()
