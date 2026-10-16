from dataclasses import replace
import hashlib
import json

import pytest

from app.evaluation import golden_native_block_tool_review as current
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender, Exchange
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.harness.steps import RevisionRequest
from scripts.run_golden_native_review import prepare_claim_scope
from tests.test_golden_native_partitioned_tool_review import exchange_provider, tool_response, valid_review
from tests.test_native_editor_product_budget import offline  # autouse no-network guard


def grouped(flat, count):
    return dict(score=flat['score'], verdict=flat['verdict'],
        issue_resolutions=flat['issue_resolutions'], reviews=[dict(block=b,
            issues=[{k:v for k,v in i.items() if k != 'block'} for i in flat['issues'] if i['block']==b],
            advisories=[{k:v for k,v in a.items() if k != 'block'} for a in flat['advisories'] if a['block']==b])
            for b in range(1, count+1)])


def control(index=3):
    _, req = prepare_claim_scope(index)
    inputs = current.native.build_inputs(req)
    return req, inputs, len(inputs.source.blocks)


def test_complete_inventory_preserves_issue_and_advisory_partition_and_full_sources():
    _, inputs, count = control()
    flat = valid_review(issue=True, advisory=True)
    raw = compact(grouped(flat, count))
    payload, wire, journal = current.validate(raw, inputs)
    assert len(payload.issues) == len(journal['advisories']) == 1
    assert current._flatten(wire) == flat
    assert journal['raw'] == raw and journal['structural_block_inventory_complete']
    assert not journal['semantic_coverage_proven']
    base, new = current.previous.request(inputs), current.request(inputs)
    assert base.messages[2:] == new.messages[2:]
    assert base.messages[1].content.split('[UNTRUSTED DATA]')[1] == new.messages[1].content.split('[UNTRUSTED DATA]')[1]
    assert current.digest(new.messages[0].content) == journal['policy_sha256']
    editor = current.request(inputs, accepted=wire)
    data = json.loads(editor.messages[1].content.split('[UNTRUSTED DATA]\n')[1].split('\n[END UNTRUSTED DATA]')[0])
    assert data['accepted_review']['issues'] == flat['issues']
    assert 'advisories' not in data['accepted_review'] and 'reviews' not in data['accepted_review']


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'reordered', 'invented', 'positive_explanation'])
def test_incomplete_or_expanded_inventory_is_rejected(fault):
    _, inputs, count = control()
    value = grouped(valid_review(), count)
    if fault == 'missing': value['reviews'].pop()
    elif fault == 'duplicate': value['reviews'][-1]['block'] = 1
    elif fault == 'reordered': value['reviews'].reverse()
    elif fault == 'invented': value['reviews'][-1]['block'] = count+1
    else: value['reviews'][0]['explanation'] = 'unrequested duplicate narrative'
    with pytest.raises(ValueError): current.validate(compact(value), inputs)


def test_advisory_only_report_passes_and_invalid_sources_still_reject():
    _, inputs, count = control()
    value = grouped(valid_review(advisory=True), count)
    result, _, _ = current.validate(compact(value), inputs)
    assert result.verdict == 'pass' and not result.issues
    value['reviews'][5]['advisories'][0]['source_ids'] = [999999]
    with pytest.raises(ValueError): current.validate(compact(value), inputs)


def test_nested_previous_findings_require_explicit_resolution_and_do_not_disappear():
    _, inputs, count = control()
    before = grouped(valid_review(issue=True), count)
    before['score'] = '70'
    corrected = grouped(valid_review(issue=True), count)
    with pytest.raises(ValueError, match='resolution_inventory'):
        current.validate(compact(corrected), inputs, previous_raw=compact(before))
    corrected['issue_resolutions'] = [dict(previous_id=1, disposition='replaced', final_issue=1,
        source_ids=[31], explanation='Scripted mapping, not a semantic verdict.')]
    _, _, journal = current.validate(compact(corrected), inputs, previous_raw=compact(before))
    assert journal['previous_issues'][0]['block'] == 4
    request = current.request(inputs, previous_raw=compact(before))
    assert journal['policy_sha256'] == current.digest(request.messages[0].content)


def test_full_review_edit_recheck_path_keeps_original_request_binding():
    req, inputs, count = control()
    provider = exchange_provider([tool_response(grouped(valid_review(issue=True), count)),
        req.report, tool_response(grouped(valid_review(advisory=True), count))])
    flow = current.NativeBusinessReviewWorkflow(BudgetedReviewSender(provider))
    initial = flow.evaluate(req)
    edited = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, initial))
    final = flow.evaluate(replace(req, report=edited.report))
    assert final.verdict.value == 'pass' and flow.calls == 3 and flow.revisions == 1
    assert len(flow.last_journal['parsed_review']['reviews']) == count


def test_block_tool_actual_product_five_call_budget(tmp_path, monkeypatch):
    from pathlib import Path
    from app.product.native_coach_composition import build_native_coach_application
    from app.product.recent_review import RecentReviewProductRequest
    from app.rag.hybrid import LocalHybridKnowledgeProvider
    from app.providers.models import ToolCall
    from tests import test_native_editor_product_budget as product

    class ProductProvider(product.ScriptedProductProvider):
        def chat(self, request):
            response = super().chat(request)
            if request.metadata.get('review_phase') == 'native_business_revision':
                response = replace(response, content=self.edit['report'], tool_calls=(), finish_reason='stop')
                self.last_exchange = Exchange(request, response,
                    hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
                return response
            if request.metadata.get('review_phase') in ('native_business_review', 'native_business_reassessment'):
                data = json.loads(request.messages[1].content.split('[UNTRUSTED DATA]\n')[1].split('\n[END UNTRUSTED DATA]')[0])
                flat = dict(json.loads(response.content), advisories=[])
                value = grouped(flat, len(data['source_index']['blocks']))
                response = replace(response, content=None, finish_reason='tool_calls',
                    tool_calls=(ToolCall('submission', 'submit_report_review', value),))
                self.last_exchange = Exchange(request, response,
                    hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
            return response

    monkeypatch.setattr(product, 'ScriptedProductProvider', ProductProvider)
    factory = product.Factory(recover=False, charge_ceiling=True)
    req = factory.descriptor.req
    app = build_native_coach_application(summary_builder=product.SummaryBuilder(req.player_summary),
        provider_factory=factory, knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path)
    flows = []
    def review_factory(runtime, provider):
        flow = current.NativeBusinessReviewWorkflow(product.RecordingSharedBudgetSender(provider))
        flows.append(flow)
        return flow
    monkeypatch.setattr(app._runtime._execution_factory, '_review_workflow_factory', review_factory)
    result = app.review(RecentReviewProductRequest(riot_id='DK ShowMaker#KR1', routing_region='asia', count=5, queue=420),
        run_id='offline_block_tool_budget')
    assert result.publication_status.value == 'published', result.terminal_reason
    assert len(factory.providers['offline_block_tool_budget'].requests) == flows[0].send.provider.calls == 5
    assert flows[0].send.provider.tokens <= 401920
    assert flows[0].last_journal['structural_block_inventory_complete']
