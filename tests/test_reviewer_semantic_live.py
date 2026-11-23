"""Offline launch boundaries; no key discovery, provider IO or native certification."""
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from scripts import reviewer_semantic_live as live
from scripts.reviewer_responses_transport import digest


@pytest.fixture
def setup(monkeypatch):
    now = datetime.now(timezone.utc)
    plan = dict(version=live.batch.SEMANTIC_VERSION, budget={'max_requests': 6},
        profile={'group': 'GPT-pro', 'route': 'proxy-12000'},
        workspace={'python': str(Path(sys.executable).resolve())}, source_identity={'head': 'a'*40},
        review_principals={'primary': {'principal_id': 'root'}, 'independent': {'principal_id': 'child'}})
    approval = dict(version='reviewer-semantic-authorization-v1', plan_sha256=digest(plan),
        budget=deepcopy(plan['budget']), profile=deepcopy(plan['profile']), approved=True,
        user_evidence='OFFLINE CONSENT FIXTURE ONLY', account_group_confirmed='GPT-pro',
        price_cny_per_million={'input':'0.4', 'output':'2'}, issued_at=now.isoformat(),
        expires_at=(now+timedelta(hours=1)).isoformat())
    ci = dict(headSha='a'*40, status='completed', conclusion='success', databaseId=1,
              jobs=[{'conclusion':'success'}])
    controller = SimpleNamespace(plan=plan, fixture_only=False, status=lambda: {'phase':'ready'})
    client = SimpleNamespace(request=lambda *a: {'thread': {'id':'child','parentThreadId':'root'}})
    monkeypatch.chdir(live.batch.ROOT)
    monkeypatch.setattr(live.legacy, '_git_head', lambda: 'a'*40)
    monkeypatch.setattr(live.legacy, '_git_is_clean', lambda: True)
    monkeypatch.setattr(live.socket, 'create_connection', lambda *a, **kw: nullcontext())
    return controller, client, approval, ci


@pytest.mark.parametrize('fault', ['approval', 'budget', 'expired', 'ci', 'head', 'dirty', 'parent', 'phase', 'fixture'])
def test_rejection_before_key_and_sender(setup, monkeypatch, fault):
    controller, client, approval, ci = setup
    if fault == 'approval': approval['approved'] = False
    if fault == 'budget': approval['budget']['max_requests'] = 7
    if fault == 'expired': approval['expires_at'] = approval['issued_at']
    if fault == 'ci': ci['jobs'][0]['conclusion'] = 'failure'
    if fault == 'head': ci['headSha'] = 'b'*40
    if fault == 'dirty': monkeypatch.setattr(live.legacy, '_git_is_clean', lambda: False)
    if fault == 'parent': client.request = lambda *a: {'thread': {'id':'child','parentThreadId':'other'}}
    if fault == 'phase': controller.status = lambda: {'phase':'closed'}
    if fault == 'fixture': controller.fixture_only = True
    def forbidden(*a, **kw): pytest.fail('must reject before key/send')
    with pytest.raises(ValueError):
        live.send(controller, client, approval, ci, read_key=forbidden, sender=forbidden)


def test_one_send_uses_batch_mode_and_rechecks_after_key(setup, monkeypatch):
    controller, client, approval, ci = setup
    sent = []
    def next_call(sender, *, before_send):
        before_send()
        return sender({'fixture': True}, response_mode='nonstream-tool-v1')
    controller.send_next = next_call
    def sender(business, **kwargs):
        sent.append(kwargs)
        return {'fixture': True}
    assert live.send(controller, client, approval, ci, read_key=lambda _: 'fixture-key', sender=sender) == {'fixture':True}
    assert sent == [{'api_key':'fixture-key', 'response_mode':'nonstream-tool-v1'}]
    def changed(_):
        monkeypatch.setattr(live.legacy, '_git_is_clean', lambda: False)
        return 'fixture-key'
    with pytest.raises(ValueError):
        live.send(controller, client, approval, ci, read_key=changed, sender=sender)
    assert len(sent) == 1


def test_document_requires_exact_original_bytes(tmp_path):
    path = tmp_path / 'approval.json'
    path.write_text('{"fixture": true}', encoding='utf-8')
    pin = live.batch.sha(path)
    assert live.document(path, pin) == {'fixture':True}
    path.write_text('{"fixture": false}', encoding='utf-8')
    with pytest.raises(ValueError): live.document(path, pin)
