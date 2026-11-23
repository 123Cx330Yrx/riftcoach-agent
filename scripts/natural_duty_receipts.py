"""Read-only accounting for the six-call candidate's actual process artifacts."""
from decimal import Decimal
from dataclasses import replace
import json
from pathlib import Path

from app.evaluation.natural_duty_contract import CONTRACT, VERSION, role_for_request
from app.evaluation.golden_stream_bridge import CapacityBridgeObservation, REQUEST
from app.evaluation.role_qualification import read_role_calls
from app.runtime.reviewer_roles import role_descriptor
from scripts.natural_duty_preparation import sha, canonical, inventory


def read_calls(directory):
    directory = Path(directory)
    roles = {k: dict(v, transport_id=VERSION+':'+k) for k,v in role_descriptor().items() if k != 'revision'}
    calls = read_role_calls(directory, role_contract=roles, request_role=role_for_request,
                            observation_type=CapacityBridgeObservation)
    if len(calls) > 6:
        raise ValueError('natural_call_limit')
    expected = set()
    for call in calls:
        record = call['binding']
        ordinal = record['ordinal']
        stream = directory/record['raw_directory']/f'stream-{ordinal:03d}'
        reservation = stream/'reservation.json'
        if reservation.exists():
            value = json.loads(reservation.read_bytes())
            if any(value.get(k) != record[k] for k in ('model','thinking_profile_id')):
                raise ValueError('natural_reservation_identity')
        progress = stream/'progress.json'
        observed = CapacityBridgeObservation.model_validate_json(progress.read_bytes(), strict=True) if progress.exists() else None
        if call['response'] is not None:
            if observed is None:
                raise ValueError('natural_complete_response_missing_observation')
            if (observed.http_requests != 1 or observed.state != 'complete' or observed.close_state != 'closed'
                    or observed.terminal_ms is None or observed.eof_ms is None
                    or observed.close_ms is None or observed.input_tokens != call['response'].usage.input_tokens
                    or observed.output_tokens != call['response'].usage.output_tokens):
                raise ValueError('natural_complete_response_invalid_observation')
        if observed is not None and observed.http_requests > 1:
            raise ValueError('natural_http_retry')
        call['http_calls'] = observed.http_requests if observed else None
        expected.update(call['artifact_sha256'])
        # Failure evidence is body-free and remains bound even without a response.
        failure = stream/'failure.json'
        if failure.exists():
            expected.add(failure.relative_to(directory).as_posix())
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
    if actual != expected:
        raise ValueError('natural_transport_inventory_mismatch')
    return calls


def summarize(directory):
    calls = read_calls(directory)
    by_model = {}
    for (_,model), price in CONTRACT.pricing_profiles.items():
        selected = [c for c in calls if c['binding']['model']==model]
        known = [c for c in selected if c['usage'] is not None]
        inp = sum(c['usage']['input_tokens'] for c in known)
        out = sum(c['usage']['output_tokens'] for c in known)
        by_model[model] = dict(reserved_calls=len(selected), completed_calls=sum(c['completed'] for c in selected),
            unknown_usage_calls=len(selected)-len(known), input_tokens=inp, output_tokens=out,
            known_usage_estimated_uncached_cny=str((Decimal(inp)*price.input_cost_per_million
                                                   +Decimal(out)*price.output_cost_per_million)/1_000_000))
    unknown = sum(c['usage'] is None for c in calls)
    known_cost = sum(Decimal(v['known_usage_estimated_uncached_cny']) for v in by_model.values())
    return dict(reserved_calls=len(calls), completed_calls=sum(c['completed'] for c in calls),
        unknown_usage_calls=unknown, observed_unaccepted_calls=sum(c['usage'] is not None and not c['completed'] for c in calls),
        receiptless_calls=sum(not c['completed'] for c in calls),
        http_calls_known=sum(c['http_calls'] or 0 for c in calls), http_observation_unknown_calls=sum(c['http_calls'] is None for c in calls),
        unreserved_call_slots=6-len(calls), by_model=by_model,
        known_usage_estimated_uncached_cny=str(known_cost),
        total_estimated_uncached_cny=None if unknown else str(known_cost), billing_status='estimate_not_invoice',
        accounting_status='partial' if unknown else 'known_usage',
        production_admitted=False, semantic_approval=False)


def validate_roots(run_directory, guard):
    """Bind archived inputs to the roots emitted before the first send."""
    run_directory = Path(run_directory)
    first_raw = (run_directory/'first-request.json').read_bytes()
    auth_raw = (run_directory/'authorization.json').read_bytes()
    plan = json.loads((run_directory/'plan.json').read_bytes())
    plan_sha = plan.pop('preparation_plan_sha256')
    if (sha(first_raw)!=guard['first_request_sha256'] or sha(auth_raw)!=guard['authorization_sha256']
            or sha(canonical(plan))!=plan_sha or plan_sha!=guard['plan_sha256']
            or plan['run_id']!=guard['run_id'] or plan['first_request_sha256']!=sha(first_raw)):
        raise ValueError('natural_archived_input_root_mismatch')
    transport = run_directory/'transport'/guard['run_id']
    claim_path, request_path = transport/'call-001.json', transport/'generation/request-001.json'
    # Later broken observations must still replay as invalid_receipts. Root
    # validation does not require a successful whole-batch receipt reader.
    if claim_path.exists() and request_path.exists():
        claim, issued_raw = json.loads(claim_path.read_bytes()), request_path.read_bytes()
        issued, prepared = REQUEST.validate_json(issued_raw,strict=True), REQUEST.validate_json(first_raw,strict=True)
        if (claim.get('ordinal')!=1 or claim.get('role')!='generation'
                or claim.get('raw_directory')!='generation' or claim.get('request_sha256')!=sha(issued_raw)
                or not 0<issued.timeout_s<=prepared.timeout_s or replace(issued,timeout_s=prepared.timeout_s)!=prepared):
            raise ValueError('natural_archived_first_send_changed')


def replay(*, run_directory, operator_directory, guard_sha, closure_sha):
    """Verify original stdout trust roots; never create or repair any artifact."""
    run_directory, operator_directory = Path(run_directory).resolve(), Path(operator_directory).resolve()
    raw_guard = (operator_directory/'guard.json').read_bytes()
    raw_closure = (operator_directory/'closure.json').read_bytes()
    if sha(raw_guard)!=guard_sha or sha(raw_closure)!=closure_sha:
        raise ValueError('natural_original_stdout_root_mismatch')
    guard, closure = json.loads(raw_guard), json.loads(raw_closure)
    if (closure['guard_sha256']!=guard_sha or guard['run_directory']!=str(run_directory)
            or closure['run_id']!=guard['run_id']):
        raise ValueError('natural_closure_binding')
    actual = inventory(run_directory.rglob('*'), root=run_directory)
    if actual != closure['run_inventory']:
        raise ValueError('natural_closed_inventory_changed')
    observation_files = inventory(operator_directory.glob('observation-*.json'),root=operator_directory)
    if observation_files != closure['operator_observations']:
        raise ValueError('natural_original_observations_changed')
    validate_roots(run_directory,guard)
    result = json.loads((run_directory/'result.json').read_bytes())
    try:
        accounting = summarize(run_directory/'transport'/guard['run_id'])
    except Exception as error:
        accounting = dict(accounting_status='invalid_receipts', reserved_calls=None,
            completed_calls=None, unknown_usage_calls=None, error_type=type(error).__name__)
    if result['accounting'] != accounting:
        raise ValueError('natural_accounting_changed')
    return dict(version='natural-duty-readonly-replay-v1', run_id=guard['run_id'],
        inventory_sha256=sha(canonical(actual)), accounting=accounting, guard_sha256=guard_sha,
        closure_sha256=closure_sha, native_semantic_reviews_required=True, production_admitted=False)
