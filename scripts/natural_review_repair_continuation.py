"""Inherit a sealed initial pair without retrying or accepting its rejection."""
from decimal import Decimal
import json
from pathlib import Path
import shutil
import subprocess
import sys

from app.evaluation import sol_review_contract as contract
from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import SessionBlocked, canonical, digest
from scripts.reviewer_profile_batch import inventory

VERSION = 'natural-rejected-initial-repair-continuation-v1'
PROOF = 'natural-rejected-initial-repair-proof-v1'


def read(path):
    return json.loads(Path(path).read_bytes())


def state(root):
    """Select the complete pair and budget by committed operations, not dates."""
    root = Path(root)
    folder = root/'execution/session'
    terminal = read(folder/'terminal.json')
    if terminal != dict(reason='semantic_rejected', key='completion-initial',
                        publication_allowed=False, production_admitted=False):
        raise SessionBlocked('repair_parent_completion_rejection_required')
    rows, values = [], []
    for n, path in enumerate(sorted((folder/'operations').glob('*-intent.json')), 1):
        row = read(path)
        result = read(path.with_name(path.name.replace('-intent', '-result')))
        if (path.name != f'{n:04d}-intent.json' or row['ordinal'] != n
                or result['intent_sha256'] != digest(path.read_bytes())):
            raise SessionBlocked('repair_parent_operation_changed')
        rows.append(row)
        values.append(result['value'])
    hosts = [n for n, row in enumerate(rows) if row['kind'] == 'host-task']
    if (len(hosts) != 2 or hosts[-1] != len(rows)-1 or hosts[1] != hosts[0]+4
            or [rows[n]['request']['key'] for n in hosts] != ['facts-initial', 'completion-initial']
            or [r['kind'] for r in rows[hosts[0]-2:]] !=
                ['model', 'journal', 'host-task', 'host-decision', 'model', 'journal', 'host-task']
            or values[hosts[0]+1] != dict(accepted=True)):
        raise SessionBlocked('repair_parent_complete_pair_required')
    handles = {}
    for n, duty in zip(hosts, ('facts', 'completion')):
        handle = values[n]
        context = rows[n-2]['request'].get('metadata', {}).get(contract.CONTEXT, {})
        if (context.get('version') != contract.VERSION or context.get('duty') != duty
                or context.get('stage') != 'initial' or values[n-2].get('ok') is not True
                or rows[n-1]['request'].get('name') != duty+'-initial'
                or handle['binding'] != rows[n]['request']['binding']
                or handle['binding']['key'] != duty+'-initial'):
            raise SessionBlocked('repair_parent_pair_binding_changed')
        submission = read(Path(handle['folder'])/'submission.json')
        accepted = all(submission[r]['decision']['accepted'] for r in ('primary', 'independent'))
        if accepted != (duty == 'facts'):
            raise SessionBlocked('repair_parent_original_decision_changed')
        if duty == 'completion':
            defects = [d for r in ('primary', 'independent') for d in submission[r]['decision']['defects']]
            if not defects or any(d['kind'] != 'missed_error' for d in defects):
                raise SessionBlocked('repair_parent_missed_error_required')
        handles[duty+'-initial'] = handle
    budget = values[-3]['budget']
    if (budget['logical'] != dict(generation=2, review=2) or budget['failed'] or budget['stopped']
            or budget['router_calls'] != budget['calls'] or len(budget['attempts']) != budget['calls']
            or budget['attempts'][-1]['status'] != 'completed'):
        raise SessionBlocked('repair_parent_budget_changed')
    last = sorted((folder/'checkpoints').glob('*.json'))[-1]
    return dict(prefix_operations=len(rows), handles=handles, historical_budget=budget,
                active_seconds=read(last)['active_seconds'], checkpoint_sha256=digest(last.read_bytes()))


def preview(current):
    from scripts import review_duty_direct_patch as direct
    opinions, source = [], None
    for duty in ('facts', 'completion'):
        material = read(Path(current['handles'][duty+'-initial']['folder'])/'material.json')
        inputs = contract.restore_context(json.loads(material['request_raw'])['metadata'][contract.CONTEXT])
        if source is not None and inputs != source:
            raise SessionBlocked('repair_parent_sources_differ')
        source = inputs
        opinions.append(direct.bind(inputs, duty, material['responses'][0]))
    assembled = direct.preview(source, opinions)
    if assembled.report == source.source.report:
        raise SessionBlocked('repair_parent_no_actual_edits')
    return dict(original_report_sha256=digest(source.source.report.encode()),
                preview_report_sha256=digest(assembled.report.encode()),
                patch_journal_sha256=digest(canonical(assembled.journal)))


def parent_inputs(operator, seal_sha):
    root = Path(operator).resolve()
    seal = read(root/'seal.json')
    plan = read(root/'plan.json')
    if (digest((root/'seal.json').read_bytes()) != seal_sha
            or inventory(root) != dict(seal['inventory'], **{'seal.json': seal_sha})
            or digest((root/'plan.json').read_bytes()) != seal['plan_sha256']
            or Path(plan['operator']).resolve() != root
            or seal['result'].get('reason') != 'semantic_rejected'
            or seal['result'].get('strict_replay') is not True):
        raise SessionBlocked('repair_parent_seal_or_inventory_changed')
    if plan.get('continuation'):
        from scripts.sol_natural_continuation import verify_parent as verify_ancestor
        verify_ancestor(plan['continuation'])
    current = state(root)
    if (current['checkpoint_sha256'] != seal['original_roots']['checkpoint']
            or {k:current['historical_budget'][k] for k in ('calls','tokens','reserved_tokens','retries')}
                != seal['result']['accounting']):
        raise SessionBlocked('repair_parent_terminal_budget_changed')
    return root, plan, seal, current


def audit(operator, seal_sha, event_source):
    from scripts import sol_natural_launch as launch
    root, plan, seal, current = parent_inputs(operator, seal_sha)
    authors = root.with_name(root.name+'-authors')
    before, author_before = inventory(root), inventory(authors)
    if Path(plan['cwd']).resolve() == launch.ROOT.resolve():
        replayed = launch.replay(plan, seal['plan_sha256'], event_source, **seal['original_roots'])
    else:
        replayed = frozen_replay(root, plan)
    if replayed != seal['result']:
        raise SessionBlocked('repair_parent_native_replay_changed')
    assembly = preview(current)
    if before != inventory(root) or author_before != inventory(authors):
        raise SessionBlocked('repair_parent_audit_mutated_originals')
    return dict(version=PROOF, parent_operator=str(root), parent_seal_sha256=seal_sha,
        parent_inventory=before, parent_author_inventory=author_before, state=current,
        assembly=assembly, original_strict_replay=replayed, original_native_pair_replayed=True,
        original_rejection_retained=True, provider_requests=0, key_reads=0)


def frozen_replay(root, plan):
    """Use the original checkout's reader; never relax its cwd/source guard."""
    cwd = Path(plan['cwd'])
    if (subprocess.check_output(['git','rev-parse','HEAD'], cwd=cwd, text=True).strip() != plan['head']
            or subprocess.check_output(['git','status','--porcelain'], cwd=cwd).strip()
            or Path(plan['python']).resolve() != Path(sys.executable).resolve()):
        raise SessionBlocked('repair_original_frozen_execution_required')
    code = '''import json,sys
from pathlib import Path
from scripts import sol_natural_launch as launch
root=Path(sys.argv[1]); plan=json.loads((root/'plan.json').read_bytes())
seal=json.loads((root/'seal.json').read_bytes())
with launch.host(plan) as events:
    result=launch.replay(plan,seal['plan_sha256'],events,**seal['original_roots'])
print('REPAIR_PARENT_REPLAY='+json.dumps(result,ensure_ascii=True))
'''
    output = subprocess.check_output([plan['python'],'-X','utf8','-c',code,str(root)],
        cwd=cwd, text=True, encoding='utf-8', timeout=180)
    lines = [line[len('REPAIR_PARENT_REPLAY='):] for line in output.splitlines()
             if line.startswith('REPAIR_PARENT_REPLAY=')]
    if len(lines) != 1:
        raise SessionBlocked('repair_original_replay_output_required')
    return json.loads(lines[0])


def _spec(path, sha, proof):
    from scripts.sol_natural_launch import limits as launch_limits
    root, plan, _, current = parent_inputs(proof['parent_operator'], proof['parent_seal_sha256'])
    limits = contract.CONTRACT.descriptor()
    if plan['limits'] != launch_limits(contract):
        raise SessionBlocked('repair_parent_limits_changed')
    budget = current['historical_budget']
    remaining = limits['max_calls']-budget['calls']
    available = limits['total_tokens']-budget['tokens']-budget['reserved_tokens']
    if (remaining < 2 or available < 2*contract.FRESH_REVIEW_RESERVATION
            or current['active_seconds'] >= limits['execution_timeout_s']):
        raise SessionBlocked('repair_parent_budget_exhausted')
    return dict(version=VERSION, proof_file=str(path), proof_sha256=sha, operator=str(root),
        seal_sha256=proof['parent_seal_sha256'], run_id=plan['run_id'],
        prefix_operations=current['prefix_operations'], historical_budget=budget,
        active_seconds=current['active_seconds'], remaining_attempts=remaining,
        max_new_tokens=min(available, remaining*80384),
        estimated_additional_cny=str(Decimal(remaining)*Decimal('0.07296')))


def verify_parent(spec):
    path = Path(spec['proof_file'])
    if digest(path.read_bytes()) != spec['proof_sha256']:
        raise SessionBlocked('repair_original_proof_changed')
    proof = read(path)
    root, _, seal, current = parent_inputs(spec['operator'], spec['seal_sha256'])
    if (proof.get('version') != PROOF or proof.get('original_native_pair_replayed') is not True
            or proof.get('original_rejection_retained') is not True
            or proof.get('provider_requests') != 0 or proof.get('key_reads') != 0
            or Path(proof['parent_operator']).resolve() != root
            or proof['parent_seal_sha256'] != spec['seal_sha256']
            or proof['parent_inventory'] != inventory(root)
            or proof['parent_author_inventory'] != inventory(root.with_name(root.name+'-authors'))
            or proof['state'] != current or proof['assembly'] != preview(current)
            or proof['original_strict_replay'] != seal['result']
            or spec != _spec(path, spec['proof_sha256'], proof)):
        raise SessionBlocked('repair_parent_proof_or_scope_changed')
    return proof


def bind(path, sha):
    path = Path(path).resolve()
    if digest(path.read_bytes()) != sha:
        raise ValueError('repair_original_proof_required')
    spec = _spec(path, sha, read(path))
    verify_parent(spec)
    return spec


def import_prefix(session):
    proof = verify_parent(session.continuation)
    parent = Path(proof['parent_operator'])
    for name in proof['parent_inventory']:
        if name.startswith('execution/session/operations/') and name.endswith(('-intent.json', '-result.json')):
            target = session.root/'operations'/Path(name).name
            with target.open('xb') as stream:
                stream.write((parent/name).read_bytes())
    session.journal_root.mkdir(parents=True, exist_ok=False)
    for duty in ('facts', 'completion'):
        shutil.copy2(parent/f'execution/journal/{duty}-initial.json', session.journal_root/f'{duty}-initial.json')
    write_new_json(session.root/'continuation-import.json', dict(version=VERSION,
        parent_seal_sha256=session.continuation['seal_sha256'], original_review_accepted=False,
        inherited_operations=proof['state']['prefix_operations'], budgets_copied_without_reset=True,
        new_provider_requests=0))
    session.active_before = session.continuation['active_seconds']
    session._checkpoint('rejected_initial_pair_imported')


class InheritedReviews:
    def __init__(self, current, original, spec, handles):
        self.current, self.original, self.spec, self.handles = current, original, spec, handles

    def __getattr__(self, name):
        return getattr(self.current, name)

    def inherited_binding(self, bound):
        original = self.handles.get(bound['key'])
        if original is None:
            return bound
        old = original['binding']
        if {k:v for k,v in old.items() if k != 'plan_sha256'} != {
                k:v for k,v in bound.items() if k != 'plan_sha256'}:
            raise SessionBlocked('repair_inherited_business_binding_changed')
        return old

    def replay(self, handle):
        if handle in self.handles.values():
            # Whole sealed inventories are verified on session entry, before
            # new IO and at closure. Re-read each actual native task here.
            return self.original[handle['binding']['key']].replay(handle)
        return self.current.replay(handle)

    def submit(self, handle, *args, **kwargs):
        if handle in self.handles.values():
            raise SessionBlocked('repair_parent_resubmission_forbidden')
        return self.current.submit(handle, *args, **kwargs)


def attach_native(gate, spec, event_source):
    from scripts.codex_review_event_source import CodexHostReviewEventSource
    from scripts.host_review_workspace import HostReviewWorkspace
    from scripts.reviewer_profile_batch import ExactNativeGate
    proof = verify_parent(spec)
    root = Path(proof['parent_operator'])
    plan = read(root/'plan.json')
    expected = dict(plan['review_plan'], initial_review_rejection_policy=gate.PAUSE_INITIAL)
    if gate.plan != expected:
        raise SessionBlocked('repair_original_native_owners_required')
    events = CodexHostReviewEventSource(event_source.client, plan['review_plan'])
    workspace = HostReviewWorkspace(cwd=plan['cwd'], python=plan['python'],
        answers=root.with_name(root.name+'-authors'), evidence_roots=[root])
    reader = ExactNativeGate(plan['review_plan'],workspace,events)
    original = {key: reader for key in proof['state']['handles']}
    if plan.get('continuation'):
        if plan['continuation']['version'] != 'natural-accepted-facts-continuation-v1':
            raise SessionBlocked('repair_unsupported_parent_ancestry')
        from scripts.natural_completion_continuation import verify_parent as facts_parent
        ancestor = facts_parent(plan['continuation'])
        if ancestor['accepted_handle'] != proof['state']['handles']['facts-initial']:
            raise SessionBlocked('repair_original_facts_handle_changed')
        facts_root = Path(ancestor['parent_operator'])
        facts_plan = read(facts_root/'plan.json')
        facts_workspace = HostReviewWorkspace(cwd=facts_plan['cwd'], python=facts_plan['python'],
            answers=facts_root.with_name(facts_root.name+'-authors'), evidence_roots=[facts_root])
        original['facts-initial'] = ExactNativeGate(facts_plan['review_plan'], facts_workspace,
            CodexHostReviewEventSource(event_source.client, facts_plan['review_plan']))
    gate.native = InheritedReviews(gate.native, original, spec, proof['state']['handles'])


def verify_frontier(session, kind, request):
    if session.contract_module is not contract:
        raise SessionBlocked('repair_continuation_contract_changed')
    if session.cursor >= session.continuation['prefix_operations'] and kind == 'model':
        context = request.get('metadata', {}).get(contract.CONTEXT, {})
        if context.get('stage') != 'fresh' or context.get('duty') not in ('facts', 'completion'):
            raise SessionBlocked('repair_continuation_only_fresh_allowed')
