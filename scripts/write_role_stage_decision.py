"""Write an explicit human stage judgment from saved files; never call a model.

The independent judgment is a separate input, not a source for the primary
judgment. Validate identity before releasing the waiting executor, which then
checks the complete persisted handoff before any further Provider request.
"""
import argparse
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import digest
from app.evaluation.role_task_outcome import stage_identity
from scripts.qualify_role_observations import CHECKS
from scripts.role_host_identity import candidate_sha256
from scripts.run_role_task_observation import Observer, StageDecision


def write_decision(run, key, stage, notes, *, profile):
    from app.evaluation import role_qualification as backend
    observer = Observer
    if profile == 'coarse':
        from app.evaluation import coarse_role_qualification as backend
        from scripts.run_coarse_role_qualification import CoarseObserver as observer
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
    other_path = path.with_name('independent-'+stage+'-review.json')
    other = json.loads(other_path.read_bytes())
    accepted, defects, reason = (notes[k] for k in ('accepted', 'defects', 'reason'))
    if other['response_sha256'] != sha(path) or (accepted and other['accepted'] is not True):
        raise ValueError('host_writer_independent_binding_or_rejection')
    needs_report = stage != 'initial' or row['expected_initial'] == 'accept'
    checks = notes['final_report_checks'] if needs_report else None
    report_sha = digest(value['report'])
    if needs_report and set(checks) != set(CHECKS):
        raise ValueError('host_writer_report_checks')
    report = None if not needs_report else dict(report_sha256=report_sha,
        reviewer='Primary complete-source review', source_review=notes['report_reason'], **checks)
    decision = StageDecision.model_validate(dict(response_sha256=sha(path), accepted=accepted,
        candidate_sha256=candidate_sha256(plan['identity'], backend=backend),
        input_sha256=row['input_sha256'], key=key,
        target_and_correction_valid=notes['target_and_correction_valid'],
        assessment=dict(stage=stage, stage_sha256=stage_identity(value),
            reviewer='Primary complete-source review', source_review=reason,
            accepted=accepted, defects=defects), final_report=report)).model_dump()
    allowed = observer.validate_stage(plan, row, path, decision)
    if accepted and not allowed:
        raise ValueError('host_writer_invalid_acceptance')
    primary = dict(accepted=accepted, defects=defects, stage_sha256=sha(path),
        report_sha256=report_sha, independent_file=other_path.name,
        independent_sha256=sha(other_path), reason=reason,
        target_and_correction_valid=notes['target_and_correction_valid'],
        final_report_checks=checks, report_reason=notes.get('report_reason'))
    write_new_json(path.with_name('primary-'+stage+'-review.json'), primary)
    write_new_json(path.with_name('decision-'+stage+'.json'), decision)
    return decision


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-directory', required=True, type=Path)
    parser.add_argument('--profile', required=True, choices=('role', 'coarse'))
    parser.add_argument('--key', required=True)
    parser.add_argument('--stage', required=True, choices=('initial', 'revision', 'final'))
    parser.add_argument('--notes', required=True, type=Path)
    args = parser.parse_args()
    result = write_decision(args.run_directory, args.key, args.stage,
        json.loads(args.notes.read_bytes()), profile=args.profile)
    print(json.dumps({k: result[k] for k in ('key', 'accepted', 'candidate_sha256')}))
