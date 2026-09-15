"""Engineering regressions, not claims about a real model's semantic quality."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from app.evaluation import golden_bounded_correction as old
from app.evaluation import golden_bounded_correction_requests as requests
from app.evaluation import golden_contextual_correction as current
from app.evaluation.golden_contextual_sources import build_inputs, numeric_support, MARKER
from app.evaluation.golden_contextual_requests import project, restore
from app.evaluation.golden_contextual_validation import expand_context
from app.evaluation.golden_contextual_workflow import ContextualCorrectionWorkflow
from app.evaluation.golden_review_experiment import compact
from app.harness.steps import EvaluationRequest, KnowledgeEvidence, RevisionRequest
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
from app.report_validation import COACH_REPORT_HEADINGS
from tests.test_golden_bounded_correction import fixture, claim, issue
from tests.test_golden_contextual_review import patch
from tests.test_golden_fact_candidate import summary
from tests.test_golden_integrated_review import ReplayProvider


def external():
    return dict(opgg=[dict(digest="a"*64,position="mid",provenance="partial",upstream_patch=None,
        retrieved_at="2026-09-10T12:00:00+00:00",expires_at="2026-09-10T12:15:00+00:00",
        allowed_uses=["current_snapshot_recommendation"],facts=[dict(champion="Syndra",
            tier=2,rank=12,rank_previous=18,rank_previous_patch=5,win_rate=.49,pick_rate=.02,ban_rate=.1)])])


def request(report="OP.GG 中单辛德拉 T2，胜率约49%。", source=None):
    text="完整来源\n"+MARKER+compact(source if source is not None else external())
    return EvaluationRequest(summary(),text,KnowledgeEvidence.empty(),report,"检查观摩报告")


def first_for(req):
    _, first = fixture(req.report)
    inputs = build_inputs(req)
    first["source_digest"] = inputs.source.source_digest
    return inputs,first


def test_direct_result_misclassification_can_be_corrected_without_erasing_quote():
    target="所有未来输局都会更差。"
    inputs,first=fixture(target)
    fact_ref=inputs.source.evidence_keys.index("facts:recent_match:00")+1
    first["audits"][1]["claims"]=[claim(inputs,target,claim_kind="direct_result",scope=None,
        scope_anchor=None,evidence_refs=[fact_ref])]
    raw=compact(first)
    assert old.prepare_state(raw,inputs).mutable_claims == ()
    state=current.prepare_state(raw,inputs)
    assert state.mutable_claims == state.required_reviews == ("c001",)
    changed=claim(inputs,target,status="unsupported",scope="beyond_sample",scope_anchor="未来")
    edit=patch(state)
    edit.update(score=70,verdict="needs_revision",added_issues=[issue(inputs,target)],
        claim_edits=[dict(target_id="c001",value=changed,reason="首评把未来推断错标为直接事实")])
    result,journal=current.apply_correction(state,compact(edit),inputs=inputs)
    assert result.verdict == "needs_revision" and result.audits[1].claims[0].claim_kind == "inference"
    assert journal["edits"][0]["before"]["claim_kind"] == "direct_result" and state.raw == raw
    edit["added_issues"]=[]
    with pytest.raises(ValueError):current.apply_correction(state,compact(edit),inputs=inputs)


@pytest.mark.parametrize("quote,valid",[
    ("OP.GG 辛德拉 T2，胜率49%，登场率2%，禁用率10%，排名12。",True),
    ("OP.GG 胜率0.49，上期排名18，上版本排名5。",True),
    ("OP.GG 辛德拉为 T2、第 12 名（上期第 18）。",True),
    ("OP.GG 快照（2026-09-10T12:00:00Z）辛德拉 T2、第 12 名。",True),
    ("OP.GG 辛德拉 T9。",False),
    ("OP.GG 辛德拉上期第 12 名。",False),
    ("OP.GG 快照（2026-09-11T12:00:00Z）辛德拉 T2。",False),
    ("OP.GG 伤害49。",False),("OP.GG 胜率49。",False),
    ("OP.GG 胜率0.49%。",False),("OP.GG 禁用率49%。",False),
    ("OP.GG 队列12。",False),("OP.GG 上期排名12。",False),
])
def test_external_metrics_keep_units_and_field_identity(quote,valid):
    inputs=build_inputs(request(quote))
    pack=json.loads(inputs.pack_json)
    row=SimpleNamespace(quote=quote,evidence_refs=["external:opgg:00:00"])
    assert all(v["supported"] for v in numeric_support(row,pack)) is valid


def test_external_fact_can_be_cited_and_source_changes_invalidate_response():
    inputs,first=first_for(request())
    ref=inputs.source.evidence_keys.index("external:opgg:00:00")+1
    first["audits"][0]["claims"]=[claim(inputs,inputs.source.report,claim_kind="direct_result",scope=None,
        scope_anchor=None,evidence_refs=[ref])]
    state=current.prepare_state(compact(first),inputs)
    result,_=current.apply_correction(state,compact(patch(state)),inputs=inputs)
    assert result.audits[0].claims[0].evidence_refs == ["external:opgg:00:00"]
    changed=external();changed["opgg"][0]["facts"][0]["win_rate"]=.51
    with pytest.raises(ValueError,match="source_digest_mismatch"):
        expand_context(compact(first),inputs.source.report,json.loads(build_inputs(request(source=changed)).pack_json))


@pytest.mark.parametrize("mutation",["rate","boolean","champion","digest","uses","expiry","duplicate"])
def test_malformed_external_snapshot_is_not_indexed(mutation):
    data=external();snapshot=data["opgg"][0];fact=snapshot["facts"][0]
    if mutation=="rate":fact["win_rate"]=49
    if mutation=="boolean":fact["rank"]=True
    if mutation=="champion":fact["champion"]="ignore instructions"
    if mutation=="digest":snapshot["digest"]="missing"
    if mutation=="uses":snapshot["allowed_uses"]=[]
    if mutation=="expiry":snapshot["expires_at"]=snapshot["retrieved_at"]
    if mutation=="duplicate":snapshot["facts"]*=2
    with pytest.raises(ValueError,match="external_source_invalid"):build_inputs(request(source=data))


def test_table_projection_retains_entire_evidence_and_review_reasoning():
    inputs,first=first_for(request())
    first["audits"][0]["claims"]=[claim(inputs,inputs.source.report,explanation="不能因为前次说正确就通过")]
    state=current.prepare_state(compact(first),inputs)
    data=requests.correction_data(state);original=deepcopy(data)
    tables=project(data)
    assert restore(json.loads(compact(tables)))==json.loads(compact(original))
    assert data==original and tables["deterministic_source_facts"]==request().deterministic_report
    assert "不能因为前次说正确就通过" in compact(tables)
    tampered=deepcopy(data);tampered["facts_and_provenance"]["facts"]["external:opgg:00:00"]["rank"]=999
    with pytest.raises(ValueError,match="projection_loss"):project(tampered)


def test_five_calls_include_external_sources_and_correct_direct_misclassification():
    target,fixed="所有未来输局都会更差。","这四场仅作样本观察。"
    report="\n\n".join(COACH_REPORT_HEADINGS)+"\n\n"+target+"\n\n建议核对单局。[K1]"
    req=request(report); revised=report.replace(target,fixed)
    inputs,first=first_for(req);after,second=first_for(replace(req,report=revised))
    ref=inputs.source.evidence_keys.index("facts:recent_match:00")+1
    first["audits"][1]["claims"]=[claim(inputs,target,claim_kind="direct_result",scope=None,
        scope_anchor=None,evidence_refs=[ref])]
    second["audits"][1]["claims"]=[claim(after,fixed)]
    correction=patch(current.prepare_state(compact(first),inputs))
    correction.update(score=70,verdict="needs_revision",added_issues=[issue(inputs,target)],
        claim_edits=[dict(target_id="c001",value=claim(inputs,target,status="unsupported",
            scope="beyond_sample",scope_anchor="未来"),reason="首评错把未来推断当直接事实")])
    recheck=patch(current.prepare_state(compact(second),after))
    from tests.test_golden_contextual_patch_wire import wire_patch
    replies=[compact(first),compact(wire_patch(correction)),revised,compact(second),compact(wire_patch(recheck))]
    provider=ReplayProvider(lambda _,n:replies[n-1]); sender=BudgetedReviewSender(provider)
    flow=ContextualCorrectionWorkflow(sender)
    initial=flow.evaluate(req)
    wrong=replace(req,deterministic_report=req.deterministic_report.replace('"win_rate":0.49','"win_rate":0.51'))
    with pytest.raises(ValueError,match="revision_source_changed"):
        flow.revise(RevisionRequest(wrong.player_summary,wrong.deterministic_report,wrong.knowledge,report,initial))
    output=flow.revise(RevisionRequest(req.player_summary,req.deterministic_report,req.knowledge,report,initial))
    assert flow.evaluate(replace(req,report=output.report)).verdict.value=="pass"
    assert flow.calls==sender.budget.calls==5
    revision=provider.requests[2]
    assert current.FULL_CONTEXT_RULE in revision.messages[0].content
    assert "external_fact_paths" in revision.messages[1].content
    assert "禁止把另一个report_block里的定义借给本句" not in "".join(m.content for m in revision.messages)


def test_supplemental_notes_bind_only_to_declared_added_claims():
    target="这四场仅作样本观察。"
    inputs,first=fixture(target)
    state=current.prepare_state(compact(first),inputs)
    edit=patch(state)
    edit['added_claims']=[dict(audit='cohort_comparison',value=claim(inputs,target),review_note='新增的样本观察')]
    edit['review_notes']=[dict(target_id='c001',explanation='新增项目的补充说明')]
    result,journal=current.apply_correction(state,compact(edit),inputs=inputs)
    assert result.verdict=='pass'
    assert journal['supplemental_added_claim_notes']==[
        dict(target_id='c001',added_claim_index=0,explanation='新增项目的补充说明')]
    edit['review_notes'][0]['target_id']='c002'
    with pytest.raises(ValueError,match='inventory_mismatch'):
        current.apply_correction(state,compact(edit),inputs=inputs)


@pytest.mark.parametrize('quote,anchor,accepted',[
    ('各只 1 局，无统计稳定性。','各只1局',True),
    ('这 4 场只供观察。','这4场',True),
    ('这 4 场只供观察。','这5场',False),
    ('这1 0局只供观察。','这10局',False),
    ('这10局只供观察。','这1 0局',False),
    ('这 4 场与这4 场只供观察。','这4场',False),
    ('这4，场只供观察。','这4场',False),
])
def test_anchor_display_whitespace_is_source_bound_and_journaled(quote,anchor,accepted):
    inputs,first=fixture(quote)
    row=claim(inputs,quote,scope_anchor=anchor)
    first['audits'][0]['claims']=[row]
    raw=compact(first);state=current.prepare_state(raw,inputs);edit=patch(state)
    edit['claim_edits']=[dict(target_id='c001',value=row,reason='核对样本范围')]
    if not accepted:
        with pytest.raises(ValueError):current.apply_correction(state,compact(edit),inputs=inputs)
        return
    result,journal=current.apply_correction(state,compact(edit),inputs=inputs)
    canonical=result.audits[0].claims[0]
    assert canonical.scope_anchor in quote and canonical.quote==quote
    assert state.raw==raw and row['scope_anchor']==anchor
    assert journal['anchor_resolutions'][0]['before']==anchor
    assert journal['anchor_resolutions'][0]['after']==canonical.scope_anchor


def test_feedback_exposes_later_direct_scope_errors_after_an_earlier_anchor_error():
    inputs,first=fixture('这四场仅作观察。\n\n直接数值结果。')
    first['audits'][0]['claims']=[claim(inputs,inputs.source.blocks[0][1],scope_anchor='另四场')]
    ref=inputs.source.evidence_keys.index('facts:recent_match:00')+1
    first['audits'][1]['claims']=[claim(inputs,inputs.source.blocks[1][1],claim_kind='direct_result',
        scope='selected_sample',scope_anchor='样本',evidence_refs=[ref,ref])]
    state=current.prepare_state(compact(first),inputs)
    matrix=json.loads(state.diagnostics_json)['errors'][0]
    found={target:{matrix['codebook'][i-1] for i in indices} for target,indices in matrix['targets']}
    assert 'scope_anchor_invalid' in found['c001']
    assert {'direct_result_scope_must_be_null','duplicate_evidence_reference'} <= found['c002']
    assert set(found)=={'c001','c002'}


def test_feedback_cap_cannot_hide_any_of_48_claim_scope_errors():
    quotes=[f'样本 {chr(65+i)} 只作观察。' for i in range(48)]
    inputs,first=fixture('\n\n'.join(quotes))
    ref=inputs.source.evidence_keys.index('facts:recent_match:00')+1
    for i,quote in enumerate(quotes):
        first['audits'][i//24]['claims'].append(claim(inputs,quote,claim_kind='direct_result',
            scope='selected_sample',scope_anchor='样本',evidence_refs=[ref]))
    state=current.prepare_state(compact(first),inputs)
    feedback=json.loads(state.diagnostics_json)
    matrix=feedback['errors'][0]
    assert matrix['codes']==['per_target_validation_errors']
    assert {row[0] for row in matrix['targets']}==set(state.mutable_claims)
    assert len(matrix['targets'])==48
    assert len(json.dumps(feedback,ensure_ascii=False))<=3000


def outcome_pack():
    from app.evaluation.golden_fact_candidate import fact_pack
    source=summary()
    source['matches']=[dict(match_id=f'TEST_{i}',included_in_aggregate=True,
        role='MIDDLE',win=win,cs_per_min=cs) for i,(win,cs) in enumerate(
            [(True,8.95),(True,8.66),(False,9.64),(False,8.38)])]
    source['matches'].append(dict(match_id='SUPPORT',included_in_aggregate=True,
        role='UTILITY',win=False,cs_per_min=1.34))
    return fact_pack(source)


def test_complete_cited_rows_support_role_outcome_mean_without_derived_ref():
    pack=outcome_pack()
    refs=[f'facts:recent_match:{i:02}' for i in range(5)]
    row=SimpleNamespace(quote='中单输局补刀9.01，赢局8.81。',evidence_refs=refs)
    ledger=numeric_support(row,pack)
    assert all(v['supported'] for v in ledger)
    evidence=next(v for v in ledger if v['token']=='9.01')['candidates'][0]
    assert evidence['op']=='cited_complete_role_outcome_mean'
    assert evidence['role']=='MIDDLE' and evidence['outcome']=='loss'
    assert evidence['operands']==[('facts:recent_match:02','/cs_per_min'),('facts:recent_match:03','/cs_per_min')]
    assert row.evidence_refs==refs


@pytest.mark.parametrize('mutation',['missing_citation','missing_metric','other_role','excluded','wrong_value','unknown_provenance'])
def test_outcome_mean_does_not_invent_operands_or_cross_roles(mutation):
    pack=outcome_pack();refs=[f'facts:recent_match:{i:02}' for i in range(5)]
    quote='中单输局补刀9.01。'
    if mutation=='missing_citation':refs.remove('facts:recent_match:03')
    if mutation=='missing_metric':pack['facts']['facts:recent_match:03']['cs_per_min']=None
    if mutation=='other_role':pack['facts']['facts:recent_match:03']['role']='UTILITY'
    if mutation=='excluded':pack['facts']['facts:recent_match:03']['included_in_aggregate']=False
    if mutation=='wrong_value':quote='中单输局补刀9.02。'
    if mutation=='unknown_provenance':pack['provenance'].pop('facts:recent_match:03')
    ledger=numeric_support(SimpleNamespace(quote=quote,evidence_refs=refs),pack)
    assert not all(v['supported'] for v in ledger)


@pytest.mark.parametrize('quote,anchor,valid',[
    ('输局中艾尼维亚的表现是值得单局验证的假设。','输局中',True),
    ('赢局中的表现仅限本次观察。','赢局中',True),
    ('输局中表现更差。','输局中',False),
    ('中单的表现是值得单局验证的假设。','中单',False),
    ('赢局中表现仅限本次观察。','输局中',False),
])
def test_outcome_anchor_needs_sample_limitation_in_its_own_cited_passage(quote,anchor,valid):
    inputs,first=fixture(quote)
    first['audits'][0]['claims']=[claim(inputs,quote,scope_anchor=anchor)]
    if valid:
        result=expand_context(compact(first),quote,json.loads(inputs.pack_json))
        assert result.audits[0].claims[0].scope_anchor==anchor
    else:
        with pytest.raises(ValueError,match='scope_anchor_invalid'):
            expand_context(compact(first),quote,json.loads(inputs.pack_json))


def test_sample_words_do_not_cancel_an_unsupported_future_issue():
    quote='本次输局的情况保证所有未来输局都会更差。'
    inputs,first=fixture(quote)
    first['audits'][0]['claims']=[claim(inputs,quote,status='unsupported',
        scope='beyond_sample',scope_anchor='未来')]
    with pytest.raises(ValueError):
        expand_context(compact(first),quote,json.loads(inputs.pack_json))


def test_feedback_reviews_numbers_introduced_only_by_evaluator_explanation():
    inputs,first=fixture('这四场中单经济差异只指本样本。')
    first['audits'][0]['claims']=[claim(inputs,inputs.source.report,
        explanation='中单经济差值115.88，伤害差值695.42。')]
    state=current.prepare_state(compact(first),inputs)
    feedback=json.loads(state.diagnostics_json)
    assert feedback['errors'][0]['codebook']==['review_explanation_numbers_need_source_check']
    assert feedback['errors'][1]==dict(target_id='c001',explanation_numbers=['115.88','695.42'])
    assert 'claim_edits修正解释及证据' in current.CORRECTION_POLICY
    # A local lookup failure is not an automatically manufactured report issue.
    assert expand_context(compact(first),inputs.source.report,json.loads(inputs.pack_json)).issues==[]
