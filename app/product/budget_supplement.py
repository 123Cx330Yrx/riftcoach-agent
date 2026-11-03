"""Operator-supplied cumulative limits for one pinned product task only."""
from datetime import datetime, timezone
import json
import re

from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import SessionPaused

FIELDS = {'kind', 'authorized', 'authorization_sha256', 'binding', 'guard_sha256',
          'checkpoint_sha256', 'baseline', 'original_limits', 'limits', 'expires_at_utc'}
LIMITS = ('max_calls', 'total_tokens', 'execution_timeout_s')


def validate(value, session, *, installing=False):
    from app.product import sol_contract
    from app.product.session_usage import session_accounting
    if (not isinstance(value, dict) or set(value) != FIELDS
            or value['kind'] != 'product-task-budget-supplement-v1' or value['authorized'] is not True
            or not session.worker_product or session.contract_module is not sol_contract
            or value['binding'] != session.binding or value['guard_sha256'] != session.guard_sha
            or session.binding.get('execution_contract') != sol_contract.CONTRACT.snapshot().model_dump(mode='json')):
        raise ValueError('budget_supplement_binding')
    for key in ('authorization_sha256', 'guard_sha256', 'checkpoint_sha256'):
        if not isinstance(value[key], str) or not re.fullmatch('[0-9a-f]{64}', value[key]):
            raise ValueError('budget_supplement_digest')
    pins = {session.checkpoint_sha} if installing else set(session.checkpoint_pins.values())
    if value['checkpoint_sha256'] not in pins:
        raise ValueError('budget_supplement_checkpoint')
    base = {k: sol_contract.CONTRACT.descriptor()[k] for k in LIMITS}
    if (value['original_limits'] != base or set(value['limits']) != set(LIMITS)
            or any(type(value['limits'][k]) is not int or value['limits'][k] < base[k] for k in LIMITS)
            or value['limits'] == base):
        raise ValueError('budget_supplement_limits')
    expiry = datetime.fromisoformat(value['expires_at_utc'])
    if expiry.tzinfo is None:
        raise ValueError('budget_supplement_expiry')
    if installing and (datetime.now(timezone.utc) >= expiry or value['baseline'] != session_accounting(session)):
        raise ValueError('budget_supplement_baseline_or_expired')
    return value


def activate(session, supplied=None):
    """Append a pinned administrative artifact; do not alter operation ordinals."""
    path = session.root/'budget-supplement.json'
    if path.exists():
        value = validate(json.loads(path.read_bytes()), session)
        if supplied is not None and supplied != value:
            raise ValueError('budget_supplement_conflict')
        return
    if supplied is None:
        return
    if session.read_only or (session.root/'terminal.json').exists():
        raise ValueError('budget_supplement_closed')
    validate(supplied, session, installing=True)
    write_new_json(path, supplied)
    session._checkpoint('budget_supplement_activated')


def execution_limits(session):
    limits = session.contract_module.CONTRACT.descriptor()
    path = session.root/'budget-supplement.json'
    if not path.exists():
        return limits
    session.verify()
    value = validate(json.loads(path.read_bytes()), session)
    if datetime.now(timezone.utc) >= datetime.fromisoformat(value['expires_at_utc']):
        raise SessionPaused('product_budget_authorization_expired')
    return {**limits, **value['limits']}
