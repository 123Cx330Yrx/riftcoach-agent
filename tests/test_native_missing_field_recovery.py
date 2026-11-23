"""Actual missing-field failures remain invalid; only explicit replacement fixes them."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.harness.steps import EvaluationRequest, KnowledgeEvidence, KnowledgeCitation, RevisionRequest
from app.providers.models import ChatResponse, TokenUsage


def fixture():
    saved = json.loads(Path('tests/fixtures/native_missing_block_reassessment.json').read_text(encoding='utf-8'))
    value = saved['evaluation_request']
    raw = value['knowledge']
    knowledge = KnowledgeEvidence(context=raw['context'], source_ids=tuple(raw['source_ids']),
        citations=tuple(KnowledgeCitation(**c) for c in raw['citations']), abstained=raw['abstained'])
    return saved, EvaluationRequest(value['player_summary'], value['deterministic_report'], knowledge,
                                    value['report'], value['user_utterance'])


def scripted_flow(replies):
    requests = []
    def send(request):
        requests.append(request)
        assert len(requests) <= len(replies), 'unexpected additional model call'
        response = ChatResponse(content=replies[len(requests)-1], provider='zhipu', model='glm-5.3-flash',
            finish_reason='stop', usage=TokenUsage(input_tokens=10, output_tokens=10))
        return Exchange(request, response, hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
    return native.NativeBusinessReviewWorkflow(send), requests


def request_body(request):
    return native.strict_json(request.messages[1].content.split('[UNTRUSTED DATA]\n')[1].split('\n[END UNTRUSTED DATA]')[0])


def test_two_actual_complete_responses_stop_without_filling_block_from_prose():
    saved, req = fixture()
    assert digest(native.build_inputs(req).data_json) == saved['source_input_sha256']
    flow, requests = scripted_flow([saved['initial_raw'], saved['recheck_raw']])
    with pytest.raises(ValueError):
        flow.evaluate(req)
    assert flow.calls == len(requests) == 2 and flow.revisions == 0
    data = request_body(requests[1])
    assert data['previous_review'] == json.loads(saved['initial_raw'])
    assert data['previous_raw_sha256'] == digest(saved['initial_raw'])
    assert data['previous_issues'][0]['block'] is None
    assert data['diagnostics'][0]['loc'] == ['issues', 0, 'block']
    assert 'block' not in json.loads(saved['recheck_raw'])['issues'][0]


def test_adding_field_is_not_exact_retention_but_explicit_replacement_is_reachable():
    saved, req = fixture()
    inputs = native.build_inputs(req)
    fixed = json.loads(saved['recheck_raw'])
    fixed['issues'][0]['block'] = 14  # Analyst-authored witness, never an output parser.
    with pytest.raises(ValueError, match='native_retained_issue_changed'):
        native.validate_legacy_v31(compact(fixed), inputs, previous_raw=saved['initial_raw'])
    fixed['issue_resolutions'][0]['disposition'] = 'replaced'
    result, _, journal = native.validate(compact(fixed), inputs, previous_raw=saved['initial_raw'])
    assert result.verdict == 'needs_revision'
    assert journal['previous_raw'] == saved['initial_raw']
    assert journal['previous_issues'][0]['block'] is None
    assert journal['parsed_review']['issues'][0]['block'] == 14
    assert journal['resolutions'][0]['disposition'] == 'replaced'
    assert result.issues[0].quote == inputs.source.blocks[13][1]


def test_actual_missing_field_can_reach_full_revision_and_recheck_with_five_call_budget():
    saved, req = fixture()
    fixed = json.loads(saved['recheck_raw'])
    fixed['issues'][0]['block'] = 14
    fixed['issue_resolutions'][0]['disposition'] = 'replaced'
    controls = json.loads(Path('data/evaluation/datasets/golden_native_scope_resolution_controls_v1.json').read_text(encoding='utf-8'))
    correct = controls['cases'][0]['report']
    final = compact(dict(score=95, verdict='pass', issues=[], issue_resolutions=[]))
    flow, requests = scripted_flow([saved['initial_raw'], compact(fixed), correct, final+'\nUnstructured ending', final])
    initial = flow.evaluate(req)
    revised = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, initial))
    accepted = flow.evaluate(replace(req, report=revised.report))
    assert accepted.verdict.value == 'pass' and flow.calls == 5 and flow.revisions == 1
    assert request_body(requests[2])['accepted_review']['issues'][0]['block'] == 14
    assert request_body(requests[2])['accepted_review']['issue_resolutions'][0]['disposition'] == 'replaced'
    assert all(size(r) <= 63936 for r in requests)
    assert sum(size(r) + r.max_tokens for r in requests) <= 401920


def test_failed_candidate_is_blocked_before_dataset_credentials_or_provider(monkeypatch):
    from types import SimpleNamespace
    from scripts import run_golden_native_review as runner
    monkeypatch.setattr(native, 'LIVE_STATUS', 'offline_missing_field_reassessment')
    monkeypatch.setattr(runner, 'prepare_scope', lambda _: pytest.fail('read after failed admission'))
    with pytest.raises(ValueError, match=native.LIVE_BLOCK_REASON):
        runner.run(SimpleNamespace(execute=True, suite='scope', case_index=1), candidate_module=native)
