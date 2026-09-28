"""Write explicit human stage judgments without model calls or inferred consent.

Opted-in runs first retain independent working drafts, then materialize the
same formal review files after an explicit primary submission.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import digest
from app.evaluation.role_task_outcome import stage_identity
from scripts.qualify_role_observations import CHECKS
from scripts.role_host_identity import candidate_sha256
from scripts.run_role_task_observation import Observer, StageDecision
from scripts.role_stage_review_drafts import plan_mode, _review


def build_formal_decision(run, key, stage, notes, other, *, independent_sha256, profile):
    """Build the existing primary/decision formats; never publish a file."""
    from app.evaluation import role_qualification as backend
    observer = Observer
    if profile == 'coarse':
        from app.evaluation import coarse_role_qualification as backend
        from scripts.run_coarse_role_qualification import CoarseObserver as observer
    elif profile == 'correction-scope':
        from app.evaluation import correction_scope_qualification as backend
        from scripts.run_correction_scope_qualification import CorrectionScopeObserver as observer
    elif profile == 'boundary-examples':
        from app.evaluation import boundary_examples_qualification as backend
        from scripts.run_boundary_examples_qualification import BoundaryExamplesObserver as observer
    elif profile != 'role':
        raise ValueError('host_writer_profile')
    run = Path(run).resolve()
    plan = json.loads((run/'plan.json').read_bytes())['preparation_plan']
    row = next(r for r in plan['cases'] if r['key'] == key)
    if stage not in ('initial', 'revision', 'final'):
        raise ValueError('host_writer_stage')
    path = run/key.replace(':', '-')/(stage+'.json')
    if not path.resolve().is_relative_to(run):
        raise ValueError('host_writer_path')
    value = json.loads(path.read_bytes())
    if value['key'] != key or value['stage'] != stage:
        raise ValueError('host_writer_stage_identity')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    accepted, defects, reason = (notes[k] for k in ('accepted', 'defects', 'reason'))
    if other['response_sha256'] != sha(path) or (accepted and other['accepted'] is not True):
        raise ValueError('host_writer_independent_binding_or_rejection')
    needs_report = stage != 'initial' or row['expected_initial'] == 'accept'
    bound = dict(key=key, input_sha256=row['input_sha256'], stage=stage,
        stage_sha256=stage_identity(value), response_sha256=sha(path),
        report_sha256=digest(value['report']), source_file_sha256=sha(path.with_name('source.json')),
        expected_initial=row['expected_initial'])
    # Legacy records need not contain raw transport bindings, but every source
    # and semantic binding required by the consuming gate must be explicit.
    required = set(bound) - {'expected_initial'}
    if any(other.get(k) != bound[k] for k in required):
        raise ValueError('host_writer_independent_binding_or_rejection')
    raw_fields = ('request_sha256', 'provider_response_sha256')
    if any(field in other for field in raw_fields):
        transport = run/'transport'/key.replace(':', '-')
        ordinal = ('initial', 'revision', 'final').index(stage) + 1
        calls = backend.read_calls(transport)
        if len(calls) < ordinal:
            raise ValueError('host_writer_independent_raw_binding')
        call = calls[ordinal-1]['binding']
        bound.update(request_sha256=call['request_sha256'],
            provider_response_sha256=sha(transport/call['raw_directory']/f'response-{ordinal:03d}.json'))
    else:
        bound.update(request_sha256=None, provider_response_sha256=None)
    if value['journal'] is not None:
        bound['final_input_sha256'] = value['journal']['input_sha256']
    _review(other, bound, True)
    if accepted and not needs_report and notes.get('target_and_correction_valid') is not True:
        raise ValueError('host_writer_correction_confirmation_required')
    checks = notes['final_report_checks'] if needs_report else None
    report_sha = digest(value['report'])
    if needs_report and set(checks) != set(CHECKS):
        raise ValueError('host_writer_report_checks')
    report = None if not needs_report else dict(report_sha256=report_sha,
        reviewer='Primary complete-source review', source_review=notes['report_reason'], **checks)
    decision = StageDecision.model_validate(dict(response_sha256=sha(path), accepted=accepted,
        candidate_sha256=candidate_sha256(plan['identity'], backend=backend),
        input_sha256=row['input_sha256'], key=key,
        target_and_correction_valid=notes.get('target_and_correction_valid', False),
        assessment=dict(stage=stage, stage_sha256=stage_identity(value),
            reviewer='Primary complete-source review', source_review=reason,
            accepted=accepted, defects=defects), final_report=report)).model_dump()
    allowed = observer.validate_stage(plan, row, path, decision)
    if accepted and not allowed:
        raise ValueError('host_writer_invalid_acceptance')
    primary = dict(accepted=accepted, defects=defects, stage_sha256=sha(path),
        report_sha256=report_sha, independent_file='independent-'+stage+'-review.json',
        independent_sha256=independent_sha256, reason=reason,
        target_and_correction_valid=notes.get('target_and_correction_valid', False),
        final_report_checks=checks, report_reason=notes.get('report_reason'))
    return primary, decision


def write_decision(run, key, stage, notes, *, profile,
                   expected_response_sha256=None, before_write=lambda: None,
                   independent_draft_sha256=None):
    run = Path(run).resolve()
    if plan_mode(run) is not None:
        from scripts.role_stage_review_drafts import finalize_stage_review
        if independent_draft_sha256 is None:
            raise ValueError('host_writer_explicit_draft_submission_required')
        return finalize_stage_review(run, key, stage, notes, profile=profile,
            independent_draft_sha256=independent_draft_sha256, before_write=before_write)
    def guard():
        if (run/'result.json').exists():
            raise ValueError('host_writer_batch_closed')
        before_write()
    guard()
    if stage not in ('initial', 'revision', 'final'):
        raise ValueError('host_writer_stage')
    path = run/key.replace(':', '-')/(stage+'.json')
    if not path.resolve().is_relative_to(run):
        raise ValueError('host_writer_path')
    if expected_response_sha256 is not None and hashlib.sha256(path.read_bytes()).hexdigest() != expected_response_sha256:
        raise ValueError('host_writer_stage_changed')
    other_path = path.with_name('independent-'+stage+'-review.json')
    other_raw = other_path.read_bytes()
    primary, decision = build_formal_decision(run, key, stage, notes, json.loads(other_raw),
        independent_sha256=hashlib.sha256(other_raw).hexdigest(), profile=profile)
    guard()
    write_new_json(path.with_name('primary-'+stage+'-review.json'), primary)
    guard()
    write_new_json(path.with_name('decision-'+stage+'.json'), decision)
    return decision


def wait_and_write_decision(run, key, stage, notes, *, profile, max_wait_seconds,
                            clock=time.monotonic, sleep=time.sleep):
    """Legacy waiting writer; opted-in runs require an explicit draft SHA."""
    if not 0 < max_wait_seconds <= 900:
        raise ValueError('host_writer_wait_limit')
    run = Path(run).resolve()
    if plan_mode(run) is not None:
        raise ValueError('host_writer_explicit_draft_submission_required')
    if stage not in ('initial', 'revision', 'final'):
        raise ValueError('host_writer_stage')
    path = run/key.replace(':', '-')/(stage+'.json')
    if not path.resolve().is_relative_to(run):
        raise ValueError('host_writer_path')
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if (run/'result.json').exists():
        raise ValueError('host_writer_batch_closed')
    write_new_json(path.with_name('primary-notes-'+stage+'.json'),
        dict(response_sha256=sha, notes=notes))
    deadline = clock() + max_wait_seconds
    other = path.with_name('independent-'+stage+'-review.json')
    def guard():
        if (run/'result.json').exists():
            raise ValueError('host_writer_batch_closed')
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError('host_writer_stage_changed')
        if clock() >= deadline:
            raise ValueError('host_writer_independent_deadline')
    while True:
        guard()
        try:
            json.loads(other.read_bytes())
        except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError):
            sleep(min(.25, max(0, deadline-clock())))
            continue
        guard()
        return write_decision(run, key, stage, notes, profile=profile,
            expected_response_sha256=sha, before_write=guard)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-directory', required=True, type=Path)
    parser.add_argument('--profile', required=True, choices=('role', 'coarse', 'correction-scope', 'boundary-examples'))
    parser.add_argument('--key', required=True)
    parser.add_argument('--stage', required=True, choices=('initial', 'revision', 'final'))
    parser.add_argument('--notes', required=True, type=Path)
    parser.add_argument('--draft-independent', action='store_true')
    parser.add_argument('--supersedes-sha')
    parser.add_argument('--reason')
    parser.add_argument('--confirmed', action='store_true')
    parser.add_argument('--independent-draft-sha')
    parser.add_argument('--wait-seconds', type=float,
        help='Legacy mode only: persist primary notes and wait for independent review.')
    args = parser.parse_args()
    notes = json.loads(args.notes.read_bytes())
    if args.draft_independent:
        if args.wait_seconds is not None or args.independent_draft_sha:
            parser.error('Draft creation and final submission are separate actions.')
        from scripts.role_stage_review_drafts import write_independent_draft
        result = write_independent_draft(args.run_directory, args.key, args.stage, notes,
            profile=args.profile, supersedes_sha256=args.supersedes_sha,
            reason=args.reason, confirmed=args.confirmed)
        print(json.dumps(result))
    else:
        if args.supersedes_sha or args.reason or args.confirmed:
            parser.error('Draft options require --draft-independent.')
        if args.wait_seconds is not None and args.independent_draft_sha:
            parser.error('Explicit draft submission does not use the legacy waiting writer.')
        writer = write_decision if args.wait_seconds is None else wait_and_write_decision
        options = (dict(independent_draft_sha256=args.independent_draft_sha)
            if args.wait_seconds is None else dict(max_wait_seconds=args.wait_seconds))
        result = writer(args.run_directory, args.key, args.stage, notes,
            profile=args.profile, **options)
        print(json.dumps({k: result[k] for k in ('key', 'accepted', 'candidate_sha256')}))
