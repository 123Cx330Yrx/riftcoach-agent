"""Archive a completed but unaccepted initial stream; require manual retry.

The old result stays failed. A separate pinned recovery marker permits only
replaying that failure to a manual-decision boundary, never consuming its tool.
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

VERSION = 'product-initial-protocol-recovery-v1'
ERRORS = ['event_sequence', 'response_not_created', 'unexpected_event']


def read(path):
    return json.loads(Path(path).read_bytes())


def failure_evidence(session, ordinal):
    from app.runtime.sol_session_receipts import request_from_raw
    from scripts.prepare_reviewer_profile_screen import visible, json_value
    from scripts.reviewer_responses_transport import digest as wire_digest
    from scripts.reviewer_responses_stream import build_wire
    folder = session.root/'operations'
    intent_path = folder/f'{ordinal:04d}-intent.json'
    result_path = folder/f'{ordinal:04d}-result.json'
    intent, result = read(intent_path), read(result_path)
    value = result['value']; budget = value['budget']; call = budget['calls']
    attempt = read(folder/f'attempt-{call:03d}.json')
    request = request_from_raw(attempt['issued_raw'])
    context = request.metadata[sol_contract.CONTEXT]
    business = visible(json_value(request))
    sol_contract.validate_business(business, context)
    if (intent['kind'] != 'model' or result['intent_sha256'] != digest(intent_path.read_bytes())
            or attempt['intent_sha256'] != result['intent_sha256'] or attempt['ordinal'] != call
            or sol_contract.role_for_request(request) != 'review'
            or context['stage'] != 'initial' or context['duty'] != 'facts'
            or value.get('ok') is not False or value.get('error_code') != 'sol_call_failed'
            or 'reaped_timeout' in value or 'recoverable_format' in value
            or budget['failed'] is not True or budget['stopped'] is not True):
        raise ValueError('protocol_recovery_failure_binding')
    transport = session.transport_root/'review'/f'call-{call:03d}'
    receipt, worker, obs = (read(transport/n) for n in (
        'receipt.json', 'worker-result.json', 'observation/observation.json'))
    usage = receipt.get('usage')
    response = obs.get('response_contract') or {}
    if (receipt.get('response_mode') != sol_contract.RESPONSE_MODE
            or receipt.get('profile') != asdict(sol_contract.REVIEW_PROFILE)
            or read(transport/'request.json') != business or read(transport/'validation-context.json') != context
            or receipt.get('request_sha256') != wire_digest(business)
            or receipt.get('wire_sha256') != wire_digest(build_wire(business))
            or receipt.get('validation_context_sha256') != wire_digest(context)
            or receipt.get('ok') is not False or receipt.get('code') != 'worker_rejected'
            or receipt.get('worker_code') != ERRORS[0] or receipt.get('worker_exit') != 0
            or receipt.get('reaped') is not True or receipt.get('http_requests') != 1
            or receipt.get('usage_state') != 'known' or receipt.get('usage_conflict') is not False
            or not isinstance(usage, dict) or worker.get('usage') != usage
            or worker.get('ok') is not False or worker.get('public_tool_call') is not None
            or worker.get('business_validated') is not False or worker.get('semantic_approval') is not False
            or worker.get('code') != ERRORS[0] or worker.get('usage_conflict') is not False
            or (worker.get('stream_protocol') or {}).get('errors') != ERRORS
            or (obs.get('stream_protocol') or {}).get('errors') != ERRORS
            or obs.get('http_requests') != 1 or obs.get('response_status') != 200
            or obs.get('eof') is not True or obs.get('closed') is not True
            or obs.get('exception_type') is not None or response.get('terminal_status') != 'completed'
            or response.get('model_matches') is not True or response.get('reasoning_echo') != 'high'
            or response.get('function_calls') != 1 or response.get('output_type_counts', {}).get('other') != 0):
        raise ValueError('protocol_recovery_not_bounded_rejection')
    before = attempt['budget_before']
    if (budget['calls'] != before['calls']+1 or budget['tokens'] != before['tokens']+usage['total_tokens']
            or budget['reserved_tokens'] != before['reserved_tokens'] or budget['retries'] != before['retries']
            or budget['attempts'][:-1] != before['attempts']
            or usage['total_tokens'] != usage['input_tokens']+usage['output_tokens']):
        raise ValueError('protocol_recovery_accounting_delta')
    return dict(operation_ordinal=ordinal, failed_result_sha256=digest(result_path.read_bytes()),
        role='review', ordinal=call, issued_raw=attempt['issued_raw'],
        receipt_sha256=digest((transport/'receipt.json').read_bytes()))


def inspect_parent(parent, reference):
    parent = _safe(parent)
    if (reference['profile'] != sol_contract.WORKER_PROFILE or parent.name != reference['binding']['run_id']
            or reference['binding']['execution_contract'] != sol_contract.CONTRACT.snapshot().model_dump(mode='json')):
        raise ValueError('protocol_recovery_binding')
    with _session(parent, reference) as session:
        terminal = read(session.root/'terminal.json')
        if (terminal.get('publication_allowed') is not False or terminal.get('production_admitted') is not False
                or terminal['value']['terminal_reason'] != 'evaluation_failed'
                or terminal['value']['run_id'] != parent.name or tree(session.journal_root)
                or (session.root/'seal.json').exists() or (session.root/'protocol-recovery.json').exists()):
            raise ValueError('protocol_recovery_not_initial_rejection')
        intents = sorted((session.root/'operations').glob('*-intent.json'))
        evidence = failure_evidence(session, len(intents))
        for index, path in enumerate(intents, 1):
            value = read(path.with_name(path.name.replace('-intent','-result')))
            intent = read(path)
            if (path.name != f'{index:04d}-intent.json' or intent['ordinal'] != index
                    or value['intent_sha256'] != digest(path.read_bytes())):
                raise ValueError('protocol_recovery_prefix_binding')
            if intent['kind'] == 'model' and index != len(intents):
                from app.runtime.sol_session_receipts import request_from_raw
                prior = value['value']
                req = request_from_raw(prior.get('issued_raw') or prior['reaped_timeout']['issued_raw'])
                if sol_contract.role_for_request(req) == 'review' and not prior.get('reaped_timeout'):
                    raise ValueError('protocol_recovery_prior_review')
        segment = parent/'.continuation/segments'/str(terminal['value']['segment'])/parent.name
        receipt = read(segment/'api_run_receipt.json')
        if (receipt.get('report_available') is not False or receipt.get('terminal_reason') != 'evaluation_failed'
                or any((segment/'evaluations').glob('*.json'))
                or receipt['trace_reference']['sha256'] != digest((segment/'runtime_trace.json').read_bytes())):
            raise ValueError('protocol_recovery_publication_or_review')
        accounting = session_accounting(session)
        if accounting != reference['accounting'] or accounting['unresolved_intents']:
            raise ValueError('protocol_recovery_accounting')
        supplement = read(session.root/'budget-supplement.json') if (session.root/'budget-supplement.json').exists() else None
        if supplement is not None:
            from app.product.budget_supplement import validate
            validate(supplement, session)
        return dict(binding=reference['binding'], accounting=accounting, active_seconds=session.active_before,
                    failure=evidence, budget_supplement=supplement)


def prepare(*, parent_run, destination_root, reference):
    parent, root = _safe(parent_run), _safe(destination_root)
    child = root/parent.name
    if root.exists() or child.is_relative_to(parent) or parent.is_relative_to(child):
        raise ValueError('protocol_recovery_destination_not_new')
    state = inspect_parent(parent, reference); before = tree(parent); pins = []
    with _session(child, dict(binding=state['binding']), read_only=False, sink=pins.append) as session:
        session.active_before = state['active_seconds']
        for part in ('session/operations', 'transport'):
            for name in tree(parent/'.continuation'/part):
                target = child/'.continuation'/part/name; target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as out:out.write((parent/'.continuation'/part/name).read_bytes())
        for name in ('session/stream-migration.json', 'nonstream-parent.zip',
                     'session/zero-send-recovery.json', 'zero-send-parent.zip'):
            source = parent/'.continuation'/name
            if source.exists():
                with (child/'.continuation'/name).open('xb') as out:out.write(source.read_bytes())
        archive = child/'.continuation/protocol-parent.zip'
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
            for name in before:bundle.writestr(name, (parent/name).read_bytes())
        write_new_json(session.root/'protocol-recovery.json', dict(version=VERSION, binding=state['binding'],
            failure=state['failure'], parent_checkpoint_sha256=reference['checkpoint_sha256'],
            archive_sha256=digest(archive.read_bytes())))
        session._checkpoint('protocol_rejection_prefix_imported')
        if state['budget_supplement'] is not None:
            from app.product.budget_supplement import activate
            activate(session, dict(state['budget_supplement'], guard_sha256=session.guard_sha,
                checkpoint_sha256=session.checkpoint_sha, baseline=state['accounting']))
    if tree(parent) != before:raise ValueError('protocol_recovery_parent_changed')
    proof = dict(version=VERSION, parent_run=str(parent), destination_root=str(root), parent_inventory=before,
        parent_reference=reference, parent_state=state, binding=state['binding'], accounting=state['accounting'],
        child_checkpoint={**pins[-1], 'checkpoint':Path(pins[-1]['checkpoint']).name},
        child_inventory=tree(child), new_model_requests=0)
    path = root/'protocol-recovery-proof.json'; write_new_json(path, proof)
    return path, digest(path.read_bytes())


def retry_evidence(session):
    marker = session.root/'protocol-recovery.json'
    if not marker.exists():return None
    value = read(marker)
    if session.cursor != value['failure']['operation_ordinal']:return None
    if (not session.worker_product or value['version'] != VERSION or value['binding'] != session.binding
            or digest((session.root.parent/'protocol-parent.zip').read_bytes()) != value['archive_sha256']
            or failure_evidence(session, session.cursor) != value['failure']):
        raise ValueError('protocol_recovery_marker_changed')
    return {k:v for k,v in value['failure'].items() if k not in ('operation_ordinal','failed_result_sha256')}


def verify(path, sha, *, runs_root):
    path, root = _safe(path), _safe(runs_root)
    if digest(path.read_bytes()) != sha:raise ValueError('protocol_recovery_proof_changed')
    proof = read(path); parent = _safe(proof['parent_run']); child = root/parent.name
    if (proof['version'] != VERSION or proof['destination_root'] != str(root) or proof['new_model_requests'] != 0
            or tree(parent) != proof['parent_inventory'] or tree(child) != proof['child_inventory']):
        raise ValueError('protocol_recovery_inventory')
    state = inspect_parent(parent, proof['parent_reference'])
    if state != proof['parent_state'] or state['accounting'] != proof['accounting'] or state['binding'] != proof['binding']:
        raise ValueError('protocol_recovery_state')
    with zipfile.ZipFile(child/'.continuation/protocol-parent.zip') as bundle:
        if len(bundle.namelist()) != len(set(bundle.namelist())) or {n:digest(bundle.read(n)) for n in bundle.namelist()} != proof['parent_inventory']:
            raise ValueError('protocol_recovery_archive')
    for part in ('session/operations','transport'):
        if tree(parent/'.continuation'/part) != tree(child/'.continuation'/part):raise ValueError('protocol_recovery_prefix')
    with _session(child, dict(binding=proof['binding'], **proof['child_checkpoint'])) as session:
        if (session.root/'terminal.json').exists() or tree(session.journal_root):raise ValueError('protocol_recovery_child_closed')
        session.cursor = state['failure']['operation_ordinal']; retry_evidence(session)
        if session_accounting(session) != state['accounting'] or session.active_before < state['active_seconds']:
            raise ValueError('protocol_recovery_accounting')
        old = state['budget_supplement']; new_path = session.root/'budget-supplement.json'
        new = read(new_path) if new_path.exists() else None
        if old is None and new is not None or old is not None and (new is None or
                any(new[k] != v for k,v in old.items() if k not in {'guard_sha256','checkpoint_sha256','baseline'})):
            raise ValueError('protocol_recovery_budget_changed')
        if new is not None:
            from app.product.budget_supplement import validate
            validate(new, session)
            if new['baseline'] != state['accounting']:raise ValueError('protocol_recovery_budget_baseline')
    return proof
