"""Stream-only product failure handling, with owned subprocesses and zero network."""
import json

import pytest

from app.product import sol_contract as product
from app.runtime.observed_provider import ObservedLLMProvider
from app.product.sol_workflow import ProductBudget
from app.evaluation.sol_natural_session import SessionPaused
from scripts import review_duty_composition as duty
from scripts import reviewer_responses_process as process
from scripts.prepare_reviewer_profile_screen import visible, json_value
from tests.test_sol_natural_candidate import application, offline
from tests.test_sol_product_contract import session_at, current_pins
from tests.test_natural_duty_candidate import Responses
from tests.test_runtime_execution_factory_combined import _NoopObserver
from tests.test_reviewer_responses_supervisor import worker, USAGE


def request():
    return product.make_request(duty.TimedDocumentWorkflow.build_inputs(Responses().req), 'facts')


@pytest.mark.parametrize('mode,errors', [
    ('protocol_unknown_preamble', ['event_sequence', 'response_not_created', 'unexpected_event']),
    ('anonymous_rejected', ['response_identity', 'event_sequence']),
])
def test_sql_recovery_stream_fixtures_reject_one_owned_call_with_known_usage(tmp_path, mode, errors):
    """Check both SQL parent-failure producers without needing a database.

    The anonymous case intentionally emulates the old receiver in its child;
    current acceptance of empty prefixes and metadata heartbeats is separate.
    """
    from app.providers.errors import ProviderResponseError

    factory, attempts = application(tmp_path, mode=mode, candidate=product, factory_only=True)
    provider = factory('candidate')
    with pytest.raises(ProviderResponseError, match='sol_call_failed'):
        provider.chat(request())
    assert attempts == [200] and provider.generator.requests == []
    call = provider.reviewer.directory/'call-001'
    receipt = json.loads((call/'receipt.json').read_bytes())
    result = json.loads((call/'worker-result.json').read_bytes())
    observation = json.loads((call/'observation/observation.json').read_bytes())
    assert receipt['code'] == 'worker_rejected' and receipt['reaped']
    assert receipt['http_requests'] == 1 and receipt['usage_state'] == 'known'
    assert receipt['usage']['total_tokens'] == 20
    assert result['stream_protocol']['errors'] == errors
    assert observation['stream_protocol'] == result['stream_protocol']
    assert observation['eof'] and observation['closed']
    assert result['public_tool_call'] is None and not result['business_validated']


@pytest.mark.parametrize('mode', ['bad_json', 'non_tool'])
def test_format_pause_does_not_resend_without_explicit_retry(tmp_path, mode):
    req = request()
    for ordinal, manual in enumerate([False, False, True]):
        with session_at(tmp_path, manual=manual, pins=current_pins(tmp_path) if ordinal else None) as session:
            factory, attempts = application(tmp_path, mode=mode, candidate=product, factory_only=True)
            provider = ObservedLLMProvider(delegate=factory('candidate'), observer=_NoopObserver(),
                request_identity=product.request_identity)
            budget = ProductBudget(provider, session=session, coach_contract=product.CONTRACT)
            with pytest.raises(SessionPaused, match='format_awaiting_manual_retry'):
                budget.chat(req)
            assert attempts == ([] if ordinal == 1 else [200])
            assert budget.tokens == (20 if ordinal < 2 else 40)
            assert budget.reserved_tokens == 0
            assert session.status()['format_waiting']


@pytest.mark.parametrize('scenario', ['before', 'during_unknown', 'during_known', 'deadline_known'])
def test_product_mode_owned_process_cancellation_and_deadline(tmp_path, scenario):
    req = request()
    root = tmp_path/'call'
    body = "observed('waiting_for_raw_bytes')\n"
    if scenario.endswith('known') and scenario != 'during_unknown':
        body += "write('usage.json', usage)\n"
    body += "write('ready.json', True)\ntime.sleep(60)"
    receipt = process.run_once(visible(json_value(req)), profile=product.REVIEW_PROFILE,
        api_key='OFFLINE_SENTINEL', directory=root, response_mode=product.RESPONSE_MODE,
        validation_context=req.metadata[product.CONTEXT], command=worker(body),
        timeout_s=2 if scenario == 'deadline_known' else 10,
        cancel=lambda: scenario == 'before' or scenario.startswith('during') and (root/'ready.json').exists())
    assert receipt['reaped'] and not receipt['ok']
    assert receipt['code'] == ('deadline_exceeded' if scenario == 'deadline_known' else 'cancelled')
    assert receipt['http_requests'] == (0 if scenario == 'before' else 1)
    assert receipt['usage'] == (USAGE if scenario in ('during_known', 'deadline_known') else None)
    assert json.loads((root/'receipt.json').read_text()) == receipt
