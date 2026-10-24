"""Source-only Host provenance checks with explicit synthetic native fixtures."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys

import pytest

from scripts import preservation_material_review as review


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('unit tests cannot reach a host or model')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)


@pytest.fixture(scope='module')
def packet():
    return review.material()


@pytest.fixture
def prepared(tmp_path, monkeypatch, packet):
    monkeypatch.setattr(review, 'material', lambda: deepcopy(packet))
    handle = review.prepare(tmp_path/'evidence', tmp_path/'answers'/'independent.json')
    path, pin = Path(handle['checkpoint']), handle['checkpoint_sha256']
    cp, _ = review.read(path,pin)
    answer = dict(kind=review.VERSION,checkpoint_sha256=pin,material_sha256=cp['material_sha256'],
        reviewer=review.REVIEWER,source_review='Synthetic source-only validation fixture.',
        cases=[dict(case_id=p['case_id'],final_facts='fixture',final_task='fixture',revision_effect='fixture',
                    basis='fixture') for p in packet['pairs']],
        protocol_review='Synthetic protocol assessment.',recommendation='unresolved',reasons=['fixture'])
    text = json.dumps(answer,ensure_ascii=True,indent=2)
    Path(cp['author_path']).write_bytes(text.encode())
    thread = dict(id=review.REVIEWER,parentThreadId=review.PARENT,
        source=dict(subAgent=dict(thread_spawn=dict(parent_thread_id=review.PARENT,agent_path='/root/host_scope_calibration'))))
    turn = dict(id='turn',status='completed',itemsView='full',error=None,items=[
        dict(type='userMessage',id='dispatch',content=[dict(type='text',text=str(path)+' '+pin)]),
        dict(type='agentMessage',id='final',phase='final_answer',text=text)])
    class Client:
        def request(self, method, params):
            if method=='thread/read':return dict(thread=thread)
            assert method=='thread/turns/list' and params['limit']==1
            return dict(data=[turn])
    return path,pin,cp,thread,turn,Client()


def test_material_keeps_full_reports_sources_and_excludes_authored_labels(packet):
    assert len(packet['pairs'])==6 and len(packet['policies']['system_policies'])==4
    assert 'evaluation' not in packet and 'expectation' not in json.dumps(packet)
    for item,row in zip(review.diagnostic.pairs.material_pairs(),packet['pairs']):
        assert row['original_report']==item.original.source.report
        assert row['final_report']==item.final.source.report
        assert row['original_source_index']==json.loads(item.original.data_json)['source_index']
    assert packet['provider_calls']==0 and packet['application_receipt'] is None


def test_native_source_only_import_requires_real_author_content(prepared):
    path,pin,cp,thread,turn,client=prepared
    result=review.import_native(client,path,pin,review.REVIEWER+'/turn/final')
    assert result['author_sha256']==result['native_final_sha256']
    assert result['independent_answer']['recommendation']=='unresolved'
    assert not result['paid_execution_authorized'] and not result['product_qualified']
    assert 'response_sha256' not in result


@pytest.mark.parametrize('mutation',['parent','turn','extra_final','file_mismatch','dispatch_pin'])
def test_wrong_native_membership_or_binding_rejects(prepared,mutation):
    path,pin,cp,thread,turn,client=prepared
    if mutation=='parent':thread['parentThreadId']='another-parent'
    elif mutation=='turn':turn['id']='older-turn'
    elif mutation=='extra_final':turn['items'].append(deepcopy(turn['items'][-1]))
    elif mutation=='file_mismatch':turn['items'][-1]['text']+=' '
    else:turn['items'][0]['content'][0]['text']=str(path)+' wrong-pin'
    with pytest.raises(ValueError,match='material_review_native'):
        review.import_native(client,path,pin,review.REVIEWER+'/turn/final')


def test_material_drift_and_duplicate_case_coverage_reject(prepared):
    path,pin,cp,thread,turn,client=prepared
    author=Path(cp['author_path'])
    answer=json.loads(author.read_bytes())
    answer['cases'][-1]=answer['cases'][0]
    author.write_bytes(json.dumps(answer).encode())
    with pytest.raises(ValueError,match='answer_binding_or_coverage'):
        review.check_answer(path,pin)
    Path(cp['material_path']).write_bytes(b'{}')
    with pytest.raises(ValueError,match='material_changed'):
        review.read(path,pin)


def test_dispatch_carries_exact_paths_and_rejects_changed_checkpoint(prepared):
    path,pin,cp,thread,turn,client=prepared
    text=review.dispatch(path,pin,sys.executable)
    assert str(review.ROOT) in text
    assert str(Path(sys.executable).resolve()) in text
    assert str(path.resolve()) in text and pin in text
    assert cp['author_path'] in text
    assert all('--section '+s in text for s in ('meta','sources','pairs','policies'))
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='checkpoint_changed'):
        review.dispatch(path,pin,sys.executable)


def test_opaque_native_route_does_not_claim_readable_input(prepared):
    path,pin,cp,thread,turn,client=prepared
    turn['items']=turn['items'][1:]
    def proof(actual_thread,actual_turn,final,**kwargs):
        assert actual_thread is thread and actual_turn is turn
        assert final is turn['items'][0]
        assert kwargs==dict(allow_opaque=True,parse_task=False)
        return dict(task=None,id='native-opaque-dispatch')
    client.read_collaboration_dispatch=proof
    result=review.import_native(client,path,pin,review.REVIEWER+'/turn/final')
    assert result['current_input_readable'] is False
    assert result['dispatch_id']=='native-opaque-dispatch'
    assert result['native_final_sha256']==result['author_sha256']
