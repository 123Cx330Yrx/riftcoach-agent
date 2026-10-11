"""Actual serialized phase policy and immutable real-failure regressions."""
import json
import socket
from dataclasses import replace

import pytest

from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_review_experiment import digest
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from scripts.native_contract_options import editor_request, validate_editor
from scripts.run_native_editor_diagnostic import ROOT, prepare
from tests.test_golden_integrated_review import ReplayProvider
from scripts import run_native_editor_diagnostic as runner


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket,'connect',lambda *a,**k:pytest.fail('offline regression reached network'))


def real_failure():
    return json.loads((ROOT/'data/evaluation/results/golden_native_editor_result_685993d.json').read_text(encoding='utf-8'))


def test_all_applicable_domain_policies_reach_serialized_editor_and_both_reviews():
    case,req,edit=prepare(1)
    inputs=native.build_inputs(req)
    final=native.request(native.build_inputs(replace(req,report=real_failure()['actual_report'])))
    first=native.request(inputs)
    for message in (first.messages[0].content,edit.messages[0].content,final.messages[0].content):
        for rule in native.SEMANTIC_POLICIES.values():
            assert message.count(rule)==1
    # This refactor must not silently change already-qualified native requests.
    assert digest(native.POLICY)=='d2400441cb06b8c8f31b0085a8e0d7ad04063cf9b0d80efee0c2cc49663f8e25'
    assert '只输出score、verdict、issues、issue_resolutions四项' not in edit.messages[0].content
    assert 'issue_resolutions' not in edit.response_contract.schema_dict()['properties']
    historical=real_failure()
    actual=historical['actual_request']
    new=json.loads(validate_request(edit,transport_id=CAPACITY_TRANSPORT_ID))
    # Only system policy and budget-owned metadata/timeout differ: full inputs
    # and output schema were not simplified to make the new candidate pass.
    assert new['messages'][1:]==actual['messages'][1:]
    assert new['response_contract']==actual['response_contract']
    assert new['messages'][0]['content']!=actual['messages'][0]['content']


def test_actual_failed_editor_remains_valid_structure_but_stops_before_recheck(tmp_path):
    failure=real_failure()
    case,req,_=prepare(1)
    wire,_=validate_editor(failure['response']['content'],native.build_inputs(req),case['proposed_review_raw'])
    assert [d.disposition for d in wire.decisions]==['apply','apply']
    assert wire.report==failure['actual_report']
    assert not failure['semantic_approval'] and not failure['independent_review']['accepted']
    runner.write_new_json(tmp_path/'plan.json',dict(started_at_unix=1000))
    result=runner.observe(ReplayProvider(lambda *_:failure['response']['content']),tmp_path,case,req,
        phase='edit',clock=lambda:1010)
    assert result['stop_reason']=='editor_disposition_mismatch'
    assert result['completed_calls']==1 and not result['protocol_success']
    assert not (tmp_path/'recheck').exists()
