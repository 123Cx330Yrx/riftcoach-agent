"""Current editor through real Agent/tools/publication; scripted models only."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from app.evaluation import review_bound_editor as editor
from app.evaluation.golden_coarse_source_projection import VERSION as PROJECTION
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.product.native_coach_composition import _build_coach_application, BOUNDARY_EXAMPLES_ASSETS
from app.product.run_receipts import FileRunReceiptStore
from app.providers.models import ChatResponse, TokenUsage, ToolCall
from app.providers.zhipu_profiles import ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.runtime.coach_contract import BOUNDARY_EXAMPLES_COACH_CONTRACT
from app.runtime.reviewer_roles import RoleRoutedProvider
from app.runtime.store import RuntimeTraceStore
from scripts.native_contract_options import body
from tests.test_coarse_revision_editor import BEFORE, AFTER, cases
from tests.test_native_editor_product_budget import ScriptedProductProvider, SummaryBuilder, offline
from tests.test_role_coach_application import run


class Responses(ScriptedProductProvider):
    review_data = staticmethod(body)

    def __init__(self, *, mode, ceiling):
        super().__init__(recover=mode == 'recovery', charge_ceiling=ceiling)
        self.req, _, _, self.initial_raw = cases()['claim-scope:4']
        self.mode = mode

    def chat(self, request):
        if 'agent_loop_iteration' in request.metadata:
            return super().chat(request)
        self.requests.append(request)
        data = self.review_data(request)
        if request.metadata['review_phase'] == 'native_business_revision':
            op = dict(block=4, before=BEFORE, after=AFTER, reason='Scripted direction correction.')
            if self.mode == 'bad_anchor':
                op['before'] = 'ABSENT ANCHOR'
            if self.mode == 'bad_fact':
                op['after'] = '辅助局视野分为999，故能保证今后获胜。'
            value = dict(edits=[op])
            name = editor.TOOL
        else:
            self.review_calls += 1
            roots = data['source_roots']
            rows = [dict(zip(roots['columns'], row)) for row in roots['roots']]
            computed = next(r['source_id'] for r in rows if r['key'] == 'derived/computed_evidence')
            value = json.loads(self.initial_raw)
            for issue in value['issues']:
                issue['source_ids'] = [computed]
            if self.review_calls == 1 and self.recover:
                value['score'] = str(value['score'])
            elif self.recover and self.review_calls == 2:
                value['issue_resolutions'] = [dict(previous_id=i, disposition='replaced',
                    final_issue=i, source_ids=[computed], explanation='Scripted type recovery.')
                    for i in range(1, len(value['issues']) + 1)]
            elif self.review_calls > 1:
                if self.mode in ('bad_fact', 'fresh_reject'):
                    value.update(score=40, verdict='fail')
                    value['issues'][0]['explanation'] = 'Scripted fresh rejection, not model detection.'
                else:
                    value = dict(score=95, verdict='pass', issues=[], advisories=[], issue_resolutions=[])
            name = 'submit_report_review'
        response = ChatResponse(content=None, tool_calls=(ToolCall('scripted', name, value),),
            provider=self.provider_name, model=self.model_name, finish_reason='tool_calls',
            usage=TokenUsage(size(request) if self.charge_ceiling else 10,
                             request.max_tokens if self.charge_ceiling else 10))
        self.last_exchange = Exchange(request, response, hashlib.sha256(validate_request(
            request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
        return response


class Factory:
    def __init__(self, mode, ceiling):
        self.mode, self.ceiling = mode, ceiling
        self.descriptor = self.make()
        self.created = {}

    def make(self):
        generator = Responses(mode=self.mode, ceiling=self.ceiling)
        reviewer = Responses(mode=self.mode, ceiling=self.ceiling)
        reviewer.model_name = 'glm-5.3'
        reviewer.thinking_profile_id = ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE.profile_id
        return RoleRoutedProvider(generator, reviewer, source_projection=PROJECTION)

    def __call__(self, run_id):
        self.created[run_id] = self.make()
        return self.created[run_id]


def application(tmp_path, mode, ceiling):
    factory = Factory(mode, ceiling)
    flows = []

    class Capture(editor.ReviewBoundRevisionWorkflow):
        def __init__(self, sender):
            super().__init__(sender)
            flows.append(self)

    app = _build_coach_application(contract=BOUNDARY_EXAMPLES_COACH_CONTRACT,
        assets=BOUNDARY_EXAMPLES_ASSETS, workflow_type=Capture,
        summary_builder=SummaryBuilder(deepcopy(factory.descriptor.generator.req.player_summary)),
        provider_factory=factory,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(Path('data/rag_docs')),
        runs_root=tmp_path)
    return app, factory, flows


@pytest.mark.parametrize('mode,ceiling', [('success', False), ('success', True),
    ('bad_anchor', False), ('bad_fact', False), ('fresh_reject', False), ('recovery', False)])
def test_current_editor_actual_agent_tools_and_publication(tmp_path, mode, ceiling):
    app, factory, flows = application(tmp_path, mode, ceiling)
    result = run(app, 'review_bound_coach')
    router, flow = factory.created['review_bound_coach'], flows[0]
    budget = flow.send.provider
    success = mode == 'success'
    assert result.publication_status.value == ('published' if success else 'rejected'), result
    expected = ['generation', 'generation', 'review']
    if mode == 'recovery':
        expected += ['review', 'revision']
    else:
        expected += ['revision'] + ([] if mode == 'bad_anchor' else ['review'])
    assert [r['role'] for r in router.attempts] == expected
    assert budget.calls == len(router.attempts) == len(expected)
    assert [r['ordinal'] for r in router.attempts] == list(range(1, len(expected) + 1))
    assert any(m.role.value == 'tool' for m in router.generator.requests[1].messages)
    assert [r.metadata.get('agent_loop_iteration') for r in router.generator.requests[:2]] == [1, 2]
    tool_data = [json.loads(m.content)['data'] for m in router.generator.requests[1].messages if m.role.value == 'tool']
    assert len(tool_data) == 5 and all(p['chunks'] for p in tool_data)
    requests = router.generator.requests + router.reviewer.requests
    assert budget.tokens == sum(r['input_tokens'] + r['output_tokens'] for r in router.attempts)
    if ceiling:
        assert budget.tokens == sum(size(r) + r.max_tokens for r in requests) <= 401920
    trace = RuntimeTraceStore(tmp_path, 'review_bound_coach').read_trace(result.trace_reference)
    receipt = FileRunReceiptStore(tmp_path).read_receipt('review_bound_coach')
    assert trace.usage.provider_calls_attempted == trace.usage.provider_responses_observed == len(expected)
    assert trace.usage.input_tokens + trace.usage.output_tokens == budget.tokens
    assert receipt.report_available is success
    assert receipt.publication_status == result.publication_status
    assert receipt.trace_reference == result.trace_reference
    final_artifacts = [a for a in trace.artifacts if a.kind == 'final_report']
    final_path = tmp_path/'review_bound_coach'/'output/final_report.md'
    if not success:
        assert result.output is None or result.output.report is None
        assert not final_path.exists()
        assert final_artifacts == []
    if mode == 'bad_anchor':
        assert flow.stopped and flow.last_edit_journal is None
        return
    journal = flow.last_edit_journal
    assert journal and not journal['semantic_approval'] and not journal['production_admitted']
    assert journal['original_report'] == router.generator.req.report
    after = '辅助局视野分为999，故能保证今后获胜。' if mode == 'bad_fact' else AFTER
    exact = router.generator.req.report.replace(BEFORE, after)
    assert journal['assembled_report'] == exact
    assert flow._expected_recheck.source.report == exact
    if mode == 'recovery':
        assert flow.stopped and budget.stopped and budget.last_exchange is None
        assert len(router.reviewer.requests) == 2  # No sixth request or publication.
        return
    final = body(router.reviewer.requests[-1])
    initial = body(router.reviewer.requests[0])
    assert not {'previous_review', 'previous_issues', 'accepted_review'} & final.keys()
    assert final['knowledge'] == initial['knowledge']
    assert final['knowledge']['retrievals'] == [dict(provider=p['provider'],
        retrieved_at=p['retrieved_at'], chunk_ids=[c['chunk_id'] for c in p['chunks']]) for p in tool_data]
    assert router.reviewer.requests[-1].messages == editor.Current.make_request(flow._expected_recheck).messages
    if success:
        assert result.output.report == exact
        assert final_path.read_bytes() == exact.encode('utf-8')
        assert len(final_artifacts) == 1
        assert final_artifacts[0].relative_path == 'output/final_report.md'
        assert final_artifacts[0].sha256 == hashlib.sha256(final_path.read_bytes()).hexdigest()
        print(dict(evidence='scripted_application_not_live_quality', ceiling=ceiling,
            calls=budget.calls, tokens=budget.tokens,
            full_reservation=sum(size(r) + r.max_tokens for r in requests)))
    else:
        assert flow.stopped
