"""Chat through existing durable product Runtime; real SDK, substitute HTTP."""
import json
import sys
from pathlib import Path

import pytest

from app.product import sol_contract as old, sol_chat_contract as chat
from app.evaluation.sol_natural_session import SessionPaused
from app.runtime.sol_natural_provider import SolReviewProvider
from app.providers.errors import ProviderResponseError
from scripts.reviewer_responses_process import run_once, read_json
from scripts.prepare_reviewer_profile_screen import visible, json_value
from tests.test_sol_product_contract import session_at, make_app, current_pins
from tests.test_natural_duty_candidate import run
from tests.test_sol_natural_candidate import offline
from tests.test_reviewer_chat_process import request
from tests.test_reviewer_chat_process import CHILD as CHAT_CHILD


@pytest.mark.parametrize('mode,calls', [('pass',4),('repair',6),('identical',6)])
def test_chat_product_uses_actual_sdk_and_publishes_exact_report(tmp_path, mode, calls):
    with session_at(tmp_path,candidate=chat) as session:
        app,factory,flows,attempts=make_app(tmp_path,session,mode=mode,candidate=chat)
        result=run(app)
        assert result.publication_status.value=='published'
        assert flows[0].send.provider.calls==calls and len(attempts)==calls-2
        folder=tmp_path/'transport/candidate/review'
        profiles = list(folder.glob('call-*/profile.json'))
        assert len(profiles) == calls - 2
        for p in profiles:
            v=json.loads(p.read_bytes());assert v['api']=='chat.completions' and v['response_mode']==chat.RESPONSE_MODE
        if mode!='pass':
            record=json.loads((tmp_path/'journal/application.json').read_bytes())
            fresh=[json.loads(p.read_bytes()) for p in (tmp_path/'journal').glob('*-fresh.json')]
            assert len(fresh)==2 and {v['report_sha256'] for v in fresh}=={record['report_sha256']}
        session.close({'completed':True})


@pytest.mark.parametrize('failure,reason', [('bad_json','session_format_awaiting_manual_retry'),
                                          ('timeout','session_timeout_awaiting_manual_retry')])
def test_failure_resume_preserves_prefix_and_requires_explicit_retry(tmp_path,failure,reason):
    with session_at(tmp_path,candidate=chat) as session:
        app,factory,_,attempts=make_app(tmp_path,session,candidate=chat,
            mode='bad_json' if failure=='bad_json' else 'pass', statuses=(524,) if failure=='timeout' else ())
        with pytest.raises(SessionPaused,match=reason):run(app)
        assert len(attempts)==1
    prefix={str(p):p.read_bytes() for p in (tmp_path/'transport').rglob('*.json')}
    with session_at(tmp_path,candidate=chat,pins=current_pins(tmp_path)) as session:
        app,_,_,attempts=make_app(tmp_path,session,candidate=chat)
        with pytest.raises(SessionPaused,match=reason):run(app)
        assert attempts==[]
    assert all(Path(name).read_bytes()==v for name,v in prefix.items())
    with session_at(tmp_path,candidate=chat,pins=current_pins(tmp_path),manual=True) as session:
        app,factory,flows,attempts=make_app(tmp_path,session,candidate=chat,mode='pass')
        result=run(app)
        assert result.publication_status.value=='published' and len(attempts)==2
        budget=flows[0].send.provider
        assert budget.calls==5 and budget.tokens>=80
        assert (budget.reserved_tokens>0)==(failure=='timeout')
        assert factory.providers['candidate'].generator.requests==[]


@pytest.mark.parametrize('mode', ['wrong_model','two_tools','bad_anchor','fresh_reject'])
def test_chat_bad_identity_or_business_never_publishes(tmp_path,mode):
    with session_at(tmp_path,candidate=chat) as session:
        app,_,_,_=make_app(tmp_path,session,candidate=chat,mode=mode)
        if mode in ('fresh_reject', 'bad_anchor'):
            reason = 'product_fresh_repair_required' if mode == 'fresh_reject' else 'product_patch_repair_required'
            with pytest.raises(SessionPaused,match=reason):run(app)
        else:
            result = run(app)
            assert result.publication_status.value == 'rejected'
        assert not (tmp_path/'journal/outcome.json').exists()


def test_chat_identity_is_separate_but_business_and_budget_are_shared(tmp_path):
    business,context=request()
    inputs=old.restore_context(context)
    req=chat.make_request(inputs,'facts')
    assert visible(json_value(req))==business
    chat.validate_business(business,req.metadata[chat.CONTEXT])
    with pytest.raises(ValueError):old.role_for_request(req)
    with pytest.raises(ValueError):chat.role_for_request(old.make_request(inputs,'facts'))
    assert chat.CONTRACT.snapshot()!=old.CONTRACT.snapshot()
    for field in ('max_calls','total_tokens','execution_timeout_s','transport_retries'):
        assert chat.CONTRACT.descriptor()[field]==old.CONTRACT.descriptor()[field]
    with pytest.raises(ValueError):chat.request_bytes(req,transport_id=old.REVIEW_TRANSPORT)
    provider=SolReviewProvider(api_key='OFFLINE_SENTINEL',directory=tmp_path/'review',task_directory=tmp_path,contract_module=chat)
    assert provider.expected_profile(req)['api']=='chat.completions'


@pytest.mark.parametrize('mode,known', [('read_error', True), ('close_error', True),
    ('known_hang', True), ('conflict_hang', False)])
def test_product_consumer_settles_failed_chat_usage_without_accepting_output(tmp_path, mode, known):
    _, context = request()
    req = chat.make_request(old.restore_context(context), 'facts')
    def sender(business, **kwargs):
        directory = kwargs['directory']
        def cancel_after_identity_checkpoint():
            observation = read_json(directory/'observation/observation.json') or {}
            identity = observation.get('response_contract') or {}
            return (directory/'blocked.json').exists() and identity.get('model_matches') is True
        return run_once(business, **kwargs,
            command=[sys.executable, '-c', 'MODE='+repr(mode)+'\n'+CHAT_CHILD],
            cancel=cancel_after_identity_checkpoint)
    provider = SolReviewProvider(api_key='OFFLINE_SENTINEL', directory=tmp_path/'review',
        task_directory=tmp_path, sender=sender, contract_module=chat)
    with pytest.raises(ProviderResponseError) as caught:
        provider.chat_at_ordinal(req, ordinal=1, role='review')
    usage = provider.failure_usage(caught.value, req)
    assert (usage is not None) is known
    if known:
        assert usage['total_tokens'] == 20
    assert not provider.retryable(caught.value, req)
    assert not provider.recoverable_format(caught.value, req)
    assert not (tmp_path/'call-result-001.json').exists()
