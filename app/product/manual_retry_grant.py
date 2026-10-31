"""One task-scoped administrative retry supplement, never a global policy edit.

Only the authorized operator supplies this object to the Worker. HTTP resume
does not accept it. Committed decisions can replay after expiry without IO.
"""
from copy import deepcopy
from datetime import datetime, timezone
import re


def validate(grant, *, session, failed_sha, retries, replay=False):
    from app.product import sol_contract
    fields = {'kind', 'authorized', 'task_id', 'run_id', 'owner_id',
              'checkpoint_sha256', 'failed_result_sha256', 'original_grant_sha256',
              'prior_retries', 'additional_retries', 'limits', 'expires_at_utc'}
    if (not isinstance(grant, dict) or set(grant) != fields
            or grant['kind'] != 'product-one-extra-retry-v1'
            or grant['authorized'] is not True
            or session.contract_module is not sol_contract or not session.worker_product):
        raise ValueError('retry_grant_invalid')
    limits = sol_contract.CONTRACT.descriptor()
    if (type(grant['prior_retries']) is not int or grant['prior_retries'] != retries
            or retries != limits['transport_retries']
            or type(grant['additional_retries']) is not int or grant['additional_retries'] != 1
            or grant['limits'] != {k: limits[k] for k in
                                 ('max_calls', 'total_tokens', 'execution_timeout_s')}):
        raise ValueError('retry_grant_limits')
    for key in ('task_id', 'run_id', 'owner_id'):
        if not isinstance(grant[key], str) or not grant[key] or grant[key] != session.binding.get(key):
            raise ValueError('retry_grant_task')
    for key in ('checkpoint_sha256', 'failed_result_sha256', 'original_grant_sha256'):
        if not isinstance(grant[key], str) or not re.fullmatch('[0-9a-f]{64}', grant[key]):
            raise ValueError('retry_grant_digest')
    if grant['failed_result_sha256'] != failed_sha:
        raise ValueError('retry_grant_failure')
    pins = session.checkpoint_pins.values() if replay else (session.checkpoint_sha,)
    if grant['checkpoint_sha256'] not in pins:
        raise ValueError('retry_grant_checkpoint')
    expiry = datetime.fromisoformat(grant['expires_at_utc'])
    if expiry.tzinfo is None or (not replay and datetime.now(timezone.utc) >= expiry):
        raise ValueError('retry_grant_expired')
    return deepcopy(grant)
