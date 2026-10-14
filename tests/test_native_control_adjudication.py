"""Replay real public findings; the stop boundary does not certify semantics."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import socket

import pytest

from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_integrated_runtime import _result
from app.evaluation.golden_review_experiment import compact, digest
from scripts.check_native_claim_scope import load_controls
from scripts.run_golden_integrated_review import observe_report
from scripts.run_golden_native_review import score_case
from tests.test_golden_integrated_review import ReplayProvider

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / 'data/evaluation/results/golden_native_claim_scope_result_354d752.json'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail('control adjudication replay must never use the network')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def saved_case(index):
    data, requests, _ = load_controls()
    saved = next(c for c in json.loads(RESULT.read_text(encoding='utf-8'))['cases'] if c['index'] == index)
    case, request = data['cases'][index-1], requests[index-1]
    assert saved['original_report'] == request.report
    for response in saved['responses']:
        assert digest(response['content']) == response['content_sha256']
    return case, request, saved


def replay(tmp_path, case, request, responses):
    def reply(_, number):
        if number > len(responses):
            pytest.fail('an unadjudicated finding caused another model call')
        return responses[number-1]
    provider = ReplayProvider(reply)
    outcome = observe_report(provider, tmp_path, request, case,
        workflow_factory=native.NativeBusinessReviewWorkflow, score_case=score_case)
    return outcome, provider


def test_real_unexpected_finding_stops_before_revision_and_preserves_original(tmp_path):
    case, request, saved = saved_case(3)
    _, positive, _ = saved_case(1)
    before = native.build_inputs(positive).source.blocks
    after = native.build_inputs(request).source.blocks
    assert [i for i, (a, b) in enumerate(zip(before, after, strict=True), 1) if a != b] == [6]
    raw = saved['responses'][0]['content']
    outcome, provider = replay(tmp_path, case, request, [raw])
    assert outcome['valid'] and outcome['matched']  # target detection is still true
    assert outcome['unexpected_issue_indices'] == [2]
    assert outcome['manual_adjudication_required']
    assert outcome['stop_reason'] == 'unadjudicated_control_findings'
    assert not outcome['revision_attempted'] and not outcome['automatic_path_pass']
    assert outcome['completed_calls'] == outcome['reserved_calls'] == len(provider.requests) == 1
    assert not outcome['manual_semantic_acceptance'] and not outcome['semantic_approval']
    recorded = json.loads((tmp_path/'response-001.json').read_text(encoding='utf-8'))
    assert recorded['content'] == raw
    assert len(json.loads(recorded['content'])['issues']) == 2
    assert not (tmp_path/'revised-report.md').exists()
    # Historical execution evidence remains a rejected three-call path.
    assert saved['result']['completed_calls'] == 3 and saved['manual_semantic_acceptance'] is False
    assert saved['result']['automatic_path_pass'] is True


@pytest.mark.parametrize('index,calls', [(1, 1), (4, 3)])
def test_accepted_controls_keep_their_actual_paths(tmp_path, index, calls):
    case, request, saved = saved_case(index)
    outcome, provider = replay(tmp_path, case, request, [r['content'] for r in saved['responses']])
    assert outcome['automatic_path_pass'] and len(provider.requests) == calls
    assert not outcome['manual_adjudication_required']
    assert outcome['unexpected_issue_indices'] == []
    assert not outcome['semantic_approval'] and not outcome['manual_semantic_acceptance']
    if calls == 3:
        assert (tmp_path/'revised-report.md').read_text(encoding='utf-8') == saved['revised_report']


def test_genuine_unlabelled_problem_is_unadjudicated_not_automatically_false(tmp_path):
    case, request, saved = saved_case(3)
    # Analyst-authored added future claim: not a new model success or frozen case.
    request = replace(request, report=request.report+'\n\n这五局已经证明所有未来对局都会获胜。')
    inputs = native.build_inputs(request)
    wire = json.loads(saved['responses'][0]['content'])
    wire['issues'][1].update(block=len(inputs.source.blocks), category='unsupported_comparison',
        source_ids=[31], explanation='分析者构造：所选五局不能证明所有未来对局都会获胜。',
        suggested_correction='删除无依据的未来胜利保证，保留当前样本范围。')
    outcome, provider = replay(tmp_path, case, request, [compact(wire)])
    assert outcome['stop_reason'] == 'unadjudicated_control_findings'
    assert outcome['unexpected_issue_indices'] == [2] and len(provider.requests) == 1
    assert 'false_positive' not in outcome  # labels do not adjudicate the added claim


def test_same_block_findings_and_multiple_targets_remain_manual_semantic_limits():
    case, request, saved = saved_case(3)
    inputs = native.build_inputs(request)
    wire = json.loads(saved['responses'][0]['content'])
    wire['issues'][1]['block'] = 6
    result = _result(native.validate(compact(wire), inputs)[0])
    same_block = score_case(case, result)
    assert same_block['unexpected_issue_indices'] == []
    assert same_block['semantic_approval'] is False
    # A separate, explicit multi-target control may cover both locations.
    multi = deepcopy(case)
    multi['targets'] = [*case['targets'], inputs.source.blocks[3][1]]
    result = _result(native.validate(saved['responses'][0]['content'], inputs)[0])
    assert score_case(multi, result)['unexpected_issue_indices'] == []
