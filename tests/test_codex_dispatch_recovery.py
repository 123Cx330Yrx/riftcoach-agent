"""Offline tests for the explicit single-event recovery, not review evidence."""
from copy import deepcopy
from pathlib import Path

import pytest

from scripts import codex_dispatch_recovery as recovery
from scripts import codex_review_event_source as host
from scripts import host_review_task_checkpoint as checkpoint
from scripts import review_independence_contract as contract
from tests.test_codex_review_event_source import completed_item_fixture, fetch


def recovery_fixture(tmp_path):
    f = completed_item_fixture(tmp_path)
    f.plan[contract.EVIDENCE_POLICY_FIELD] = contract.FINAL_POLICY
    material = tmp_path/'material.json'
    material.write_bytes(b'{"source":"offline"}')
    f.review.update(binding=f.bound, decision=dict(reviewer='child',
        material_sha256=recovery.sha(material.read_bytes())))
    answer = contract.canonical_json(dict(binding=f.bound, review=f.review))
    f.turn['items'][0]['text'] = answer.decode()
    f.records[2]['payload']['content'][0]['text'] = answer.decode()
    f.records[3]['payload']['item']['content'][0]['text'] = answer.decode()
    task = tmp_path/'task.json'
    task.write_text(host.review_task(f.bound, 'Read the complete offline source.'), encoding='utf-8')
    cp = tmp_path/'checkpoint.json'
    cp_sha = checkpoint.publish(cp, task, 'child')
    author = tmp_path/'author.json'
    author.write_bytes(answer)
    original = f.records[1]
    dispatches = []
    for i, kind in enumerate(('NEW_TASK','MESSAGE','NEW_TASK','MESSAGE')):
        record = deepcopy(original)
        record['payload']['id'] = f'dispatch-{i}'
        record['payload']['content'] = [dict(type='input_text', text='\n'.join([
            'Message Type: '+kind,'Task name: /root/reviewer','Sender: /root','Payload:'])+'\n'),
            dict(type='encrypted_content', encrypted_content=f'opaque-{i}')]
        dispatches.append(record)
    f.records[1:2] = dispatches
    f.save()
    f.manifest = dict(version=recovery.VERSION, evidence_policy=contract.FINAL_POLICY,
        encrypted_input_equivalence_verified=False, user_recovery_instruction='Handle this handoff.',
        event_id='child/turn-1/final-1', independent_id='child',root_id='root',
        checkpoint_path=str(cp), checkpoint_sha256=cp_sha, binding=f.bound,
        author_path=str(author), author_sha256=recovery.sha(answer),native_final_sha256=recovery.sha(answer),
        material_path=str(material),material_sha256=recovery.sha(material.read_bytes()),
        dispatches=[dict(id=r['payload']['id'],record_sha256=recovery.record_sha(r),message_type=kind)
            for r,kind in zip(dispatches,('NEW_TASK','MESSAGE','NEW_TASK','MESSAGE'))],
        final_record_sha256=recovery.record_sha(f.records[5]),
        final_membership_sha256=recovery.record_sha(f.records[6]))
    f.manifest_path = tmp_path/'recovery.json'
    f.manifest_path.write_bytes(contract.canonical_json(f.manifest))
    f.recovered = recovery.PinnedDispatchRecoveryClient(f.reader.executable,
        session_root=f.reader.session_root, recovery_path=f.manifest_path,
        recovery_sha256=recovery.sha(f.manifest_path.read_bytes()))
    f.recovered.request = f.client.request
    return f


def use_recovery(f):
    f.client.read_collaboration_dispatch = f.recovered.read_collaboration_dispatch
    return fetch(f)


def test_recovery_retains_all_dispatches_and_rechecks_native_on_replay(tmp_path):
    f = recovery_fixture(tmp_path)
    with pytest.raises(ValueError, match='dispatch_or_final_ambiguous'):
        fetch(f)  # Ordinary reader still rejects exactly the original fault.
    event = use_recovery(f)
    proof = f.recovered.read_collaboration_dispatch(f.thread,f.turn,f.turn['items'][0],allow_opaque=True)
    assert proof['raw']['dispatches'] == f.records[1:5]
    assert proof['raw']['recovery_manifest'] == f.manifest
    assert proof['task'] is None
    assert event['review'] == f.review
    assert use_recovery(f) == event
    f.records[1]['payload']['content'][1]['encrypted_content'] += 'changed'
    f.save()
    with pytest.raises(ValueError, match='dispatch_set_order_or_final_changed'):
        use_recovery(f)


@pytest.mark.parametrize('fault', ['manifest','author','material','checkpoint','task',
    'extra_dispatch','ciphertext','dispatch_author','header','after_final',
    'extra_final','extra_membership','membership_parent','api_parent','api_final','api_binding','legacy'])
def test_recovery_rejects_drift_and_cannot_relax_other_policies(tmp_path, fault):
    f = recovery_fixture(tmp_path)
    if fault == 'manifest':f.manifest_path.write_bytes(f.manifest_path.read_bytes()+b' ')
    elif fault in ('author','material','checkpoint','task'):
        field = {'author':'author_path','material':'material_path','checkpoint':'checkpoint_path'}
        path = (tmp_path/'task.json') if fault == 'task' else Path(f.manifest[field[fault]])
        path.write_bytes(path.read_bytes()+b' ')
    elif fault == 'extra_dispatch':f.records.insert(4,deepcopy(f.records[1]))
    elif fault == 'ciphertext':f.records[3]['payload']['content'][1]['encrypted_content'] = 'changed'
    elif fault == 'dispatch_author':f.records[3]['payload']['author'] = '/other'
    elif fault == 'header':f.records[3]['payload']['content'][0]['text'] += 'unbound extra text'
    elif fault == 'after_final':f.records.insert(6,f.records.pop(4))
    elif fault == 'extra_final':f.records.append(deepcopy(f.records[5]))
    elif fault == 'extra_membership':f.records.append(deepcopy(f.records[6]))
    elif fault == 'membership_parent':f.records[6]['payload']['thread_id'] = 'other'
    elif fault == 'api_parent':f.thread['parentThreadId'] = 'other'
    elif fault == 'api_final':f.turn['items'].append(deepcopy(f.turn['items'][0]))
    elif fault == 'api_binding':f.bound = dict(f.bound,report_sha256='0'*64)
    elif fault == 'legacy':f.plan[contract.EVIDENCE_POLICY_FIELD] = contract.DISPATCH_POLICY
    f.save()
    with pytest.raises(ValueError):use_recovery(f)


def test_recovery_does_not_affect_an_unregistered_single_dispatch(tmp_path):
    f = recovery_fixture(tmp_path)
    f.records[1:5] = [deepcopy(f.records[1])]
    f.records[1]['payload']['content'] = [dict(type='input_text',text='\n'.join([
        'Message Type: NEW_TASK','Task name: /root/reviewer','Sender: /root','Payload:',
        host.review_task(f.bound,'Read all sources.')]))]
    f.save()
    f.turn['id'] = 'other-turn'
    f.records[1]['payload']['internal_chat_message_metadata_passthrough']['turn_id'] = 'other-turn'
    f.records[3]['payload']['turn_id'] = 'other-turn'
    f.save()
    final = f.turn['items'][0]
    assert f.recovered.read_collaboration_dispatch(f.thread,f.turn,final,allow_opaque=True) == (
        f.reader.read_collaboration_dispatch(f.thread,f.turn,final,allow_opaque=True))


def test_unregistered_duplicate_event_is_still_rejected(tmp_path):
    f = recovery_fixture(tmp_path)
    f.manifest['event_id'] = 'child/other-turn/final-1'
    f.manifest_path.write_bytes(contract.canonical_json(f.manifest))
    f.recovered.recovery_sha256 = recovery.sha(f.manifest_path.read_bytes())
    with pytest.raises(ValueError,match='dispatch_or_final_ambiguous'):use_recovery(f)
