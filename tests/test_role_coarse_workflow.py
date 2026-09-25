"""Real initial receipt through existing revision order, with offline IO."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from app.evaluation.golden_role_coarse import RoleCoarseReviewWorkflow as Workflow, CONTRACT_ID
from app.evaluation.golden_role_clarity import RoleClarityReviewWorkflow as Legacy
from app.evaluation.golden_review_experiment import compact
from app.evaluation.role_qualification import ROOT, frozen_cases
from app.harness.steps import RevisionRequest, EvaluationVerdict
from app.providers.models import ChatResponse, TokenUsage
from app.evaluation import golden_coarse_source_projection as coarse
from tests.test_role_review_notes import OfflineSender, request_data, tool_response


@pytest.fixture(scope='module')
def source_and_review():
    cases = {row['key']: source for row, source in frozen_cases()[0]}
    saved = json.loads((ROOT/'data/evaluation/results/golden_coarse_source_result_v1.json').read_bytes())
    wire = saved['public_json_contents']['observed-2/response.json']['tool_calls'][0]['arguments']
    return cases['observed:2'], cases['observed:1'], wire


def test_actual_review_drives_existing_edit_and_fresh_final(source_and_review):
    source, correct, wire = source_and_review
    final = dict(score=96, verdict='pass', issues=[], issue_resolutions=[], advisories=[])
    edit = ChatResponse(content=correct.report, provider='zhipu', model='glm-5.3-flash',
                        finish_reason='stop', usage=TokenUsage(10, 10))
    sender = OfflineSender(tool_response(wire), edit, tool_response(final))
    flow = Workflow(sender)
    result = flow.evaluate(source)
    assert flow.last_journal['experiment'] == CONTRACT_ID
    assert flow.last_journal['validator_experiment'] == CONTRACT_ID
    assert [r['source_id'] for r in flow.last_journal['selected_sources'][0]['selected_sources']] == [27, 38, 39]
    inputs = flow.build_inputs(source)
    _, accepted, _ = flow.validate_review(compact(wire), inputs)
    request = flow.make_request(inputs, accepted=accepted)
    assert request_data(request)['accepted_review']['issues'] == wire['issues']
    assert 'advisories' not in request_data(request)['accepted_review']
    assert not request.tools
    assert coarse.restore_request(request, inputs, accepted=accepted) == Legacy.make_request(inputs, accepted=accepted)
    draft = flow.revise(RevisionRequest(source.player_summary, source.deterministic_report,
        source.knowledge, source.report, result))
    assert draft.report == correct.report
    recheck = replace(source, report=draft.report)
    fresh = request_data(flow.make_request(flow.build_inputs(recheck)))
    assert not {'accepted_review', 'previous_review', 'previous_issues'} & fresh.keys()
    assert flow.evaluate(recheck).verdict is EvaluationVerdict.PASS
    assert flow.calls == 3 and flow.revisions == 1


@pytest.mark.parametrize('ids', [[15,19], [999], [True], [39,39]])
def test_coarse_references_are_not_silently_repaired(source_and_review, ids):
    source, _, wire = source_and_review
    invalid = deepcopy(wire)
    invalid['issues'][0]['source_ids'] = ids
    with pytest.raises(ValueError):
        Workflow.validate_review(compact(invalid), Workflow.build_inputs(source))


def test_old_workflow_cannot_accept_new_complete_root(source_and_review):
    source, _, wire = source_and_review
    with pytest.raises(ValueError):
        Legacy.validate_review(compact(wire), Legacy.build_inputs(source))


def test_reassessment_keeps_prior_and_checks_resolution_sources(source_and_review):
    source, _, wire = source_and_review
    inputs = Workflow.build_inputs(source)
    raw = compact(wire)
    request = Workflow.make_request(inputs, previous_raw=raw, diagnostics={'reason':'offline'})
    assert request_data(request)['previous_review'] == wire
    assert coarse.restore_request(request, inputs, previous_raw=raw, diagnostics={'reason':'offline'}) == Legacy.make_request(inputs, previous_raw=raw, diagnostics={'reason':'offline'})
    revised = deepcopy(wire)
    revised['issue_resolutions'] = [dict(previous_id=1, disposition='replaced', final_issue=1,
        source_ids=[39], explanation='Same actual future prediction remains unsupported.')]
    Workflow.validate_review(compact(revised), inputs, previous_raw=raw)
    revised['issue_resolutions'][0]['source_ids'] = [15]
    with pytest.raises(ValueError, match='not_citable'):
        Workflow.validate_review(compact(revised), inputs, previous_raw=raw)


def test_changed_recheck_source_is_rejected(source_and_review):
    source, correct, wire = source_and_review
    edit = ChatResponse(content=correct.report, provider='zhipu', model='glm-5.3-flash',
                        finish_reason='stop', usage=TokenUsage(10,10))
    flow = Workflow(OfflineSender(tool_response(wire), edit))
    result = flow.evaluate(source)
    flow.revise(RevisionRequest(source.player_summary,source.deterministic_report,
        source.knowledge,source.report,result))
    with pytest.raises(ValueError,match='source_changed'):
        flow.evaluate(replace(source,report=correct.report,user_utterance='different owner request'))


def test_all_original_fifteen_keep_complete_sources_in_each_phase():
    for _, source in frozen_cases()[0]:
        inputs = Workflow.build_inputs(source)
        empty = dict(score=96, verdict='pass', issues=[], issue_resolutions=[], advisories=[])
        for kwargs in ({}, {'previous_raw':compact(empty), 'diagnostics':{'offline':True}}):
            projected = Workflow.make_request(inputs, **kwargs)
            assert coarse.restore_request(projected, inputs, **kwargs) == Legacy.make_request(inputs, **kwargs)
        assert not Workflow.validate_review(compact(empty), inputs)[2]['semantic_approval']


def test_security_and_prose_tail_remain_terminal(source_and_review):
    from app.providers.errors import ProviderResponseError
    source, _, wire = source_and_review
    inputs = Workflow.build_inputs(source)
    with pytest.raises(ProviderResponseError, match='native_review_non_json_suffix'):
        Workflow.validate_review(compact(wire)+'\nUnrecorded contradictory judgment.', inputs)
    unsafe = deepcopy(wire)
    unsafe['issues'][0]['category'] = 'prompt_injection'
    unsafe.update(verdict='fail',score=0)
    with pytest.raises(ValueError,match='security_terminal'):
        Workflow.validate_review(compact(unsafe), inputs)
