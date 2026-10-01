"""Reproducible real-failure replay, provenance checks and bounded offline witness."""
import json
from types import SimpleNamespace
import hashlib
from pathlib import Path

import pytest

from scripts import check_native_claim_scope as controls
from scripts import run_golden_native_review as runner


def test_committed_sources_replay_failure_and_bounded_workflow_without_live_runs():
    result = controls.audit()
    assert len(result['shapes']) == 7
    assert result['original_real_semantic_failure_preserved']['final_verdict'] == 'needs_revision'
    assert result['original_real_semantic_failure_preserved']['calls'] == 3
    assert len(result['scripted_five_call_path']) == 5
    assert result['full_output_reservation'] <= result['total_budget']
    assert result['provider_calls'] == 0
    assert not result['semantic_approval'] and not result['production_admitted']


def test_numeric_failure_survives_disposition_fix_and_explicit_corrected_path_is_bounded():
    result = controls.audit_reassessment()
    assert result['disposition_only_counterexample'] == dict(protocol_valid=True, numeric_statement_correct=False)
    assert result['vision_from_original_rows']['cohort_mean'] == '33.75'
    assert result['vision_from_original_rows']['win_mean'] == result['vision_from_original_rows']['cohort_median'] == '33.5'
    assert [c['expected_report'] for c in result['full_report_controls']] == ['accept', 'reject', 'reject', 'reject']
    assert len(result['scripted_five_call_path']) == 5
    assert result['full_output_reservation'] <= 401920
    assert not result['semantic_fix_proven'] and result['provider_calls'] == 0


def test_real_universal_case_reassessment_failure_is_preserved_as_contract_failure():
    from app.evaluation import golden_native_issues_review as native
    from app.evaluation.golden_integrated_runtime import Exchange
    from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
    from app.providers.models import ChatResponse, TokenUsage

    data, requests, _ = controls.load_controls()
    fixture = json.loads(Path('tests/fixtures/native_claim_scope_retained_changed.json').read_text(encoding='utf-8'))
    assert fixture['case_id'] == data['cases'][3]['id']
    issued = []

    def send(request):
        issued.append(request)
        saved = fixture['responses'][len(issued) - 1]
        return Exchange(request, ChatResponse(content=saved['content'], provider='zhipu',
            model='glm-5.3-flash', finish_reason=saved['finish_reason'],
            usage=TokenUsage(**saved['usage'])),
            hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())

    flow = native.NativeBusinessReviewWorkflow(send)
    with pytest.raises(ValueError, match='disposition'):
        flow.evaluate(requests[3])
    assert len(issued) == 2 and flow.calls == 2 and flow.revisions == 0
    assert flow.last_feedback['errors'][0]['loc'] == ('issue_resolutions', 0, 'disposition')
    with pytest.raises(ValueError, match='native_retained_issue_changed'):
        native.validate_legacy_v31(fixture['responses'][1]['content'], native.build_inputs(requests[3]),
            previous_raw=fixture['responses'][0]['content'])


@pytest.mark.parametrize('mutation, error', [
    ('origin', 'claim_scope_origin_changed'),
    ('report', 'claim_scope_report_changed'),
    ('source', 'claim_scope_sources_changed'),
])
def test_altered_evidence_is_rejected_before_building_requests(tmp_path, monkeypatch, mutation, error):
    data = json.loads(controls.DATASET.read_text(encoding='utf-8'))
    if mutation == 'origin':
        data['origin_result_sha256'] = '0' * 64
    elif mutation == 'report':
        data['cases'][0]['report'] += '\nAn unreviewed conclusion.'
    else:
        data['source_files'][0]['sha256'] = '0' * 64
    path = tmp_path / 'changed.json'
    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(controls, 'DATASET', path)
    with pytest.raises(ValueError, match=error):
        controls.load_controls()


def test_claim_scope_preview_and_execution_gate_precede_external_io(monkeypatch):
    from app.evaluation import golden_native_issues_review as native
    from app.harness.steps import EvaluationVerdict
    from tests.test_golden_native_runner import forbidden, isolate_external
    isolate_external(monkeypatch)
    monkeypatch.setattr(runner, 'verify_public_ci', forbidden)
    data, requests, _ = controls.load_controls()
    for index, (expected, request) in enumerate(zip(data['cases'], requests, strict=True), 1):
        case, loaded = runner.prepare_claim_scope(index)
        assert case == expected and loaded == request
        args = SimpleNamespace(execute=False, suite='claim-scope', case_index=index)
        plan = runner.run(args, candidate_module=native)
        assert plan['selected_cases'] == [case['id']]
        assert plan['suite'] == 'claim-scope' and plan['max_calls_per_report'] == 5
        assert not plan['semantic_approval']
    with pytest.raises(ValueError, match='native_control_case_index_invalid'):
        runner.prepare_claim_scope(0)
    negative = data['cases'][2]
    result = SimpleNamespace(verdict=EvaluationVerdict.NEEDS_REVISION, score=70,
        issues=[dict(quote=negative['targets'][0], category='fact_error')])
    assert runner.score_case(negative, result)['target_location_flagged']
    args.execute = True
    # Admission is stateful; explicitly test the offline gate independently.
    monkeypatch.setattr(native, 'LIVE_STATUS', 'offline_claim_scope_adjudication')
    monkeypatch.setattr(runner, 'prepare_claim_scope', forbidden)
    with pytest.raises(ValueError, match=native.LIVE_BLOCK_REASON):
        runner.run(args, candidate_module=native)
