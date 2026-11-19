"""Candidate policy/identity and scripted full workflow, never model evidence."""
from dataclasses import replace

import pytest

from app.evaluation.document_review_identity import request_identity as baseline_identity
from app.evaluation.golden_role_boundary_examples import EXAMPLES
from app.evaluation.golden_review_experiment import digest
from app.evaluation.role_qualification import frozen_cases
from scripts import report_contrast_review as candidate
from scripts.report_document_workflow import DocumentReviewWorkflow
from tests.test_report_block_keyed_editor import run_flow


def test_all_fifteen_exact_sources_and_existing_review_schema_preserved():
    rows = frozen_cases()[0]
    assert len(rows) == 15
    for _, source in rows:
        inputs = DocumentReviewWorkflow.build_inputs(source)
        original = DocumentReviewWorkflow.make_request(inputs)
        request = candidate.ContrastDocumentWorkflow.make_request(inputs)
        assert candidate.baseline_request(request) == original
        assert request.messages[1:] == original.messages[1:]
        assert request.tools == original.tools
        assert request.max_tokens == original.max_tokens and request.timeout_s == original.timeout_s
        assert EXAMPLES not in request.messages[0].content
        assert request.messages[0].content.count(candidate.CONTRASTS) == 1
        assert candidate.request_identity(request) == ('zhipu', 'glm-5.3')
        with pytest.raises(ValueError): baseline_identity(request)


@pytest.mark.parametrize('fault', ['policy', 'marker', 'report', 'schema'])
def test_candidate_cannot_bypass_policy_or_baseline_source_shape(fault):
    _, source = frozen_cases()[0][0]
    request = candidate.ContrastDocumentWorkflow.make_request(DocumentReviewWorkflow.build_inputs(source))
    if fault == 'policy': request = replace(request, messages=(replace(request.messages[0],
        content=request.messages[0].content + 'unapproved policy'), *request.messages[1:]))
    if fault == 'marker': request = replace(request, metadata={**request.metadata, candidate.METADATA: 'other'})
    if fault == 'report': request = replace(request, messages=(request.messages[0], replace(request.messages[1],
        content=request.messages[1].content.replace('[HOST_BLOCK:', '[WRONG_BLOCK:')), *request.messages[2:]))
    if fault == 'schema': request = replace(request, tools=())
    with pytest.raises(ValueError): candidate.request_identity(request)


@pytest.mark.parametrize('mode', ['pass', 'reject_fresh', 'bad_edit', 'empty_edit'])
def test_contrast_initial_keyed_edit_and_contrast_fresh_share_existing_budget(monkeypatch, mode):
    flow = run_flow(monkeypatch, mode, workflow_type=candidate.ContrastDocumentWorkflow,
        router_type=candidate.ContrastDiagnosticRouter,
        contract=candidate.ContrastDiagnosticLimits())
    if flow is not None:
        assert flow.last_journal['teaching_candidate'] == candidate.VERSION
        assert flow.last_journal['policy_sha256'] == digest(
            flow.make_request(flow._expected_recheck).messages[0].content)
        assert flow.last_edit_journal['teaching_candidate'] == candidate.VERSION
        assert not flow.last_edit_journal['semantic_approval']
