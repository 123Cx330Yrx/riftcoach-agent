"""Explicit inheritance of a sealed, accepted two-review overlap boundary.

No credentials, dispatch, authorization issuance, or sender lives here. Old
receipts are copied as identified inherited bytes, never counted as new IO.
"""
from pathlib import Path
import json
import math

from app.evaluation import sol_original15_session as original, sol_review_contract as contract
from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import CandidateSession, SessionBlocked, canonical, digest
from app.evaluation.sol_session_review import SessionReviewGate
from scripts import review_duty_direct_patch as direct
from scripts.host_review_workspace import HostReviewWorkspace
from scripts.reviewer_profile_batch import ExactNativeGate, inventory

VERSION = 'original15-overlap-prefix-recovery-v1'
PREFIX_KINDS = ['model', 'journal', 'host-task', 'host-decision'] * 2


def read(path):
    return json.loads(Path(path).read_bytes())


def parent_inventory(parent):
    from scripts.sol_original15_launch import evidence_inventory
    return evidence_inventory(read(Path(parent)/'plan.json'))


def prefix_files(case):
    files = {}
    for n in range(1, 9):
        for suffix in ('intent', 'result'):
            name = f'session/operations/{n:04d}-{suffix}.json'
            files[name] = digest((case/name).read_bytes())
    files.update({f'session/operations/{p.name}': digest(p.read_bytes())
        for p in (case/'session/operations').glob('attempt-*.json')})
    files.update({f'transport/{p}': sha for p,sha in inventory(case/'transport').items()})
    files.update({f'journal/{duty}-initial.json': digest((case/'journal'/f'{duty}-initial.json').read_bytes())
        for duty in ('facts', 'completion')})
    return files


def prepare_parent(parent, seal_sha, key, events, output):
    """Verify native originals/receipts, then write a zero-send inheritance proof."""
    from scripts.sol_original15_launch import audit_transport
    parent, output = Path(parent).absolute(), Path(output).absolute()
    authors = parent.with_name(parent.name+'-authors')
    if output.exists() or any(output.is_relative_to(p) for p in (parent, authors, contract.ROOT)):
        raise ValueError('patch_recovery_new_external_proof_required')
    if digest((parent/'seal.json').read_bytes()) != seal_sha:
        raise ValueError('patch_recovery_original_seal_required')
    seal, plan = read(parent/'seal.json'), read(parent/'plan.json')
    before, author_files = parent_inventory(parent), inventory(authors)
    if seal['inventory'] != {k:v for k,v in before.items() if k != 'seal.json'}:
        raise ValueError('patch_recovery_parent_inventory_changed')
    case = parent/'cases'/original.case_slug(key)
    binding = read(case/'session/guard.json')['binding']
    roots = seal['original_roots'][key]
    session, gate = original.open_case(parent, key, plan['review_plan'], events,
        plan_sha=seal['plan_sha256'], authorization_sha=binding['authorization_sha256'],
        python=plan['python'], read_only=True,
        guard=roots['guard_sha256'], checkpoint=roots['checkpoint_sha256'])
    with session:
        intents = sorted((session.root/'operations').glob('*-intent.json'))
        if (len(intents) != 9 or [read(p)['kind'] for p in intents[:8]] != PREFIX_KINDS
                or read(intents[8])['request'].get('name') != 'outcome'
                or read(intents[8])['request']['data'].get('outcome') != 'candidate_execution_failed'
                or read(session.root/'terminal.json').get('value', {}).get('reason') != 'case_execution_failed'):
            raise ValueError('patch_recovery_not_exact_overlap_boundary')
        handles = list(gate.handles())
        if ([h['binding']['key'] for h in handles] != ['facts-initial', 'completion-initial']
                or not all(gate.native.replay(h) is True for h in handles)):
            raise ValueError('patch_recovery_both_initials_must_be_accepted')
        transport = audit_transport(session)
        if (transport['completed_calls'] != 2 or transport['failed_calls']
                or transport['http_requests_known'] != 2 or transport['http_requests_unknown']
                or transport['unknown_reserved_tokens'] or transport['receiptless_calls']):
            raise ValueError('patch_recovery_exact_successful_receipts_required')
        _, inputs = original.case_for(key)
        proposals = [direct.bind(inputs, duty, read(case/'journal'/f'{duty}-initial.json')['raw'])
                     for duty in ('facts', 'completion')]
        conflicts = direct.conflict_inventory(inputs, proposals)
        if not conflicts['conflicts']:
            raise ValueError('patch_recovery_original_conflict_required')
        try:
            direct.preview(inputs, proposals)
        except ValueError as error:
            if str(error) != 'direct_patch_overlap_requires_new_joint_design':
                raise
        else:
            raise ValueError('patch_recovery_original_stop_not_reproduced')
        budget = original.last_budget(session)
        checkpoint = read(sorted((session.root/'checkpoints').glob('*.json'))[-1])
        active = checkpoint['active_seconds']
        if (budget['calls'] != 2 or budget['logical'] != {'generation': 0, 'review': 2}
                or budget['tokens'] != transport['known_tokens'] or budget['reserved_tokens']
                or budget['retries'] or budget['failed'] or budget['stopped']
                or not isinstance(active, (int, float)) or not math.isfinite(active) or active < 0):
            raise ValueError('patch_recovery_original_budget_required')
        inherited = prefix_files(case)
    if before != parent_inventory(parent) or author_files != inventory(authors):
        raise ValueError('patch_recovery_originals_changed_during_prepare')
    value = dict(version=VERSION, parent_operator=str(parent), key=key,
        parent_seal_sha256=seal_sha, parent_plan_sha256=seal['plan_sha256'],
        parent_inventory=before, parent_author_inventory=author_files,
        parent_roots=roots, inherited_files=inherited, imported_operations=8,
        accepted_handles=handles, historical_budget=budget, inherited_active_seconds=active,
        historical_batch_accounting=seal['result']['accounting'],
        conflict_inventory_sha256=direct.inventory_sha(conflicts), transport=transport,
        original_native_review_replayed=True, original_overlap_reproduced=True,
        old_failure_retained=True, provider_requests=0, key_reads=0,
        qualified=False, publication_allowed=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_new_json(output, value)
    return dict(proof_file=str(output), proof_sha256=digest(output.read_bytes()), proof=value)


def binding(path, sha):
    path = Path(path).absolute()
    if digest(path.read_bytes()) != sha:
        raise ValueError('patch_recovery_original_proof_required')
    spec = dict(proof_file=str(path), proof_sha256=sha, proof=read(path))
    verify_parent(spec)
    return spec


def verify_parent(spec, *, full=True):
    proof, path = spec['proof'], Path(spec['proof_file'])
    parent = Path(proof['parent_operator'])
    if (digest(path.read_bytes()) != spec['proof_sha256'] or read(path) != proof
            or proof['version'] != VERSION or proof['imported_operations'] != 8
            or proof['original_native_review_replayed'] is not True
            or proof['original_overlap_reproduced'] is not True
            or proof['old_failure_retained'] is not True
            or proof['provider_requests'] != 0 or proof['key_reads'] != 0
            or digest((parent/'seal.json').read_bytes()) != proof['parent_seal_sha256']):
        raise SessionBlocked('patch_recovery_parent_proof_changed')
    case = parent/'cases'/original.case_slug(proof['key'])
    seal = read(parent/'seal.json')
    last = read(case/'session/operations/0005-result.json')['value']['budget']
    active = read(sorted((case/'session/checkpoints').glob('*.json'))[-1])['active_seconds']
    if (proof['inherited_files'] != prefix_files(case)
            or proof['historical_budget'] != last
            or proof['inherited_active_seconds'] != active
            or proof['historical_batch_accounting'] != seal['result']['accounting']
            or proof['parent_roots'] != seal['original_roots'][proof['key']]
            or proof['parent_plan_sha256'] != seal['plan_sha256']
            or proof['accepted_handles'] != [read(case/f'session/operations/{n:04d}-result.json')['value']
                for n in (3, 7)]
            or seal['inventory'] != {k:v for k,v in proof['parent_inventory'].items() if k != 'seal.json'}):
        raise SessionBlocked('patch_recovery_inherited_original_changed')
    if full and (parent_inventory(parent) != proof['parent_inventory']
            or inventory(parent.with_name(parent.name+'-authors')) != proof['parent_author_inventory']):
        raise SessionBlocked('patch_recovery_parent_inventory_changed')


class InheritedNative:
    def __init__(self, current, old, spec):
        self.current, self.old, self.spec = current, old, spec
        self.workspace = current.workspace

    def publish(self, *args, **kwargs):
        return self.current.publish(*args, **kwargs)

    def replay(self, handle):
        # Full parent inventory is checked on segment open and before new IO.
        # Every native replay additionally checks all inherited original bytes
        # and the original gate's current author/event/material validation.
        verify_parent(self.spec, full=False)
        if handle in self.spec['proof']['accepted_handles']:
            return self.old.replay(handle)
        if Path(handle['folder']).is_relative_to(Path(self.spec['proof']['parent_operator'])):
            raise SessionBlocked('patch_recovery_unknown_parent_handle')
        return self.current.replay(handle)

    def submit(self, handle, *args, **kwargs):
        if handle in self.spec['proof']['accepted_handles']:
            raise SessionBlocked('patch_recovery_parent_resubmission_forbidden')
        return self.current.submit(handle, *args, **kwargs)


def open_session(operator, spec, events, *, before_new_model=None, guard=None, checkpoint=None,
                 read_only=False, manual_retry=False, reconcile=False,
                 sink=lambda value: None, control_binding=None, author_root=None, evidence_root=None):
    verify_parent(spec)
    root, proof = Path(operator).absolute(), spec['proof']
    parent = Path(proof['parent_operator'])
    if root.resolve() != root or any(root.is_relative_to(p) or p.is_relative_to(root)
            for p in (parent, parent.with_name(parent.name+'-authors'), contract.ROOT)):
        raise ValueError('patch_recovery_separate_operator_required')
    plan = read(parent/'plan.json')
    def before():
        verify_parent(spec)
        if before_new_model is None:
            raise SessionBlocked('patch_recovery_specific_send_guard_required')
        before_new_model()
    session = CandidateSession(root/'session', binding=dict(version=VERSION, key=proof['key'],
        candidate_contract=contract.VERSION, fixture_only=False,
        input_sha256=original.case_for(proof['key'])[0]['input_sha256'],
        report_sha256=original.case_for(proof['key'])[0]['report_sha256'],
        review_plan_sha256=digest(canonical(plan['review_plan'])),
        inherited_proof_sha256=spec['proof_sha256'], control_binding=control_binding),
        transport_root=root/'transport', journal_root=root/'journal', contract_module=contract,
        guard_sha=guard, checkpoint_sha=checkpoint, read_only=read_only, manual_retry=manual_retry,
        reconcile=reconcile,
        before_new_model=before, checkpoint_sink=sink)
    workspace = HostReviewWorkspace(cwd=contract.ROOT, python=plan['python'],
        answers=author_root or root.with_name(root.name+'-authors'), evidence_roots=[evidence_root or root])
    gate = SessionReviewGate(session, plan=plan['review_plan'], workspace=workspace, event_source=events)
    old_workspace = HostReviewWorkspace(cwd=plan['cwd'], python=plan['python'],
        answers=parent.with_name(parent.name+'-authors'), evidence_roots=[parent])
    gate.native = InheritedNative(gate.native,
        ExactNativeGate(plan['review_plan'], old_workspace, events), spec)
    session.patch_parent = spec
    return session, gate


def import_parent(session):
    session.verify()
    spec, root = session.patch_parent, session.root
    verify_parent(spec)
    proof = spec['proof']
    expected = dict(version=VERSION, proof_sha256=spec['proof_sha256'],
        inherited_files=proof['inherited_files'], historical_budget=proof['historical_budget'],
        historical_batch_accounting=proof['historical_batch_accounting'],
        inherited_active_seconds=proof['inherited_active_seconds'], old_failure_retained=True)
    manifest = root/'parent-import.json'
    if manifest.exists():
        if read(manifest) != expected:
            raise SessionBlocked('patch_recovery_import_changed')
        return
    if session.read_only or list((root/'operations').iterdir()):
        raise SessionBlocked('patch_recovery_empty_owned_session_required')
    case = Path(proof['parent_operator'])/'cases'/original.case_slug(proof['key'])
    for name, sha in proof['inherited_files'].items():
        target = root.parent/name
        raw = (case/name).read_bytes()
        if digest(raw) != sha:
            raise SessionBlocked('patch_recovery_original_changed_during_import')
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
    write_new_json(manifest, expected)
    session.active_before = proof['inherited_active_seconds']
    session._checkpoint('accepted_initial_prefix_inherited')


def run_case(session, router, *, patch_coordination=None):
    import_parent(session)
    result = original.run_case(session, router, patch_coordination=patch_coordination)
    historical = session.patch_parent['proof']
    old, current, batch = historical['historical_budget'], result['accounting'], historical['historical_batch_accounting']
    aggregate = {k: batch[k] + current[k] - old[k] for k in ('calls', 'tokens', 'reserved_tokens', 'retries')}
    if any(current[k] < old[k] for k in aggregate):
        raise SessionBlocked('patch_recovery_cumulative_budget_regressed')
    return dict(**result, recovery_version=VERSION, cumulative_batch_accounting=aggregate,
        inherited_proof_sha256=session.patch_parent['proof_sha256'], original15_qualified=False)
