"""Create-only, zero-send migration of an unreviewed 1.7.0 product task.

Only successful generation and receipted nonstream 524s can be inherited.
This changes neither budgets nor retry permission. Original evidence is archived.
"""
from dataclasses import asdict
import json
from pathlib import Path
import zipfile

from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import digest, tree
from app.product import sol_contract
from app.product.local_failure_recovery import _safe, _session
from app.product.session_usage import session_accounting

VERSION = 'sol-product-stream-migration-v1'
OLD_MODE = 'natural-sol-dual-necessity-v1'
OLD_CONTRACT = dict(contract_id=sol_contract.VERSION, version='1.7.0', scope='unadmitted_opt_in',
    sha256='745668406bfc57b4654b82820c1f536580760af61cc6349d06d25b2634e2909e')


def read(path):
    return json.loads(Path(path).read_bytes())


def inspect_parent(parent, reference):
    from app.runtime.sol_session_receipts import recover_success, request_from_raw
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    from scripts.prepare_reviewer_profile_screen import visible, json_value
    from scripts.reviewer_responses_nonstream import build_wire
    parent = _safe(parent)
    binding = reference['binding']
    if (reference['profile'] != sol_contract.WORKER_PROFILE or parent.name != binding['run_id']
            or binding.get('execution_contract', OLD_CONTRACT) != OLD_CONTRACT
            or reference.get('manual_retry') is True):
        raise ValueError('stream_migration_parent_binding')
    with _session(parent, reference) as session:
        if any((session.root/n).exists() for n in ('terminal.json', 'seal.json')) or tree(session.journal_root):
            raise ValueError('stream_migration_review_already_started')
        accounting = session_accounting(session)
        if accounting != reference['accounting'] or accounting['unresolved_intents']:
            raise ValueError('stream_migration_accounting')
        calls = known = unknown = retries = successes = failures = 0
        first_wire = None
        generated_report = None
        last = None
        for index, path in enumerate(sorted((session.root/'operations').glob('*-intent.json')), 1):
            intent = read(path)
            result = read(path.with_name(path.name.replace('-intent', '-result')))
            if (path.name != f'{index:04d}-intent.json' or intent['ordinal'] != index
                    or result['intent_sha256'] != digest(path.read_bytes())):
                raise ValueError('stream_migration_operation_binding')
            value, kind = result['value'], intent['kind']
            if kind == 'model':
                calls += 1
                attempt = read(session.root/'operations'/f'attempt-{calls:03d}.json')
                if attempt['intent_sha256'] != digest(path.read_bytes()) or attempt['ordinal'] != calls:
                    raise ValueError('stream_migration_attempt_binding')
                req = request_from_raw(attempt['issued_raw'])
                role = sol_contract.role_for_request(req)
                if value.get('ok') is True and role == 'generation' and failures == 0:
                    recovered, _, _ = recover_success(session.transport_root, intent, attempt, contract_module=sol_contract)
                    if any(recovered[k] != value[k] for k in ('response_raw', 'issued_raw', 'budget', 'receipt_request_sha256')):
                        raise ValueError('stream_migration_generation_changed')
                    generated = json.loads(value['response_raw'])
                    usage = generated['usage']
                    generated_report = generated.get('content') if generated['finish_reason'] == 'stop' else None
                    known += usage['input_tokens'] + usage['output_tokens']
                    successes += 1
                elif value.get('ok') is False and role == 'review' and successes:
                    failure = value['reaped_timeout']
                    folder = session.transport_root/'review'/f'call-{calls:03d}'
                    receipt, obs, worker = (read(folder/n) for n in ('receipt.json','observation/observation.json','worker-result.json'))
                    business = visible(json_value(req))
                    context = req.metadata[sol_contract.CONTEXT]
                    sol_contract.validate_business(business, context)
                    if (not generated_report or context['report'] != generated_report
                            or context['stage'] != 'initial' or context['duty'] != 'facts'):
                        raise ValueError('stream_migration_report_binding')
                    wire = build_wire(business)
                    if first_wire is None: first_wire = wire
                    expected_profile = dict(**asdict(sol_contract.REVIEW_PROFILE), reasoning_effort='high', api='responses',
                        max_output_tokens=16384, max_retries=0, timeout_s=req.timeout_s,
                        group_verified=False, upstream_identity_verified=False, response_mode=OLD_MODE)
                    if (wire != first_wire or failure['role'] != 'review' or failure['ordinal'] != calls
                            or failure['issued_raw'] != attempt['issued_raw']
                            or failure['receipt_sha256'] != digest((folder/'receipt.json').read_bytes())
                            or read(folder/'request.json') != business or read(folder/'validation-context.json') != context
                            or read(folder/'profile.json') != expected_profile
                            or receipt.get('request_sha256') != digest_json(business)
                            or receipt.get('validation_context_sha256') != digest_json(context)
                            or receipt.get('wire_sha256') != digest_json(wire)
                            or receipt.get('profile') != asdict(sol_contract.REVIEW_PROFILE)
                            or receipt.get('response_mode') != OLD_MODE or receipt.get('ok') is not False
                            or receipt.get('code') != 'worker_rejected' or receipt.get('worker_code') != 'http_status_524'
                            or receipt.get('reaped') is not True or receipt.get('worker_exit') != 0
                            or receipt.get('usage_state') != 'unknown' or receipt.get('usage') is not None
                            or receipt.get('usage_conflict') is not False or receipt.get('http_requests') != 1
                            or obs.get('http_requests') != 1 or obs.get('response_status') != 524
                            or obs.get('closed') is not True or worker.get('code') != 'http_status_524'
                            or worker.get('ok') is not False or worker.get('usage') is not None
                            or worker.get('public_tool_call') is not None):
                        raise ValueError('stream_migration_timeout_receipt')
                    unknown += estimate_runtime_request_input_ceiling(req) + req.max_tokens
                    failures += 1
                else:
                    raise ValueError('stream_migration_unsupported_model_result')
            elif kind == 'manual-retry':
                if not failures or value.get('automatic') is not False or value.get('same_stage') is not True:
                    raise ValueError('stream_migration_retry_changed')
                retries += 1
            elif kind not in ('source','publication-source','memory','memory-manifest','tool') or failures:
                raise ValueError('stream_migration_unexpected_operation')
            if isinstance(value, dict) and 'budget' in value:
                b = value['budget']
                if (b['calls'],b['tokens'],b['reserved_tokens'],b['retries'],len(b['attempts'])) != (calls,known,unknown,retries,calls):
                    raise ValueError('stream_migration_budget_changed')
            last = value
        if (not failures or not last.get('reaped_timeout') or failures != retries+1
                or len(list((session.root/'operations').glob('attempt-*.json'))) != calls):
            raise ValueError('stream_migration_frontier')
        return dict(binding=binding, accounting=accounting, active_seconds=session.active_before,
                    successful_generation=successes, failed_nonstream_524=failures,
                    original_contract=OLD_CONTRACT, first_review_wire_sha256=digest_json(first_wire))


def digest_json(value):
    from scripts.reviewer_responses_transport import digest as wire_digest
    return wire_digest(value)


def prepare(*, parent_run, destination_root, reference):
    parent, root = _safe(parent_run), _safe(destination_root)
    child = root/parent.name
    if root.exists() or child.is_relative_to(parent) or parent.is_relative_to(child):
        raise ValueError('stream_migration_destination_not_new')
    state = inspect_parent(parent, reference)
    before = tree(parent)
    binding = dict(state['binding'], execution_contract=sol_contract.CONTRACT.snapshot().model_dump(mode='json'))
    pins = []
    with _session(child, dict(binding=binding), read_only=False, sink=pins.append) as session:
        session.active_before = state['active_seconds']
        for source, target in ((parent/'.continuation/session/operations', session.root/'operations'),
                               (parent/'.continuation/transport'/parent.name, session.transport_root)):
            for name in tree(source):
                output = target/name
                output.parent.mkdir(parents=True, exist_ok=True)
                with output.open('xb') as file: file.write((source/name).read_bytes())
        with zipfile.ZipFile(child/'.continuation/nonstream-parent.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
            for name in before: archive.writestr(name,(parent/name).read_bytes())
        write_new_json(session.root/'stream-migration.json', dict(version=VERSION,
            original_contract=OLD_CONTRACT, parent_binding=state['binding'],
            parent_guard_sha256=reference['guard_sha256'], parent_checkpoint_sha256=reference['checkpoint_sha256'],
            archive_sha256=digest((child/'.continuation/nonstream-parent.zip').read_bytes())))
        session._checkpoint('nonstream_prefix_imported')
        if session_accounting(session) != state['accounting']:
            raise ValueError('stream_migration_accounting_changed')
    if tree(parent) != before: raise ValueError('stream_migration_parent_changed')
    proof = dict(version=VERSION, parent_run=str(parent), destination_root=str(root), parent_inventory=before,
        parent_reference=reference, parent_state=state, binding=binding, accounting=state['accounting'],
        child_checkpoint={**pins[-1], 'checkpoint':Path(pins[-1]['checkpoint']).name},
        child_inventory=tree(child), new_model_requests=0, budgets_changed=False)
    path = root/'stream-migration-proof.json'
    write_new_json(path,proof)
    return path,digest(path.read_bytes())


def verify(path, sha, *, runs_root):
    path,root = _safe(path),_safe(runs_root)
    if digest(path.read_bytes()) != sha: raise ValueError('stream_migration_proof_changed')
    p=read(path)
    if p['version'] != VERSION or p['destination_root'] != str(root) or p['new_model_requests'] != 0 or p['budgets_changed'] is not False:
        raise ValueError('stream_migration_proof_binding')
    parent=_safe(p['parent_run']);child=root/parent.name
    if tree(parent)!=p['parent_inventory'] or tree(child)!=p['child_inventory']:
        raise ValueError('stream_migration_inventory_changed')
    if inspect_parent(parent,p['parent_reference'])!=p['parent_state']:
        raise ValueError('stream_migration_parent_changed')
    expected=dict(p['parent_state']['binding'],execution_contract=sol_contract.CONTRACT.snapshot().model_dump(mode='json'))
    if p['binding']!=expected or p['accounting']!=p['parent_state']['accounting']:
        raise ValueError('stream_migration_binding_changed')
    with zipfile.ZipFile(child/'.continuation/nonstream-parent.zip') as archive:
        names=archive.namelist()
        if len(set(names))!=len(names) or {n:digest(archive.read(n)) for n in names}!=p['parent_inventory']:
            raise ValueError('stream_migration_archive_changed')
    for sub in ('session/operations','transport'):
        if tree(parent/'.continuation'/sub)!=tree(child/'.continuation'/sub):
            raise ValueError('stream_migration_prefix_changed')
    with _session(child,dict(binding=p['binding'],**p['child_checkpoint'])) as session:
        if session_accounting(session)!=p['accounting'] or session.active_before<p['parent_state']['active_seconds']:
            raise ValueError('stream_migration_accounting_changed')
    return p


def replay_checkpoint_pins(session):
    """Old grants can replay only against the pinned, archived checkpoint chain."""
    path=session.root/'stream-migration.json'
    if not path.exists(): return set()
    value=read(path)
    if (not session.worker_product or value['version']!=VERSION or value['original_contract']!=OLD_CONTRACT
            or session.binding!=dict(value['parent_binding'],execution_contract=sol_contract.CONTRACT.snapshot().model_dump(mode='json'))):
        raise ValueError('stream_migration_replay_binding')
    archive=session.root.parent/'nonstream-parent.zip'
    if digest(archive.read_bytes())!=value['archive_sha256']:
        raise ValueError('stream_migration_archive_changed')
    with zipfile.ZipFile(archive) as bundle:
        prefix='.continuation/session/'
        previous=digest(bundle.read(prefix+'guard.json'))
        if previous!=value['parent_guard_sha256']: raise ValueError('stream_migration_parent_guard')
        pins=set()
        names=sorted(n for n in bundle.namelist() if n.startswith(prefix+'checkpoints/') and n.endswith('.json'))
        for index,name in enumerate(names,1):
            raw=bundle.read(name);checkpoint=json.loads(raw)
            if (name!=prefix+f'checkpoints/{index:04d}.json' or checkpoint['previous_sha256']!=previous
                    or checkpoint['guard_sha256']!=value['parent_guard_sha256']):
                raise ValueError('stream_migration_parent_checkpoint')
            previous=digest(raw);pins.add(previous)
        if previous!=value['parent_checkpoint_sha256']: raise ValueError('stream_migration_parent_checkpoint')
    return pins
