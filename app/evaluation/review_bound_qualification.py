"""Original-set evidence backend for review-bound edits; no product registration."""
from pathlib import Path

from app.evaluation import boundary_examples_qualification as base
from app.evaluation import role_qualification as old
from app.evaluation import review_bound_editor as editor
from app.evaluation.golden_review_experiment import digest

Workflow = editor.ReviewBoundRevisionWorkflow
CONTRACT = base.CONTRACT
CONTRACT_ID = 'review-bound-original15-v1'
VERSION = 'review-bound-role-qualification-v1'
PROFILE = 'review-bound'
SOURCE_FILES = (
    'app/evaluation/review_bound_editor.py',
    'app/evaluation/coarse_revision_editor.py',
    'app/evaluation/source_patch_editor.py',
    'app/evaluation/review_bound_qualification.py',
    'scripts/run_review_bound_qualification.py',
    'scripts/role_continuation.py',
)


def candidate_identity(*, root=old.ROOT):
    identity = base.candidate_identity(root=root)
    # The review model/policy is unchanged, but old whole-report qualifications
    # cannot authorize this different revision protocol or its evidence.
    return dict(identity, workflow_id=CONTRACT_ID, revision_protocol=editor.VERSION,
        revision_source_sha256={name: digest((root/name).read_text(encoding='utf-8'))
                                for name in SOURCE_FILES[:4]})


def prepare_qualification(root=old.ROOT):
    plan, requests = base.prepare_qualification(root=root)
    plan.update(qualification_version=VERSION, identity=candidate_identity(root=root))
    return plan, requests


def replay_case(frozen, source, calls, *, include_stage_evidence=True):
    return old._replay_case(frozen, source, calls, workflow_type=Workflow,
        include_stage_evidence=include_stage_evidence)


def validate_qualification(result, *, evidence_root, root=old.ROOT):
    plan, _ = prepare_qualification(root=root)
    gate = old._validate_qualification(result, evidence_root=evidence_root, root=root,
        plan=plan, read_calls=read_calls,
        replay=lambda *args: replay_case(*args, include_stage_evidence=False))
    from scripts.qualify_role_observations import inspect_runs
    evidence_root = Path(evidence_root).resolve()
    originals, hosts = {}, {}
    for row in result['cases']:
        host = old._read(old._within(evidence_root, row['host_review_file']))
        closed = host.get('closed_export')
        if not isinstance(closed, dict) or not all(closed.get(k) for k in ('run_directory', 'path', 'sha256')):
            raise ValueError('review_bound_qualification_sealed_observation_required')
        run = old._within(evidence_root, closed['run_directory'])
        binding = (closed['path'], closed['sha256'])
        if run in originals and originals[run] != binding:
            raise ValueError('review_bound_qualification_seal_conflict')
        originals[run] = binding
        hosts[row['key']] = (host, old._within(evidence_root, row['transport_directory']))
    _, rebuilt, _, inspected, _, _ = inspect_runs(list(originals), evidence_root=evidence_root,
        closed_exports=list(originals.values()), profile=PROFILE)
    if rebuilt != plan or len(inspected) != 15 or any(
            hosts.get(row['key']) != (host, transport) for row, host, transport in inspected):
        raise ValueError('review_bound_qualification_strict_observation_mismatch')
    return gate


read_calls = base.read_calls
read_role_calls = base.read_role_calls
summarize_role_calls = base.summarize_role_calls
frozen_cases = old.frozen_cases
size = old.size
review = old.review
