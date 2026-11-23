"""Recover response envelopes without erasing receipts or buying old stages."""
import json

import pytest

from app.evaluation import sol_necessity_contract as contract
from app.evaluation.sol_natural_session import SessionPaused, tree
from scripts import reviewer_responses_nonstream as codec
from scripts.reviewer_responses_process import read_json
from tests.test_reviewer_responses_nonstream import business, response, PRIVATE, offline
from tests.test_sol_natural_candidate import application
from tests.test_sol_natural_session import session, app_for, NoSearch
from tests.test_natural_duty_candidate import run


@pytest.mark.parametrize('variant,code', [
    ('mixed', 'ok'), ('text', 'single_tool_required'),
    ('two', 'single_tool_required'), ('unknown', 'non_tool_output'),
    ('bad_json', 'tool_schema_invalid'), ('wrong_model', 'model_identity'),
    ('wrong_effort', 'reasoning_identity'), ('wrong_tool', 'tool_contract'),
])
def test_explicit_policy_consumes_only_unique_valid_tool(business, variant, code):
    value = response()
    original = value['output'][0]['arguments']
    message = dict(type='message', role='assistant', status='completed',
                   content=[dict(type='output_text', text=PRIVATE, annotations=[])])
    if variant == 'mixed': value['output'].append(message)
    elif variant == 'text': value['output'] = [message]
    elif variant == 'two': value['output'] *= 2
    elif variant == 'unknown': value['output'].append(dict(type=PRIVATE))
    elif variant == 'bad_json': value['output'][0]['arguments'] = '{'
    elif variant == 'wrong_model': value['model'] = 'different-model'
    elif variant == 'wrong_effort': value['reasoning'] = dict(effort='low')
    elif variant == 'wrong_tool': value['output'][0]['name'] = 'different-tool'
    result = codec.inspect_response(value, business, output_policy=codec.TOOL_WITH_MESSAGE)
    assert result['code'] == code
    assert result['ok'] is (code == 'ok')
    assert result['usage_state'] == 'known'
    assert PRIVATE not in json.dumps(result)
    if code == 'ok':
        assert result['public_tool_call']['arguments'] == original
        assert result['response_observation']['output_type_counts']['message'] == 1
        assert codec.inspect_response(value, business)['code'] == 'non_tool_output'


def test_owned_worker_and_application_accept_mixed_tool_without_extra_request(tmp_path):
    app, factory, flows, attempts = application(tmp_path, candidate=contract, mode='mixed_tool')
    run(app)
    assert attempts == [200] * 4
    assert flows[0].outcome == 'candidate_repaired_pass_unqualified'
    assert flows[0].send.provider.calls == 6
    assert len(list(flows[0].journal_root.glob('application.json'))) == 1
    for p in factory.providers['candidate'].reviewer.directory.glob('call-*/worker-result.json'):
        value = read_json(p)
        assert value['business_validated'] is True
        assert value['response_observation']['output_type_counts']['message'] == 1
        assert 'OFFLINE_IGNORED_MESSAGE' not in p.read_text(encoding='utf-8')


@pytest.mark.parametrize('mode', ['non_tool', 'bad_json'])
def test_format_pause_manual_resume_preserves_completed_stages_and_known_usage(tmp_path, mode):
    # First retain generation and accepted facts, then fail completion only.
    prefix = session(tmp_path, candidate=contract, max_new_models=3)
    with pytest.raises(SessionPaused), prefix:
        app, factory, calls = app_for(tmp_path, prefix, 1, candidate=contract)
        run(app)
    assert calls == [200]
    first = session(tmp_path, prefix, candidate=contract)
    with pytest.raises(SessionPaused, match='format_awaiting_manual_retry'), first:
        app, factory, calls = app_for(tmp_path, first, 2, candidate=contract, mode=mode, knowledge=NoSearch())
        run(app)
    assert calls == [200] and factory.providers['candidate'].generator.requests == []
    budget = factory.providers['candidate'].candidate_budget
    assert budget.calls == 4 and budget.reserved_tokens == 0 and budget.tokens > 0
    known = budget.tokens
    assert first.status()['format_waiting'] and not first.status()['closed']
    assert not first.status()['timeout_waiting']
    before = tree(first.transport_root)
    assert 'facts-initial.json' in tree(first.journal_root)
    assert not (first.journal_root/'outcome.json').exists()
    second = session(tmp_path, first, candidate=contract)
    with pytest.raises(SessionPaused, match='format_awaiting_manual_retry'), second:
        app, factory, calls = app_for(tmp_path, second, 3, candidate=contract, knowledge=NoSearch())
        run(app)
    assert calls == [] and tree(second.transport_root) == before
    # Explicit retry still buys just one attempt, even if that also misformats.
    third = session(tmp_path, second, candidate=contract, manual_retry=True)
    with pytest.raises(SessionPaused, match='format_awaiting_manual_retry'), third:
        app, factory, calls = app_for(tmp_path, third, 4, candidate=contract, mode=mode, knowledge=NoSearch())
        run(app)
    assert calls == [200] and factory.providers['candidate']._retries == 1
    final = session(tmp_path, third, candidate=contract, manual_retry=True)
    with final:
        app, factory, calls = app_for(tmp_path, final, 5, candidate=contract, knowledge=NoSearch())
        run(app)
        budget = factory.providers['candidate'].candidate_budget
        assert budget.calls == 8 and budget.tokens > known and budget.reserved_tokens == 0
        assert factory.providers['candidate']._logical == {'generation':2, 'review':4}
        assert factory.providers['candidate'].generator.requests == []
        assert calls == [200] * 3
        final.close(dict(outcome=read_json(final.journal_root/'outcome.json')['outcome']))
    assert all(tree(final.transport_root)[p] == pin for p, pin in before.items())
    assert len(list(final.journal_root.glob('application.json'))) == 1
    originals = tree(final.root), tree(final.transport_root), tree(final.journal_root)
    replay = session(tmp_path, final, candidate=contract, read_only=True)
    with replay:
        app, factory, calls = app_for(tmp_path, replay, 6, candidate=contract, knowledge=NoSearch())
        run(app)
        assert calls == [] and factory.providers['candidate'].generator.requests == []
    assert originals == (tree(final.root), tree(final.transport_root), tree(final.journal_root))


@pytest.mark.parametrize('mode', ['wrong_model', 'reasoning_conflict', 'two_tools', 'bad_anchor'])
def test_principled_failures_never_acquire_format_retry(tmp_path, mode):
    current = session(tmp_path, candidate=contract)
    with current:
        app, factory, calls = app_for(tmp_path, current, 1, candidate=contract, mode=mode)
        run(app)
        assert not current.status()['format_waiting']
        assert not current.status()['timeout_waiting']
        assert calls == [200] * (2 if mode == 'bad_anchor' else 1)
        assert read_json(current.journal_root/'outcome.json')['outcome'] == 'candidate_execution_failed'
