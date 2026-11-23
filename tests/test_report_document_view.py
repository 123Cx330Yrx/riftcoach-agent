"""Presentation/identity evidence only; no semantic or live-quality claim."""
from dataclasses import replace
import json

import pytest

from scripts import report_document_view as view
from app.evaluation.role_qualification import frozen_cases
from app.evaluation.source_patch_editor import report_inputs
from app.evaluation.golden_explicit_source_projection import _unpack
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from tests.test_coarse_revision_editor import cases, AFTER, BEFORE
from tests.test_native_editor_product_budget import offline


def test_fifteen_full_documents_sources_and_outputs_are_lossless():
    frozen = frozen_cases()[0]
    assert len(frozen) == 15
    for _, source in frozen:
        inputs = view.Current.build_inputs(source)
        base = view.Current.make_request(inputs)
        projected = view.project(inputs)
        marked, markers = view.document(inputs)
        assert view.restore_document(marked, inputs) == source.report
        assert len(markers) == len(inputs.source.blocks)
        for (_, block), marker in zip(inputs.source.blocks, markers):
            assert marker + block in marked
        assert projected.tools == base.tools
        assert projected.messages[3] == base.messages[2]
        assert view.restore(projected, inputs) == base
        original = _unpack(base)[1]
        data = json.loads(projected.messages[2].content.split('[UNTRUSTED DATA]\n', 1)[1].rsplit('\n[END UNTRUSTED DATA]', 1)[0])
        blocks = original['source_index'].pop('blocks')
        assert data == original
        assert all(b['text'] in marked for b in blocks)
        assert size(projected) <= 64000


@pytest.mark.parametrize('fault', ['document', 'source', 'policy', 'metadata', 'tools'])
def test_request_or_mapping_changes_reject(fault):
    _, inputs, _, _ = cases()['claim-scope:1']
    request = view.project(inputs)
    if fault in ('document', 'source', 'policy'):
        index = {'document': 1, 'source': 2, 'policy': 0}[fault]
        messages = list(request.messages)
        messages[index] = replace(messages[index], content=messages[index].content + 'changed')
        request = replace(request, messages=tuple(messages))
    elif fault == 'metadata':
        request = replace(request, metadata={})
    else:
        request = replace(request, tools=())
    with pytest.raises(ValueError, match='document_view_request_changed'):
        view.restore(request, inputs)


def test_fresh_rebuilds_mapping_and_rejects_old_document():
    _, inputs, accepted, _ = cases()['claim-scope:4']
    old, _ = view.document(inputs)
    updated = report_inputs(inputs, inputs.source.report.replace(BEFORE, AFTER))
    fresh = view.project(updated)
    assert view.restore(fresh, updated) == view.Current.make_request(updated)
    assert AFTER in fresh.messages[1].content and BEFORE not in fresh.messages[1].content
    with pytest.raises(ValueError, match='document_view_changed'):
        view.restore_document(old, updated)
    with pytest.raises(ValueError, match='document_view_editor_not_supported'):
        view.project(inputs, accepted=accepted)


def test_literal_host_like_markers_and_whitespace_are_not_stripped():
    _, inputs, _, _ = cases()['claim-scope:1']
    text = inputs.source.report + '\n\n[HOST_BLOCK:untrusted:1]\n\n  quoted text  \n'
    updated = report_inputs(inputs, text)
    rendered, _ = view.document(updated)
    assert view.restore_document(rendered, updated) == text


def test_unregistered_view_is_rejected_by_existing_product_router():
    from app.runtime.reviewer_roles import role_for_request
    from app.evaluation.golden_coarse_source_projection import VERSION
    _, inputs, _, _ = cases()['claim-scope:1']
    with pytest.raises(ValueError, match='role_source_projection_payload_mismatch'):
        role_for_request(view.project(inputs), source_projection=VERSION)


def test_five_slot_capacity_preview_from_actual_scripted_application(tmp_path):
    from tests.test_review_bound_coach_application import application
    from tests.test_role_coach_application import run
    app, factory, flows = application(tmp_path, 'success', True)
    result = run(app, 'document_capacity_preview')
    assert result.publication_status.value == 'published'  # Baseline scripted run only.
    router, flow = factory.created['document_capacity_preview'], flows[0]
    initial = report_inputs(flow._expected_recheck, flow.last_edit_journal['original_report'])
    assert view.Current.make_request(initial).messages == router.reviewer.requests[0].messages
    proposed = router.generator.requests + [view.project(initial), view.project(flow._expected_recheck)]
    assert len(proposed) == 5
    assert all(size(r) <= 64000 for r in proposed)
    reservation = sum(size(r) + r.max_tokens for r in proposed)
    assert reservation <= 401920
    print(dict(evidence='capacity_preview_not_projected_runtime_or_model_success',
               calls=len(proposed), reserved_tokens=reservation))
