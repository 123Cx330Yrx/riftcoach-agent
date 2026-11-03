"""Product generation limits at construction, durable intent and transport."""
from dataclasses import replace
from io import BytesIO
import json
import time
from types import SimpleNamespace

import pytest

from app.evaluation.sol_natural_session import SessionBlocked
from app.product import sol_chat_contract, sol_contract
from app.providers.models import ChatMessage, ChatRequest, MessageRole
from tests.test_sol_product_contract import session_at
from tests.test_sol_natural_candidate import offline


CANDIDATES = (sol_contract, sol_chat_contract)


def generation(candidate, **changes):
    request = ChatRequest(
        messages=(ChatMessage(MessageRole.USER, 'offline generation'),),
        max_tokens=candidate.CONTRACT.request_policy.max_output_tokens,
        timeout_s=300, temperature=1.0, top_p=.95,
        metadata={**candidate.CONTRACT.request_policy.metadata(), 'agent_loop_iteration': 1},
    )
    return replace(request, **changes)


@pytest.mark.parametrize('candidate', CANDIDATES)
def test_product_generation_policy_and_budget_agree(candidate):
    assert candidate.CONTRACT.request_policy.max_output_tokens == 16384
    assert candidate.CONTRACT.descriptor()['max_output_tokens'] == 16384
    assert candidate.CONTRACT.descriptor()['roles']['generation']['max_output_tokens'] == 16384
    assert candidate.CONTRACT.descriptor()['request_timeout_s'] == 300


@pytest.mark.parametrize('candidate', CANDIDATES)
def test_oversized_generation_stops_before_intent_and_send_preflight(tmp_path, candidate):
    from app.evaluation.golden_stream_bridge import REQUEST

    sends, preflights = [], []
    with session_at(tmp_path, candidate=candidate) as session:
        session.before_new_model = lambda: preflights.append(True)
        request = json.loads(REQUEST.dump_json(generation(candidate, max_tokens=32768)))
        with pytest.raises(SessionBlocked, match='session_product_request_limits'):
            session.operation('model', request, lambda: sends.append(True))
        assert sends == preflights == []
        assert list((session.root / 'operations').glob('*-intent.json')) == []


@pytest.mark.parametrize('changes', [
    {'timeout_s': 301}, {'max_tokens': 0},
    {'metadata': {'agent_loop_iteration': 1}},
    {'metadata': {'harness_step': 'evaluate'}},
])
def test_invalid_new_request_never_reaches_action(tmp_path, changes):
    from app.evaluation.golden_stream_bridge import REQUEST
    with session_at(tmp_path, candidate=sol_chat_contract) as session:
        session.before_new_model = lambda: pytest.fail('preflight must not run')
        raw = json.loads(REQUEST.dump_json(generation(sol_chat_contract)))
        raw.update(changes)
        with pytest.raises(SessionBlocked, match='session_product_request_limits'):
            session.operation('model', raw, lambda: pytest.fail('must not send'))
        assert list((session.root / 'operations').glob('*-intent.json')) == []


def test_new_guard_does_not_touch_committed_operation_replay(tmp_path, monkeypatch):
    from app.evaluation.golden_stream_bridge import REQUEST
    from app.product import generation_request
    from tests.test_sol_product_contract import current_pins
    raw = json.loads(REQUEST.dump_json(generation(sol_chat_contract)))
    with session_at(tmp_path, candidate=sol_chat_contract) as session:
        assert session.operation('model', raw, lambda: {'completed': True}) == ({'completed': True}, False)
    with session_at(tmp_path, candidate=sol_chat_contract, pins=current_pins(tmp_path)) as session:
        monkeypatch.setattr(generation_request, 'validate_new_request',
                            lambda *a: pytest.fail('replay must not run new-send guard'))
        assert session.operation('model', raw, lambda: pytest.fail('replay must not send')) == ({'completed': True}, True)


def test_historical_generation_bytes_stay_readable_but_cannot_be_new_product_intent(tmp_path):
    from app.evaluation import sol_review_contract as historical
    from app.evaluation.golden_stream_bridge import REQUEST, NATURAL_FLASH_TRANSPORT_ID, validate_request
    request = generation(sol_chat_contract, max_tokens=32768,
        metadata={**historical.CONTRACT.request_policy.metadata(), 'agent_loop_iteration': 1})
    old = historical.request_bytes(request)
    assert sol_chat_contract.request_bytes(request) == old
    assert validate_request(request, transport_id=NATURAL_FLASH_TRANSPORT_ID) == old
    assert historical.CONTRACT.request_policy.max_output_tokens == 32768
    with session_at(tmp_path, candidate=sol_chat_contract) as session:
        with pytest.raises(SessionBlocked, match='session_product_request_limits'):
            session.operation('model', json.loads(REQUEST.dump_json(request)), lambda: pytest.fail('legacy send'))


@pytest.mark.parametrize('candidate', CANDIDATES)
def test_normal_product_runtime_issues_bounded_generation_and_replays_it(tmp_path, candidate):
    from app.evaluation.sol_natural_session import SessionPaused
    from tests.test_sol_product_contract import make_app, current_pins
    from tests.test_natural_duty_candidate import run
    with session_at(tmp_path, candidate=candidate, max_new_models=1) as session:
        app, factory, _, _ = make_app(tmp_path, session, candidate=candidate, mode='pass')
        with pytest.raises(SessionPaused, match='session_model_boundary'):
            run(app)
        issued = factory.providers['candidate'].generator.requests
        assert len(issued) == 1
        assert issued[0].max_tokens == 16384 and 0 < issued[0].timeout_s <= 300
    with session_at(tmp_path, candidate=candidate, max_new_models=0, pins=current_pins(tmp_path)) as session:
        app, factory, _, _ = make_app(tmp_path, session, candidate=candidate, mode='pass')
        with pytest.raises(SessionPaused, match='session_model_boundary'):
            run(app)
        assert factory.providers['candidate'].generator.requests == []


@pytest.mark.parametrize('cap', [16384, 32768])
def test_actual_flash_worker_checks_before_settings_and_sdk_wire(tmp_path, monkeypatch, cap):
    """Execute the child entry point with real OpenAI SDK and substitute HTTP."""
    import httpx
    import openai
    import sys
    from app.evaluation import golden_stream_bridge as bridge
    from app.providers import config

    wires, settings_reads = [], []
    def handler(request):
        wires.append(json.loads(request.content))
        base = dict(id='offline-stream', object='chat.completion.chunk', created=1, model='glm-5.3-flash')
        events = [
            {**base, 'choices': [{'index': 0, 'delta': {'content': 'offline report'}, 'finish_reason': None}]},
            {**base, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]},
            {**base, 'choices': [], 'usage': {'prompt_tokens': 10, 'completion_tokens': 2, 'total_tokens': 12}},
        ]
        body = ''.join('data: ' + json.dumps(event) + '\n\n' for event in events) + 'data: [DONE]\n\n'
        return httpx.Response(200, headers={'content-type': 'text/event-stream'}, content=body)

    def settings():
        settings_reads.append(True)
        return SimpleNamespace(api_key='OFFLINE_SENTINEL', model='glm-5.3-flash',
                               base_url='https://open.bigmodel.cn/api/paas/v4')
    original_client = openai.DefaultHttpxClient
    monkeypatch.setattr(openai, 'DefaultHttpxClient',
        lambda **kw: original_client(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(config, 'load_zhipu_settings', settings)
    raw = bridge.REQUEST.dump_json(generation(sol_chat_contract, max_tokens=cap))
    output = BytesIO()
    with monkeypatch.context() as io_patch:
        io_patch.setattr(sys, 'stdin', SimpleNamespace(buffer=BytesIO(raw)))
        io_patch.setattr(sys, 'stdout', SimpleNamespace(buffer=output))
        start = time.monotonic()
        if cap == 32768:
            with pytest.raises(ValueError, match='product_generation_request_budget'):
                bridge.worker(tmp_path, start, start+300, transport_id=bridge.NATURAL_FLASH_TRANSPORT_ID)
        else:
            bridge.worker(tmp_path, start, start+300, transport_id=bridge.NATURAL_FLASH_TRANSPORT_ID)
    if cap == 32768:
        assert settings_reads == wires == []
    else:
        assert len(settings_reads) == len(wires) == 1
        assert wires[0]['max_tokens'] == 16384
        assert wires[0]['model'] == 'glm-5.3-flash' and wires[0]['stream'] is True
        assert bridge.RESPONSE.validate_json(output.getvalue()).content == 'offline report'
