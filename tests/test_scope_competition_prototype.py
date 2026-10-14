"""Authored protocol and actual control-flow tests, never model-quality evidence."""
from copy import deepcopy
from dataclasses import replace
from functools import lru_cache
import hashlib
import json

import pytest

from app.evaluation import review_bound_qualification as backend
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import validate_request, REVIEW_MODEL_TRANSPORT_ID
from app.harness.steps import RevisionRequest
from app.providers.errors import ProviderResponseError
from app.providers.models import ToolCall
from scripts import scope_competition_prototype as prototype
from tests import test_coarse_revision_editor as prior

OMITTED = '早期死亡在胜败样本间几乎相同'
EXPLICIT = '中单早期死亡在中单胜败样本间几乎相同'


@lru_cache
def source():
    return next(s for f, s in backend.frozen_cases()[0] if f['key'] == 'claim-scope:3')


def check(text=OMITTED, *, cohort='selected'):
    return dict(claim=dict(block=4, exact_text=text), candidates=[
        dict(cohort='selected', anchors=[4, 14],
             relation='supports' if cohort == 'selected' else 'refutes',
             basis='全文同指标限定用于解释省略；明确相反范围时不适用。'),
        dict(cohort='MIDDLE', anchors=[4, 14],
             relation='supports' if cohort == 'MIDDLE' else 'refutes',
             basis='本句明确组别时采用；邻接其他指标不足以覆盖同指标限定。')],
        resolution=dict(status='resolved', cohort=cohort))


def answer(*, checks=None, issues=None):
    return dict(score=84 if issues else 96, verdict='needs_revision' if issues else 'pass',
        issues=issues or [], advisories=[], issue_resolutions=[],
        scope_checks=[check()] if checks is None else checks)


def issue(block, reason):
    return dict(block=block, severity='medium', category='fact_error',
        source_ids=[31, 32], explanation=reason, suggested_correction='按原文实际组别核对来源并修正真实错误。')


def test_every_original_input_and_citation_contract_is_preserved():
    for _, req in backend.frozen_cases()[0]:
        inputs = backend.Workflow.build_inputs(req)
        base, new = backend.Workflow.make_request(inputs), prototype.review_request(inputs)
        assert new.messages[1:] == base.messages[1:]
        assert new.max_tokens == base.max_tokens == 32768
        assert new.timeout_s == base.timeout_s == 300
        assert new.temperature == base.temperature and new.top_p == base.top_p
        for name in ('Problem', 'IssueResolution'):
            assert new.tools[0].input_schema['$defs'][name] == base.tools[0].input_schema['$defs'][name]
        assert prior.size(new) <= 64000
        assert 'previous_review' not in prototype._data(new)


@pytest.mark.parametrize('kind', ['omitted', 'explicit', 'unresolved', 'all_pairs', 'future'])
def test_semantic_branches_are_expressible_not_automatically_correct(kind):
    req = source()
    text = OMITTED
    if kind == 'explicit': text = EXPLICIT
    if kind == 'all_pairs': text = '中单每场胜局的早期死亡都多于每场败局'
    if kind == 'future': text = '今后中单每场胜局的早期死亡都一定多于每场败局'
    req = replace(req, report=req.report.replace(OMITTED, text))
    if kind == 'unresolved':
        req = replace(req, report=req.report.replace('全样本口径下早期死亡胜局 2.5、败局 2.67，差异很小 [K1]；', ''))
    inputs = backend.Workflow.build_inputs(req)
    audit = check(text, cohort='selected' if kind in ('omitted', 'unresolved') else 'MIDDLE')
    if kind == 'unresolved':
        audit['resolution'] = dict(status='unresolved', cohort=None)
        for candidate in audit['candidates']:
            candidate.update(relation='does_not_resolve', basis='本合成文本移除了同指标范围说明，来源不能代替文本选择。')
    issues = [issue(6, '全样本补刀并不持平，保留该独立真错。')]
    if kind in ('explicit', 'unresolved', 'future'):
        issues.append(issue(4, '合成负例的明确错组、未解范围或未来断言仍须单独阻断。'))
    raw = compact(answer(checks=[audit], issues=issues))
    _, wire, journal = prototype.validate(raw, inputs)
    assert wire.scope_checks[0].resolution.status == audit['resolution']['status']
    assert journal['raw'] == raw
    assert not journal['semantic_approval'] and not journal['scope_audit_coverage_verified']


@pytest.mark.parametrize('fault', ['missing_field', 'unknown_cohort', 'duplicate_cohort',
    'unknown_anchor', 'boolean_anchor', 'duplicate_anchor', 'wrong_quote',
    'repeated_quote', 'duplicate_claim', 'unresolved_selected', 'unsupported_resolution', 'unknown_source'])
def test_invalid_evidence_addresses_rejected_without_repair(fault):
    req = source()
    value = answer(issues=[issue(6, 'Synthetic real error')])
    audit = value['scope_checks'][0]
    if fault == 'missing_field': value.pop('scope_checks')
    if fault == 'unknown_cohort': audit['candidates'][0]['cohort'] = 'invented'
    if fault == 'duplicate_cohort': audit['candidates'][1]['cohort'] = 'selected'
    if fault == 'unknown_anchor': audit['candidates'][0]['anchors'] = [64]
    if fault == 'boolean_anchor': audit['candidates'][0]['anchors'] = [True]
    if fault == 'duplicate_anchor': audit['candidates'][0]['anchors'] = [4, 4]
    if fault == 'wrong_quote': audit['claim']['exact_text'] = 'not in report'
    if fault == 'repeated_quote':
        req = replace(req, report=req.report.replace(OMITTED, OMITTED + '；' + OMITTED))
    if fault == 'duplicate_claim': value['scope_checks'].append(deepcopy(audit))
    if fault == 'unresolved_selected': audit['resolution']['status'] = 'unresolved'
    if fault == 'unsupported_resolution': audit['resolution']['cohort'] = 'MIDDLE'
    if fault == 'unknown_source': value['issues'][0]['source_ids'] = [9999]
    before = deepcopy(value)
    with pytest.raises(ValueError):
        prototype.validate(compact(value), backend.Workflow.build_inputs(req))
    assert value == before


def test_empty_or_plausibly_wrong_audit_does_not_prove_semantics():
    inputs = backend.Workflow.build_inputs(source())
    for checks in ([], [check(cohort='MIDDLE')]):
        # Deliberately false/omitted authored interpretation remains structurally
        # legal. A full human source review must reject it; no auto-pass oracle.
        _, _, journal = prototype.validate(compact(answer(checks=checks,
            issues=[issue(4, 'Synthetic false scope finding') , issue(6, 'True error')])), inputs)
        assert not journal['scope_audit_coverage_verified']
        assert not journal['semantic_approval']


def setup_flow(malformed=False):
    req, _, _, initial_raw = prior.cases()['claim-scope:4']
    reviews, edits = [], []
    def send(request):
        if request.metadata.get('harness_step') == 'evaluate':
            reviews.append(request)
            value = json.loads(initial_raw) if len(reviews) == 1 else answer(checks=[])
            value['scope_checks'] = [check()]
            if malformed: value.pop('scope_checks')
            ex = prior.exchange(request, name='submit_report_review')
            response = replace(ex.response, model='glm-5.3', tool_calls=(
                ToolCall(id='synthetic-review', name='submit_report_review', arguments=value),))
            return replace(ex, response=response)
        edits.append(request)
        op = {k: v for k, v in prior.operation().items() if k != 'source_ids'}
        return prior.exchange(request, edits=[op], name=prototype.editor.TOOL)
    return req, prototype.OfflineWorkflow(send), reviews, edits


def test_full_initial_edit_fresh_state_machine_preserves_audit_without_fourth_review_call():
    req, flow, reviews, edits = setup_flow()
    initial = flow.evaluate(req)
    initial_journal = deepcopy(flow.last_journal)
    draft = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report,
        req.knowledge, req.report, initial))
    assert flow.evaluate(replace(req, report=draft.report)).verdict.value == 'pass'
    assert flow.calls == 3 and len(reviews) == 2 and len(edits) == 1
    edit_input = prototype._data(edits[-1])['accepted_review']
    assert edit_input['issues'] == initial_journal['parsed_review']['issues']
    assert initial_journal['parsed_review']['scope_checks'] == [check()]
    assert 'scope_checks' not in edit_input  # Audit stays in journal, not new editing instructions.
    assert 'accepted_review' not in prototype._data(reviews[-1])
    assert reviews[0].messages[0] == reviews[-1].messages[0]
    final = prototype.review_request(flow._expected_recheck)
    assert flow.last_edit_journal['final_review_request_sha256'] == hashlib.sha256(
        validate_request(final, transport_id=REVIEW_MODEL_TRANSPORT_ID)).hexdigest()
    assert not flow.last_edit_journal['semantic_approval']
    # Request capacity only. This does not exercise a registered natural task,
    # live output length, latency, or model correctness.
    assert sum(prior.size(r) + r.max_tokens for r in [*edits, *reviews]) < 401920
    with pytest.raises(ValueError): flow.evaluate(req)
    assert flow.calls == 3


def test_bad_protocol_stops_without_reassessment():
    req, flow, reviews, edits = setup_flow(malformed=True)
    with pytest.raises(ProviderResponseError): flow.evaluate(req)
    assert flow.stopped and flow.calls == 1 and len(reviews) == 1 and not edits


def test_production_routing_still_rejects_unregistered_prototype():
    prepared = prototype.review_request(backend.Workflow.build_inputs(source()))
    with pytest.raises(ValueError, match='role_source_projection_payload_mismatch'):
        prior.role_for_request(prepared, source_projection=prior.PROJECTION)


def test_committed_offline_request_audit_reproduces():
    from pathlib import Path
    saved = json.loads(Path('data/evaluation/results/golden_scope_competition_offline_20261008.json').read_bytes())
    assert prototype.audit_requests() == saved
    assert len(saved['request_audit']) == 15 and saved['provider_calls'] == 0
    assert not saved['model_quality_proven'] and not saved['natural_task_budget_verified']
