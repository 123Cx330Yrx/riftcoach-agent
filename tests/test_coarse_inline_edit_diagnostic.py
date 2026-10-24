"""Offline protocol and same-payload checks; synthetic IO never proves model quality."""
from copy import deepcopy
from functools import lru_cache
import json
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from app.evaluation import coarse_revision_editor as editor
from app.evaluation.golden_stream_bridge import transport_profile, CAPACITY_TRANSPORT_ID
from app.providers.zhipu import ZhipuProvider
from scripts import run_coarse_edit_diagnostic as base
from scripts import run_coarse_inline_edit_diagnostic as runner
from tests.test_coarse_edit_diagnostic import Host, scripted
from tests.test_coarse_revision_editor import cases, exchange, operation
from tests.test_native_editor_product_budget import offline


@lru_cache
def prepared():
    return runner.prepare(root_thread_id='synthetic-root',independent_thread_id='synthetic-independent')


def test_frozen_request_and_sdk_payload_only_inline_the_same_definition():
    _,inputs,accepted,_=cases()['claim-scope:4']
    old=editor.edit_request(inputs,accepted)
    new=editor.inline_edit_request(inputs,accepted)
    payloads=[]
    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: payloads.append(kw) or iter(()))))
    provider=ZhipuProvider.from_candidate_profile(client=client,model='glm-5.3-flash',
        profile=transport_profile(CAPACITY_TRANSPORT_ID))
    for request in (old,new):
        provider._open_stream_for_adapter(request,tool_stream=True,include_usage_tail=True)
    expected=deepcopy(payloads[0])
    schema=expected['tools'][0]['function']['parameters']
    schema['properties']['edits']['items']=schema.pop('$defs')['TextEdit']
    assert expected==payloads[1]
    assert payloads[1]['max_tokens']==32768 and payloads[1]['timeout']==300
    assert payloads[1]['extra_body']['reasoning_effort']=='high'
    plan=prepared()
    assert plan['budget']['max_calls']==1 and plan['budget']['max_tokens']==96768
    assert plan['budget']['estimated_uncached_cny']=='0.1429504'
    assert plan['sequence']==['necessary-edit'] and len(plan['cells'])==1
    assert not plan['execution_authorized'] and not plan['product_admitted']


def test_schema_constraints_equivalent_and_real_missing_field_still_rejected():
    _,inputs,accepted,_=cases()['claim-scope:4']
    old=editor.edit_request(inputs,accepted).tools[0].input_schema
    new=editor.inline_edit_request(inputs,accepted).tools[0].input_schema
    assert new['properties']['edits']['items']==old['$defs']['TextEdit']
    vectors=[({'edits':[]},True),({'edits':[operation()]},True)]
    for field in old['$defs']['TextEdit']['required']:
        op=operation();del op[field];vectors.append(({'edits':[op]},False))
    for field,value in [('source_ids',[]),('source_ids',[31,31]),('source_ids',[1]),
                        ('source_ids',['31']),('block',True),('reason',''),('before',''),
                        ('unexpected','extra'),('after','x'*24001)]:
        op=operation();op[field]=value;vectors.append(({'edits':[op]},False))
    real=json.loads((base.ROOT/'tests/fixtures/coarse_edit_missing_sources_response_20261001.json').read_bytes())
    vectors.append((real['tool_calls'][0]['arguments'],False))
    for value,valid in vectors:
        assert Draft202012Validator(old).is_valid(value)==Draft202012Validator(new).is_valid(value)==valid
    new_request=editor.inline_edit_request(inputs,accepted)
    assert editor.inspect_edit_exchange(new_request,exchange(new_request),inputs,accepted,
        inline_schema=True).journal['version']==editor.INLINE_VERSION
    with pytest.raises(ValueError,match='input_changed'):
        editor.inspect_edit_exchange(new_request,exchange(new_request),inputs,accepted)


@pytest.mark.parametrize('fault',[None,'live_missing_sources','policy','host_reject','host_unavailable','transport'])
def test_single_edit_cannot_send_fresh_or_keep_and_failure_retains_usage(tmp_path,monkeypatch,fault):
    plan=prepared();host=Host(plan,fault)
    result=base.observe(scripted(monkeypatch,fault),tmp_path,plan,event_source=host,
        adjudicate=host.adjudicate,inline_single_edit=True)
    assert result['calls']==1
    assert result['diagnostic_accepted']==(fault is None)
    assert not result['fresh_review_completed'] and not result['correct_keep_completed']
    assert not result['original15_qualified'] and not result['product_admitted']
    assert not (tmp_path/'conditional-fresh').exists() and not (tmp_path/'correct-keep').exists()
    assert json.loads((tmp_path/'result.json').read_bytes())['calls']==1
    if fault=='live_missing_sources':
        assert result['known_tokens']==11442 and result['unknown_reserved_tokens']==0
        assert result['validation_errors'][0]['loc']==('edits',0,'source_ids')


def test_inline_plan_mismatch_rejected_before_factory(tmp_path):
    plan=deepcopy(prepared());plan['sequence'].append('conditional-fresh')
    def forbidden(*a): pytest.fail('bad plan constructed a Provider')
    with pytest.raises(ValueError,match='inline_plan'):
        base.observe(forbidden,tmp_path,plan,event_source=Host(plan,None),inline_single_edit=True)


def test_prior_seal_tamper_rejected_before_preparation(monkeypatch):
    monkeypatch.setattr(base,'sha',lambda _: '0'*64)
    with pytest.raises(ValueError,match='prior_seal'):
        runner.prepare(root_thread_id='synthetic-root',independent_thread_id='synthetic-independent')


def test_new_entry_uses_ci_gate_before_credentials(tmp_path,monkeypatch):
    plan=prepared()
    monkeypatch.setattr(runner,'prepare',lambda **_:plan)
    monkeypatch.setattr(base,'ROOT',tmp_path)
    frozen=tmp_path/'frozen.json';frozen.write_text(json.dumps(plan),encoding='utf-8')
    def ci(_): raise ValueError('synthetic_ci_not_passed')
    monkeypatch.setattr(base,'verify_public_ci',ci)
    monkeypatch.setattr(base,'load_role_settings',lambda _:pytest.fail('credentials read'))
    args=SimpleNamespace(root_thread_id='synthetic-root',independent_thread_id='synthetic-independent',
        execute=True,preparation=frozen,plan_sha=base.canonical_sha(plan),env_file='unused',
        codex_executable='unused',ci_run='unused')
    with pytest.raises(ValueError,match='synthetic_ci_not_passed'): runner.run(args)
    assert not (tmp_path/'data/runs/model_comparison'/runner.EXPERIMENT).exists()
