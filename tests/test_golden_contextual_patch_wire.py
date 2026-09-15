"""Exercise the real compact correction wire and canonical final checks."""
import json

import pytest

from app.evaluation import golden_contextual_correction as canonical
from app.evaluation.golden_contextual_patch_wire import apply_wire
from app.evaluation.golden_review_experiment import compact
from tests.test_golden_bounded_correction import fixture, claim, issue
from tests.test_golden_contextual_review import patch


def wire_patch(value):
    """Explicit fixture conversion; never used to accept historical live output."""
    value=json.loads(compact(value))
    def convert(row):
        scope=row['scope']
        decision='direct' if row['claim_kind']=='direct_result' else {
            'selected_sample':'sample','question_or_negation':'negated',
            'ambiguous':'ambiguous','beyond_sample':'beyond_sample'}[scope]
        if decision not in ('ambiguous','beyond_sample'):
            decision+='_'+row['status']
        return dict(decision=decision,evidence_refs=row['evidence_refs'],explanation=row['explanation'],
            quote_ref=row['quote_ref'],scope_source=row['context']['quote_ref'] if row.get('context') else None)
    value['claim_updates']=[dict(target_id=r['target_id'],**convert(r['value'])) for r in value.pop('claim_edits')]
    value['claim_additions']=[dict(audit=r['audit'],**convert(r['value'])) for r in value.pop('added_claims')]
    return value


def test_single_explicit_decision_expands_related_fields_and_preserves_source():
    inputs,first=fixture('直接结果。')
    ref=inputs.source.evidence_keys.index('facts:recent_match:00')+1
    first['audits'][0]['claims']=[claim(inputs,inputs.source.report,claim_kind='direct_result',
        scope='selected_sample',scope_anchor='样本',evidence_refs=[ref])]
    state=canonical.prepare_state(compact(first),inputs)
    value=wire_patch(patch(state))
    value['claim_updates']=[dict(target_id='c001',decision='direct_supported',
        evidence_refs=first['audits'][0]['claims'][0]['evidence_refs'],explanation='纯结果，无范围推断')]
    result,journal=apply_wire(state,compact(value),inputs=inputs)
    row=result.audits[0].claims[0]
    assert row.claim_kind=='direct_result' and row.status=='supported'
    assert row.scope is row.scope_anchor is row.context is None
    assert row.quote==inputs.source.report and journal['decisions_explicit_not_inferred']
    assert first['audits'][0]['claims'][0]['scope']=='selected_sample'
    del value['claim_updates'][0]['decision']
    with pytest.raises(ValueError):apply_wire(state,compact(value),inputs=inputs)


def test_cited_table_scope_is_located_without_model_copying_an_anchor():
    table='| 指标 | 赢局(2) | 输局(3) |\n|---|---|---|\n| 示例 | 结果 | 结果 |'
    target='该比较仅用于观察。'
    inputs,first=fixture(table+'\n\n'+target)
    first['audits'][0]['claims']=[claim(inputs,target)]
    state=canonical.prepare_state(compact(first),inputs);value=wire_patch(patch(state))
    value['claim_updates']=[dict(target_id='c001',decision='sample_supported',
        evidence_refs=first['audits'][0]['claims'][0]['evidence_refs'],
        scope_source=inputs.source.reference(table),explanation='表格明示该比较为两赢三输样本。')]
    result,journal=apply_wire(state,compact(value),inputs=inputs)
    row=result.audits[0].claims[0]
    assert row.scope_anchor=='赢局(2)' and row.context.quote==table
    assert journal['source_locations'][0]['decision']=='sample_supported'
    value['claim_updates'][0]['scope_source']=inputs.source.reference(target)
    with pytest.raises(ValueError,match='sample_source_required'):
        apply_wire(state,compact(value),inputs=inputs)


@pytest.mark.parametrize('mutation',['unknown','duplicate','shorten','contradictory','legacy'])
def test_compact_wire_preserves_identity_and_rejects_missing_or_conflicting_decisions(mutation):
    inputs,first=fixture('这四场仅作观察，不代表长期。')
    first['audits'][0]['claims']=[claim(inputs,inputs.source.report)]
    state=canonical.prepare_state(compact(first),inputs);value=wire_patch(patch(state))
    row=dict(target_id='c001',decision='sample_supported',
        evidence_refs=first['audits'][0]['claims'][0]['evidence_refs'],explanation='同一组样本')
    value['claim_updates']=[row]
    if mutation=='unknown':row['target_id']='c999'
    if mutation=='duplicate':value['claim_updates'].append(row.copy())
    if mutation=='shorten':row['quote_ref']=inputs.source.reference('这四场仅作观察')
    if mutation=='contradictory':row['decision']='direct_supported';row['scope_source']=inputs.source.reference(inputs.source.report)
    if mutation=='legacy':row['value']={}
    with pytest.raises(ValueError):apply_wire(state,compact(value),inputs=inputs)


def test_explicit_future_decision_requires_issue_and_nonpass():
    quote='所有未来输局都会更差。'
    inputs,first=fixture(quote)
    first['audits'][0]['claims']=[claim(inputs,quote)]
    state=canonical.prepare_state(compact(first),inputs);value=wire_patch(patch(state))
    value['claim_updates']=[dict(target_id='c001',decision='beyond_sample',
        evidence_refs=first['audits'][0]['claims'][0]['evidence_refs'],explanation='样本无法支持未来保证。')]
    with pytest.raises(ValueError):apply_wire(state,compact(value),inputs=inputs)
    value.update(verdict='needs_revision',score=70,added_issues=[issue(inputs,quote)])
    result,_=apply_wire(state,compact(value),inputs=inputs)
    assert result.verdict=='needs_revision' and result.audits[0].claims[0].status=='unsupported'
