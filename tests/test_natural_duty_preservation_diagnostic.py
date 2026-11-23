"""No-network request/evidence boundaries; these do not test model quality."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import json
import socket

import pytest

from app.evaluation.golden_review_experiment import compact
from app.evaluation.natural_duty_contract import request_bytes
from app.evaluation.source_patch_editor import report_inputs
from scripts import plan_natural_duty_preservation_diagnostic as plan


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('diagnostic preparation must remain offline')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)


@pytest.fixture(scope='module')
def materials():
    return {p.case_id:p for p in plan.pairs.material_pairs()}


def test_both_research_arms_preserve_full_final_and_reject_product_identity(materials):
    pair = materials['p01']
    for name in plan.probe.duty.DUTIES:
        base = plan.make_request(pair.final, name, 'fresh')
        for arm in plan.ARMS:
            request = plan.research_request(pair.original, pair.final, name, arm)
            assert request.messages[1:len(base.messages)] == base.messages[1:]
            assert request.timeout_s == base.timeout_s == 300
            assert request.max_tokens == base.max_tokens == 32768
            assert request.tools[0].input_schema == plan.DiagnosticReview.model_json_schema()
            assert 'repairs' not in request.tools[0].input_schema['properties']
            with pytest.raises(ValueError, match='natural_duty_review_identity'):
                request_bytes(request)
            if arm == 'with_original':
                payload = request.messages[-1].content[len(plan.probe.ORIGINAL_HEADER):-len(plan.probe.ORIGINAL_END)]
                assert json.loads(payload) == dict(report=pair.original.source.report,
                    report_sha256=plan.digest(pair.original.source.report))
            else:
                assert len(request.messages) == len(base.messages)
                assert 'original_input_sha256' not in request.metadata


def test_research_ignores_case_ids_and_authored_evaluation_labels():
    before = plan.pairs.read_dataset()
    after = deepcopy(before)
    for i,c in enumerate(after['cases']):
        c['id'] = 'EVALUATION_SENTINEL_' + str(i)
        c['evaluation'] = {'fabricated_verdict':'EVALUATION_SENTINEL'}
    for a,b in zip(plan.pairs.material_pairs(before), plan.pairs.material_pairs(after)):
        for name in plan.probe.duty.DUTIES:
            for arm in plan.ARMS:
                assert plan.research_request(a.original, a.final, name, arm) == plan.research_request(
                    b.original, b.final, name, arm)


def test_source_or_index_change_rejects_before_research_request(materials):
    p = materials['p01']
    changed = json.loads(p.final.data_json)
    changed['knowledge']['context'] += ' corrupted source'
    with pytest.raises(ValueError, match='sources_changed'):
        plan.research_request(p.original, replace(p.final, data_json=compact(changed)), 'facts', 'with_original')


def test_additional_original_overflow_rejects_without_truncation(materials):
    p = materials['p01']
    large = report_inputs(p.original, p.original.source.report + '\n\n' + '测' * 4000)
    base = plan.research_request(large, large, 'facts', 'final_only')
    assert plan.probe.frozen.size(base) <= 64000
    with pytest.raises(ValueError, match='budget|ceiling|input'):
        plan.research_request(large, large, 'facts', 'with_original')


def test_output_requires_explicit_observation_lane_but_never_rewrites_verdict(materials):
    p = materials['p01']
    value = dict(score=95, verdict='pass', issues=[], issue_resolutions=[], advisories=[],
                 preservation_notes='Synthetic structural fixture: relative loss would require independent assessment.')
    wire = plan.validate_output(compact(value), p.final, 'completion', 'with_original')
    assert wire.verdict == 'pass' and not wire.issues
    assert wire.preservation_notes == value['preservation_notes']
    with pytest.raises(ValueError, match='observation_lane'):
        plan.validate_output(compact(value), p.final, 'completion', 'final_only')
    for missing in (None, '', '  '):
        value['preservation_notes'] = missing
        with pytest.raises(ValueError, match='observation_lane'):
            plan.validate_output(compact(value), p.final, 'completion', 'with_original')
    value['preservation_notes'] = None
    assert plan.validate_output(compact(value), p.final, 'completion', 'final_only').verdict == 'pass'
    # Existing final-report consistency checks must not be bypassed by the new lane.
    value['verdict'] = 'needs_revision'
    with pytest.raises(ValueError, match='revision_without_issues'):
        plan.validate_output(compact(value), p.final, 'completion', 'final_only')


def test_plan_deduplicates_only_identical_requests_and_costs_each_once(materials):
    result = plan.proposal()
    rows = result['requests']
    assert len(rows) == len({r['request_sha256'] for r in rows}) == 20
    assert len({r['model_visible_sha256'] for r in rows}) == 20
    aliased = [r for r in rows if len(r['case_aliases']) > 1]
    assert len(aliased) == 2
    assert all(r['case_aliases'] == ['p01','p02','p03'] and r['arm'] == 'final_only' for r in aliased)
    for row in rows:
        for case_id in row['case_aliases']:
            p = materials[case_id]
            request = plan.research_request(p.original, p.final, row['duty'], row['arm'])
            assert plan.probe.duty.request_sha(request) == row['request_sha256']
    assert [r['ordinal'] for r in rows] == list(range(1,21))
    core, controls, total = (result[k] for k in ('core_budget','contingent_controls_budget','maximum_budget'))
    assert core['max_calls'] == 12 and controls['max_calls'] == 8
    for key in ('max_calls','input_token_reservation','output_token_reservation','total_token_reservation',
                'max_model_active_seconds'):
        assert core[key] + controls[key] == total[key]
    assert total['total_token_reservation'] == sum(r['input_ceiling'] + r['output_reservation'] for r in rows)
    assert Decimal(total['uncached_estimate_cny']) == (
        Decimal(total['input_token_reservation'])*8 + Decimal(total['output_token_reservation'])*28) / 1000000


def test_saved_proposal_rebuilds_without_execution_or_quality_credit(tmp_path, monkeypatch):
    saved = plan.ROOT/'data/evaluation/results/natural_duty_preservation_diagnostic_plan_20261015.json'
    expected = json.loads(saved.read_bytes())
    archive = json.loads((plan.ROOT/'tests/fixtures/natural_duty_preservation_sources.json').read_bytes())
    assert archive['source_commit'] == '452972e781d16b2e716b51c067f19443b28344cf'
    assert set(archive['source_text_lf']) == {'app/evaluation/natural_duty_contract.py'}
    # Rebuild the closed plan's source inventory from its actual historical
    # text, not the later live transport. Request construction still exercises
    # current code and must reproduce every original request and budget.
    for name, source_sha in expected['source_sha256'].items():
        text = archive['source_text_lf'].get(name)
        if text is None:
            text = (plan.ROOT/name).read_text(encoding='utf-8')
        assert plan.digest(text) == source_sha, name
        path = tmp_path/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode('utf-8'))
    monkeypatch.setattr(plan, 'ROOT', tmp_path)
    result = plan.proposal()
    assert expected == result
    assert result['provider_calls'] == result['new_host_tasks'] == 0
    assert all(r['execution'] is r['model_result'] is r['independent_result'] is None for r in result['requests'])
    assert not any(result[k] for k in ('execution_ready','execution_authorized','qualified',
        'publication_allowed','independent_review_completed','actual_application_or_fresh_evidence'))
