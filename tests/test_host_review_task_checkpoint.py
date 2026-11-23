import json

import pytest

from scripts import host_review_task_checkpoint as host
from scripts.codex_review_event_source import review_task


def checkpoint(tmp_path, key='probe:A', purpose='review'):
    bound=dict(plan_sha256='a'*64,key=key,stage='revision',response_sha256='b'*64,
        report_sha256='c'*64,request_sha256='d'*64)
    task_path=tmp_path/(key.replace(':','-')+'.task.json')
    task_path.write_text(review_task(bound,'Exact task; complete source required.'),encoding='utf-8')
    path=tmp_path/(key.replace(':','-')+'.checkpoint.json')
    sha=host.publish(path,task_path,'independent-author',purpose=purpose)
    return path,sha,bound,task_path


def test_switching_tasks_rejects_old_answer_and_preserves_current_opinion(tmp_path):
    a,asha,abound,_=checkpoint(tmp_path)
    b,bsha,bbound,_=checkpoint(tmp_path,'probe:B')
    old=json.dumps(dict(binding=abound,review=dict(binding=abound,accepted=False))).encode()
    with pytest.raises(ValueError,match='answer_binding'):host.check_answer(b,bsha,old)
    current=json.dumps(dict(binding=bbound,review=dict(binding=bbound,accepted=False,
        source_review='Independent actual rejection; routing must not repair it.'))).encode()
    assert host.check_answer(b,bsha,current)==current
    assert host.read(a,asha)[1]['binding']==abound


def test_changed_task_or_checkpoint_cannot_be_silently_recovered(tmp_path):
    p,sha,b,t=checkpoint(tmp_path)
    t.write_text(review_task(dict(b,key='different'),'Other task'),encoding='utf-8')
    with pytest.raises(ValueError,match='task_digest'):host.read(p,sha)
    p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError,match='checkpoint_digest'):host.read(p,sha)


def test_checkpoint_is_create_only_and_missing_task_has_no_fallback(tmp_path):
    p,sha,_,t=checkpoint(tmp_path)
    with pytest.raises(FileExistsError):host.publish(p,t,'independent-author')
    t.unlink()
    with pytest.raises(FileNotFoundError):host.read(p,sha)


@pytest.mark.parametrize('fault',['inner_binding','event','primary','old_schema','duplicate_json'])
def test_envelope_failures_are_not_repaired(tmp_path,fault):
    p,sha,b,_=checkpoint(tmp_path)
    answer=dict(binding=b,review=dict(binding=b))
    if fault=='inner_binding':answer['review']['binding']=dict(b,key='old')
    elif fault=='event':answer['review']['independent_source_event']={}
    elif fault=='primary':answer['review']['primary_attestation']={}
    elif fault=='old_schema':answer['review'].pop('binding')
    raw=json.dumps(answer).encode()
    if fault=='duplicate_json':raw=raw[:-1]+b',"binding":{}}'
    with pytest.raises(ValueError):host.check_answer(p,sha,raw)


def test_routing_probe_cannot_be_used_as_review_or_add_a_verdict(tmp_path):
    p,sha,b,_=checkpoint(tmp_path,purpose='routing-probe')
    answer=dict(binding=b,checkpoint_sha256=sha,probe_only=True,review_performed=False)
    raw=json.dumps(answer).encode()
    assert host.check_answer(p,sha,raw)==raw
    answer['review']={'accepted':True}
    with pytest.raises(ValueError,match='probe_answer'):host.check_answer(p,sha,json.dumps(answer).encode())
    q,qsha,_,_=checkpoint(tmp_path,'probe:B')
    answer=dict(binding=host.read(q,qsha)[0]['binding'],checkpoint_sha256=qsha,
        probe_only=True,review_performed=False)
    with pytest.raises(ValueError,match='review_envelope'):host.check_answer(q,qsha,json.dumps(answer).encode())
