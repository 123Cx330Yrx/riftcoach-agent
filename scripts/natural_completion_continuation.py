"""Explicit new diagnostic after a sealed completion semantic rejection.

Only the independently accepted prefix is inherited. This does not reopen the
parent, accept its rejected opinion, repair model quality or issue a grant.
"""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import shutil

from app.evaluation import sol_review_contract as contract
from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import SessionBlocked, canonical, digest
from scripts.prepare_natural_completion_frontier import read, prefix_state
from scripts.reviewer_profile_batch import ExactNativeGate, inventory
from scripts.host_review_workspace import HostReviewWorkspace

VERSION = 'natural-accepted-facts-continuation-v1'


def verify_parent(spec):
    path = Path(spec['proof_file'])
    if digest(path.read_bytes()) != spec['proof_sha256']:
        raise SessionBlocked('launch_completion_original_proof_changed')
    proof = read(path)
    root = Path(proof['parent_operator'])
    seal = read(root/'seal.json')
    state = prefix_state(root)
    last = sorted((root/'execution/session/checkpoints').glob('*.json'))[-1]
    if (proof.get('version') != 'natural-completion-frontier-audit-v1'
            or proof.get('original_native_review_replayed') is not True
            or proof.get('original_rejected_completion_retained') is not True
            or proof.get('provider_requests') != 0 or proof.get('key_reads') != 0
            or inventory(root) != proof['parent_inventory']
            or inventory(root.with_name(root.name+'-authors')) != proof['parent_author_inventory']
            or digest((root/'seal.json').read_bytes()) != proof['parent_seal_sha256']
            or seal['result'] != proof['original_strict_replay']
            or seal['result'].get('strict_replay') is not True
            or seal['result'].get('reason') != 'semantic_rejected'
            or state != proof['state']
            or any(proof[k] != state[k] for k in ('historical_budget', 'derived_budget',
                                                 'accepted_handle', 'frontier'))
            or proof['imported_operations'] != state['prefix_operations']
            or digest(last.read_bytes()) != seal['original_roots']['checkpoint']
            or proof['inherited_active_seconds'] != read(last)['active_seconds']):
        raise SessionBlocked('launch_completion_parent_changed')
    expected = dict(proof_file=str(path), proof_sha256=spec['proof_sha256'], version=VERSION,
        operator=str(root), seal_sha256=proof['parent_seal_sha256'],
        run_id=read(root/'plan.json')['run_id'], prefix_operations=proof['imported_operations'],
        historical_budget=proof['historical_budget'], active_seconds=proof['inherited_active_seconds'],
        frontier_request_sha256=proof['state']['frontier_sha256'])
    limits = contract.CONTRACT.descriptor()
    count = limits['max_calls']-proof['historical_budget']['calls']
    available = limits['total_tokens']-proof['historical_budget']['tokens']-proof['historical_budget']['reserved_tokens']
    expected.update(remaining_attempts=count, max_new_tokens=min(available, count*80384),
        estimated_additional_cny=str(Decimal(count)*Decimal('0.07296')))
    if spec != expected or count < 3 or available < 3*contract.FRESH_REVIEW_RESERVATION:
        raise SessionBlocked('launch_completion_scope_or_budget_changed')
    return proof


def bind(path, sha):
    path = Path(path).resolve()
    if digest(path.read_bytes()) != sha:
        raise ValueError('launch_completion_original_proof_required')
    proof = read(path)
    historical = proof['historical_budget']
    count = contract.CONTRACT.descriptor()['max_calls']-historical['calls']
    available = contract.CONTRACT.descriptor()['total_tokens']-historical['tokens']-historical['reserved_tokens']
    spec = dict(proof_file=str(path), proof_sha256=sha, version=VERSION,
        operator=proof['parent_operator'], seal_sha256=proof['parent_seal_sha256'],
        run_id=read(Path(proof['parent_operator'])/'plan.json')['run_id'],
        prefix_operations=proof['imported_operations'], historical_budget=historical,
        active_seconds=proof['inherited_active_seconds'],
        frontier_request_sha256=proof['state']['frontier_sha256'], remaining_attempts=count,
        max_new_tokens=min(available,count*80384),
        estimated_additional_cny=str(Decimal(count)*Decimal('0.07296')))
    verify_parent(spec)
    return spec


def import_prefix(session):
    proof = verify_parent(session.continuation)
    parent = Path(proof['parent_operator'])
    prefix = proof['imported_operations']
    for n in range(1, prefix+1):
        for suffix in ('intent', 'result'):
            name = f'{n:04d}-{suffix}.json'
            raw = (parent/'execution/session/operations'/name).read_bytes()
            if suffix == 'result' and n == prefix-3:
                row = read(parent/'execution/session/operations'/name)
                row['value']['budget'] = deepcopy(proof['derived_budget'])
                row['imported_from_sha256'] = digest(raw)
                raw = canonical(row)
            with (session.root/'operations'/name).open('xb') as stream:
                stream.write(raw)
    session.journal_root.mkdir(parents=True, exist_ok=False)
    shutil.copy2(parent/'execution/journal/facts-initial.json', session.journal_root/'facts-initial.json')
    write_new_json(session.root/'continuation-import.json', dict(version=VERSION,
        parent_seal_sha256=proof['parent_seal_sha256'], old_completion_accepted=False,
        original_failure_retained=True, inherited_operations=prefix,
        historical_budget=proof['historical_budget'], new_provider_requests=0))
    session.active_before = proof['inherited_active_seconds']
    session._checkpoint('accepted_facts_prefix_imported')


class InheritedFacts:
    def __init__(self, current, original, spec, handle):
        self.current, self.original, self.spec, self.handle = current, original, spec, handle

    def __getattr__(self, name):
        return getattr(self.current, name)

    def replay(self, handle):
        proof = verify_parent(self.spec)
        if Path(handle['folder']).is_relative_to(Path(proof['parent_operator'])):
            if handle != self.handle:
                raise SessionBlocked('launch_completion_inherited_handle_changed')
            return self.original.replay(handle)
        return self.current.replay(handle)

    def submit(self, handle, *args, **kwargs):
        if handle == self.handle:
            raise SessionBlocked('launch_completion_parent_resubmission_forbidden')
        return self.current.submit(handle, *args, **kwargs)


def attach_native(gate, spec, event_source):
    proof = verify_parent(spec)
    parent = Path(proof['parent_operator'])
    plan = read(parent/'plan.json')
    if gate.plan != plan['review_plan']:
        raise ValueError('launch_completion_original_native_owner_required')
    workspace = HostReviewWorkspace(cwd=plan['cwd'], python=plan['python'],
        answers=parent.with_name(parent.name+'-authors'), evidence_roots=[parent])
    gate.native = InheritedFacts(gate.native, ExactNativeGate(plan['review_plan'],workspace,event_source),
                                spec,proof['accepted_handle'])


def verify_frontier(session, kind, request):
    spec = session.continuation
    if session.contract_module is not contract:
        raise SessionBlocked('launch_completion_contract_changed')
    if session.cursor == spec['prefix_operations'] and (kind != 'model'
            or digest(canonical(request)) != spec['frontier_request_sha256']):
        raise SessionBlocked('launch_completion_frontier_changed')
    if kind == 'model' and session.cursor >= spec['prefix_operations'] and contract.CONTEXT not in request.get('metadata', {}):
        raise SessionBlocked('launch_completion_generation_forbidden')
