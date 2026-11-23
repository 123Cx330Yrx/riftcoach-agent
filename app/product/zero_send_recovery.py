"""Create-only recovery after an administrative retry, before its model intent.

This is not a semantic-rejection retry. A pinned pre-execution checkpoint must
prove that the only committed operation since it was one manual-retry decision.
The rejected parent, including its terminal and all costs, remains immutable.
"""
from copy import deepcopy
import json
from pathlib import Path
import zipfile

from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import digest, tree
from app.product import sol_contract
from app.product.local_failure_recovery import _safe, _session
from app.product.session_usage import session_accounting

VERSION = 'product-zero-send-recovery-v1'


def read(path):
    return json.loads(Path(path).read_bytes())


def inspect_parent(parent, reference, baseline_sha):
    parent = _safe(parent)
    binding = reference['binding']
    if (reference['profile'] != sol_contract.WORKER_PROFILE or parent.name != binding['run_id']
            or binding.get('execution_contract') != sol_contract.CONTRACT.snapshot().model_dump(mode='json')):
        raise ValueError('zero_send_recovery_binding')
    with _session(parent, reference) as session:
        terminal = read(session.root/'terminal.json')
        terminal_value = terminal['value']
        if (terminal != dict(value=terminal_value, publication_allowed=False, production_admitted=False)
                or set(terminal_value) != {'run_id', 'segment', 'terminal_reason'}
                or terminal_value['run_id'] != parent.name or terminal_value['terminal_reason'] != 'evaluation_failed'
                or type(terminal_value['segment']) is not int or terminal_value['segment'] < 1
                or (session.root/'seal.json').exists() or tree(session.journal_root)):
            raise ValueError('zero_send_recovery_not_local_frontier')
        baseline_path = next((session.root/n for n, sha in tree(session.root).items()
            if n.startswith('checkpoints/') and sha == baseline_sha), None)
        if baseline_path is None:
            raise ValueError('zero_send_recovery_baseline')
        baseline = read(baseline_path)
        old = baseline['inventory']
        current = session._inventory()
        if old['transport'] != current['transport'] or old['journal'] != current['journal']:
            raise ValueError('zero_send_recovery_new_transport_or_review')
        if any(current['session'].get(n) != sha for n, sha in old['session'].items()):
            raise ValueError('zero_send_recovery_prefix_changed')
        intents = sorted((session.root/'operations').glob('*-intent.json'))
        if len(intents) < 2:
            raise ValueError('zero_send_recovery_missing_prefix')
        last, prior = intents[-1], intents[-2]
        expected_new = {'terminal.json', 'operations/'+last.name,
                        'operations/'+last.name.replace('-intent', '-result')}
        if set(current['session']) - set(old['session']) != expected_new:
            raise ValueError('zero_send_recovery_not_single_retry')
        for index, path in enumerate(intents, 1):
            intent, result = read(path), read(path.with_name(path.name.replace('-intent', '-result')))
            if (path.name != f'{index:04d}-intent.json' or intent['ordinal'] != index
                    or result['intent_sha256'] != digest(path.read_bytes())):
                raise ValueError('zero_send_recovery_operation_binding')
            if intent['kind'] == 'model':
                from app.runtime.sol_session_receipts import request_from_raw
                issued = request_from_raw(result['value'].get('issued_raw') or result['value']['reaped_timeout']['issued_raw'])
                role = sol_contract.role_for_request(issued)
                if role == 'review' and (result['value'].get('ok') is not False
                        or not result['value'].get('reaped_timeout')):
                    raise ValueError('zero_send_recovery_review_result')
            elif intent['kind'] not in {'source', 'publication-source', 'memory', 'memory-manifest', 'tool', 'manual-retry'}:
                raise ValueError('zero_send_recovery_unexpected_operation')
        previous = read(prior.with_name(prior.name.replace('-intent', '-result')))
        intent, decision = read(last), result['value']
        failure = previous['value']
        if (read(prior)['kind'] != 'model' or not failure.get('reaped_timeout')
                or intent['kind'] != 'manual-retry' or decision.get('automatic') is not False
                or decision.get('same_stage') is not True
                or intent['request'].get('failed_result_sha256') != digest(prior.with_name(prior.name.replace('-intent', '-result')).read_bytes())
                or intent['request'].get('timeout') != failure['reaped_timeout']
                or intent['request'].get('budget') != failure['budget']):
            raise ValueError('zero_send_recovery_retry_binding')
        expected = deepcopy(failure['budget'])
        expected.update(retries=expected['retries']+1, stopped=False, failed=False,
                        retry_issued_raw=failure['reaped_timeout']['issued_raw'])
        if decision['budget'] != expected:
            raise ValueError('zero_send_recovery_retry_accounting')
        grant = intent['request'].get('retry_grant')
        if grant is not None:
            from app.product.manual_retry_grant import validate
            validate(grant, session=session, failed_sha=intent['request']['failed_result_sha256'],
                     retries=failure['budget']['retries'], replay=True)
        accounting = session_accounting(session)
        if accounting != reference['accounting'] or accounting['unresolved_intents']:
            raise ValueError('zero_send_recovery_accounting')
        segment = parent/'.continuation/segments'/str(terminal_value['segment'])/parent.name
        receipt = read(segment/'api_run_receipt.json')
        trace = read(segment/'runtime_trace.json')
        if (receipt.get('terminal_reason') != 'evaluation_failed' or receipt.get('report_available') is not False
                or receipt.get('runtime_status') != 'completed'
                or any((segment/'evaluations').glob('*.json'))):
            raise ValueError('zero_send_recovery_semantic_result')
        trace_ref = receipt['trace_reference']
        if (trace_ref['relative_path'] != 'runtime_trace.json'
                or trace_ref['sha256'] != digest((segment/'runtime_trace.json').read_bytes())):
            raise ValueError('zero_send_recovery_trace_binding')
        # No operation/transport delta is the authoritative send proof; retain
        # the trace as independent execution evidence, not a substitute for it.
        if not trace.get('events'):
            raise ValueError('zero_send_recovery_trace_missing')
        supplement = read(session.root/'budget-supplement.json') if (session.root/'budget-supplement.json').exists() else None
        if supplement is not None:
            from app.product.budget_supplement import validate
            validate(supplement, session)
        return dict(binding=binding, accounting=accounting, terminal=terminal,
                    baseline_sha256=baseline_sha, active_seconds=session.active_before,
                    budget_supplement=supplement)


def prepare(*, parent_run, destination_root, reference, baseline_sha256):
    parent, root = _safe(parent_run), _safe(destination_root)
    child = root/parent.name
    if root.exists() or child.is_relative_to(parent) or parent.is_relative_to(child):
        raise ValueError('zero_send_recovery_destination_not_new')
    state = inspect_parent(parent, reference, baseline_sha256)
    before, pins = tree(parent), []
    with _session(child, dict(binding=state['binding']), read_only=False, sink=pins.append) as session:
        session.active_before = state['active_seconds']
        for source, target in ((parent/'.continuation/session/operations', session.root/'operations'),
                               (parent/'.continuation/transport'/parent.name, session.transport_root)):
            for name in tree(source):
                output = target/name
                output.parent.mkdir(parents=True, exist_ok=True)
                with output.open('xb') as stream: stream.write((source/name).read_bytes())
        # Preserve the older nonstream migration too; its committed grants keep
        # their original checkpoint pins during replay.
        for name in ('session/stream-migration.json', 'nonstream-parent.zip'):
            source = parent/'.continuation'/name
            if source.exists():
                target = child/'.continuation'/name
                with target.open('xb') as stream: stream.write(source.read_bytes())
        archive = child/'.continuation/zero-send-parent.zip'
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
            for name in before: bundle.writestr(name, (parent/name).read_bytes())
        write_new_json(session.root/'zero-send-recovery.json', dict(version=VERSION,
            binding=state['binding'], parent_guard_sha256=reference['guard_sha256'],
            parent_checkpoint_sha256=reference['checkpoint_sha256'], archive_sha256=digest(archive.read_bytes())))
        session._checkpoint('zero_send_prefix_imported')
        if state['budget_supplement'] is not None:
            from app.product.budget_supplement import activate
            supplement = dict(state['budget_supplement'], guard_sha256=session.guard_sha,
                checkpoint_sha256=session.checkpoint_sha, baseline=state['accounting'])
            activate(session, supplement)
        if session_accounting(session) != state['accounting']:
            raise ValueError('zero_send_recovery_budget_changed')
    if tree(parent) != before:
        raise ValueError('zero_send_recovery_parent_changed')
    proof = dict(version=VERSION, parent_run=str(parent), destination_root=str(root), parent_inventory=before,
        parent_reference=reference, parent_state=state, binding=state['binding'], accounting=state['accounting'],
        child_checkpoint={**pins[-1], 'checkpoint':Path(pins[-1]['checkpoint']).name},
        child_inventory=tree(child), new_model_requests=0)
    path = root/'zero-send-recovery-proof.json'
    write_new_json(path, proof)
    return path, digest(path.read_bytes())


def replay_checkpoint_pins(session):
    path = session.root/'zero-send-recovery.json'
    if not path.exists(): return set()
    value = read(path)
    archive = session.root.parent/'zero-send-parent.zip'
    if (not session.worker_product or value['version'] != VERSION or value['binding'] != session.binding
            or digest(archive.read_bytes()) != value['archive_sha256']):
        raise ValueError('zero_send_recovery_archive_binding')
    with zipfile.ZipFile(archive) as bundle:
        prefix = '.continuation/session/'
        previous = digest(bundle.read(prefix+'guard.json'))
        if previous != value['parent_guard_sha256']:
            raise ValueError('zero_send_recovery_guard')
        pins = set()
        names = sorted(n for n in bundle.namelist() if n.startswith(prefix+'checkpoints/') and n.endswith('.json'))
        for index, name in enumerate(names, 1):
            raw = bundle.read(name); checkpoint = json.loads(raw)
            if (name != prefix+f'checkpoints/{index:04d}.json' or checkpoint['previous_sha256'] != previous
                    or checkpoint['guard_sha256'] != value['parent_guard_sha256']):
                raise ValueError('zero_send_recovery_checkpoint_chain')
            previous = digest(raw); pins.add(previous)
        if previous != value['parent_checkpoint_sha256']:
            raise ValueError('zero_send_recovery_checkpoint')
    return pins


def verify(path, sha, *, runs_root):
    path, root = _safe(path), _safe(runs_root)
    if digest(path.read_bytes()) != sha:
        raise ValueError('zero_send_recovery_proof_changed')
    proof = read(path); parent = _safe(proof['parent_run']); child = root/parent.name
    if (proof['version'] != VERSION or proof['destination_root'] != str(root)
            or proof['new_model_requests'] != 0 or tree(parent) != proof['parent_inventory']
            or tree(child) != proof['child_inventory']):
        raise ValueError('zero_send_recovery_inventory')
    state = inspect_parent(parent, proof['parent_reference'], proof['parent_state']['baseline_sha256'])
    if state != proof['parent_state'] or state['binding'] != proof['binding'] or state['accounting'] != proof['accounting']:
        raise ValueError('zero_send_recovery_state')
    with zipfile.ZipFile(child/'.continuation/zero-send-parent.zip') as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)) or {n:digest(bundle.read(n)) for n in names} != proof['parent_inventory']:
            raise ValueError('zero_send_recovery_archive')
    for part in ('session/operations', 'transport'):
        if tree(parent/'.continuation'/part) != tree(child/'.continuation'/part):
            raise ValueError('zero_send_recovery_prefix')
    with _session(child, dict(binding=proof['binding'], **proof['child_checkpoint'])) as session:
        replay_checkpoint_pins(session)
        if (session.root/'terminal.json').exists() or (session.root/'seal.json').exists() or tree(session.journal_root):
            raise ValueError('zero_send_recovery_child_not_frontier')
        if session_accounting(session) != state['accounting'] or session.active_before < state['active_seconds']:
            raise ValueError('zero_send_recovery_accounting')
        old = state['budget_supplement']
        new = read(session.root/'budget-supplement.json') if (session.root/'budget-supplement.json').exists() else None
        if old is None and new is not None or old is not None and (new is None or
                any(new[k] != v for k,v in old.items() if k not in {'guard_sha256','checkpoint_sha256','baseline'})):
            raise ValueError('zero_send_recovery_limits_changed')
        if new is not None:
            from app.product.budget_supplement import validate
            validate(new, session)
            if new['baseline'] != state['accounting']:
                raise ValueError('zero_send_recovery_baseline_changed')
    return proof
