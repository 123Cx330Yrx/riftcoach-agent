"""Atomic edit identity and failure witnesses; no model-quality assertions."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from app.evaluation import source_patch_editor as editor
from app.evaluation.golden_native_issues_review import build_inputs
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_review import RoleReviewWorkflow
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.evaluation.role_qualification import frozen_cases
from scripts.check_source_bound_report import original_request
from scripts.native_contract_options import body


@pytest.fixture
def case():
    req, _, failure = original_request()
    reference = json.loads(Path("data/evaluation/datasets/golden_source_time_reference_audit_v2.json").read_text(encoding="utf-8"))
    return req, build_inputs(req), reference, failure


def edits_for(case):
    _, inputs, reference, _ = case
    edits = []
    for edit in reference["edits_from_original"]:
        block = next(n for n, (_, text) in enumerate(inputs.source.blocks, 1) if edit["before"] in text)
        edits.append(dict(block=block, before=edit["before"], after=edit["after"],
            source_ids=[25] if block == 27 else [31], reason="Host-authored representation witness, not model output."))
    return edits


def test_two_explicit_edits_reconstruct_reference_and_bind_full_final_input(case):
    req, inputs, reference, _ = case
    result = editor.apply_edits(compact({"edits": edits_for(case)}), inputs)
    assert result.report == reference["reference_report"]
    reconstructed = editor.report_inputs(inputs, result.report)
    assert reconstructed == build_inputs(replace(req, report=result.report))
    final = RoleReviewWorkflow.make_request(reconstructed)
    assert body(final)["source_index"]["blocks"] == build_inputs(replace(req, report=result.report)).source.prompt_sources()["blocks"]
    assert result.journal["original_report"] == req.report
    assert result.journal["full_final_review_required"]
    assert not result.journal["semantic_approval"]
    assert size(final) <= 63936


def test_keep_does_not_hide_known_error_or_create_a_pass(case):
    req, inputs, _, failure = case
    result = editor.apply_edits('{"edits":[]}', inputs)
    assert result.report == req.report
    assert not result.journal["edit_changed"] and not result.journal["semantic_approval"]
    raw = failure["public_json_contents"]["original-date-error/journal.json"]["raw"]
    payload, _, _ = RoleReviewWorkflow.validate_review(raw, inputs)
    assert payload.verdict == "pass"  # The old wrong pass stays a counterexample.
    assert failure["host_review"]["report_quote"] in result.report


@pytest.mark.parametrize("fault", ["overlap", "unknown_source", "unknown_block", "missing_anchor", "noop", "citation", "empty_before"])
def test_invalid_operation_never_yields_partially_applied_report(case, fault):
    _, inputs, _, _ = case
    edits = edits_for(case)
    if fault == "overlap": edits.append(dict(edits[0]))
    if fault == "unknown_source": edits[1]["source_ids"] = [9999]
    if fault == "unknown_block": edits[1]["block"] = 64
    if fault == "missing_anchor": edits[1]["before"] = "not in the report"
    if fault == "noop": edits[1]["after"] = edits[1]["before"]
    if fault == "citation": edits[1]["after"] += "[K9999]"
    if fault == "empty_before": edits[1]["before"] = ""
    original = inputs.source.report
    with pytest.raises(ValueError): editor.apply_edits(compact({"edits": edits}), inputs)
    assert inputs.source.report == original


def test_duplicate_blocks_are_addressed_by_position_and_whitespace_is_preserved(case):
    req, _, _, _ = case
    original = req.report.replace("\n", "\r\n") + "\r\n\r\nSAME repeated SAME.\r\n\r\nSAME repeated SAME.\r\n"
    inputs = build_inputs(replace(req, report=original))
    block = len(inputs.source.blocks)
    edit = dict(block=block, before="SAME", after="OTHER", source_ids=[25], reason="Test identity only.")
    with pytest.raises(ValueError, match="source_edit_anchor_not_unique"):
        editor.apply_edits(compact({"edits": [edit]}), inputs)
    edit.update(before="SAME repeated SAME.", after="OTHER repeated SAME.")
    result = editor.apply_edits(compact({"edits": [edit]}), inputs)
    expected = original[:original.rfind(edit["before"])] + edit["after"] + "\r\n"
    assert result.report == expected and result.report.count("SAME repeated SAME.") == 1


def test_disjoint_same_block_operations_are_simultaneous_not_cascaded(case):
    req, _, _, _ = case
    original = req.report + "\n\nalpha BETA gamma.\n"
    inputs = build_inputs(replace(req, report=original))
    def edit(before, after):
        return dict(block=len(inputs.source.blocks), before=before, after=after, source_ids=[25], reason="Test identity only.")
    edits = [edit("alpha", "BETA"), edit("BETA", "delta")]
    result = editor.apply_edits(compact({"edits": edits}), inputs)
    assert result.report == original.replace("alpha BETA gamma.", "BETA delta gamma.")
    assert editor.apply_edits(compact({"edits": list(reversed(edits))}), inputs).report == result.report


def test_delete_optional_block_allowed_but_required_heading_and_large_removal_rejected(case):
    req, _, _, _ = case
    inputs = build_inputs(replace(req, report=req.report + "\n\nRemove me.\n"))
    edit = dict(block=len(inputs.source.blocks), before="Remove me.", after="", source_ids=[25], reason="Test identity only.")
    assert editor.apply_edits(compact({"edits": [edit]}), inputs).report == req.report + "\n\n\n"
    edit.update(block=1, before=inputs.source.blocks[0][1])
    with pytest.raises(ValueError): editor.apply_edits(compact({"edits": [edit]}), inputs)


@pytest.mark.parametrize("fault", ["swap", "inline_heading", "duplicate", "fenced", "too_large", "stale_source"])
def test_invalid_structure_and_unreachable_final_review_are_rejected(case, fault):
    req, inputs, _, _ = case
    from app.report_validation import COACH_REPORT_HEADINGS as headings
    def edit(block, before, after):
        return dict(block=block, before=before, after=after, source_ids=[25], reason="Test structure only.")
    first = next(n for n, (_, text) in enumerate(inputs.source.blocks, 1) if text.startswith(headings[0]))
    second = next(n for n, (_, text) in enumerate(inputs.source.blocks, 1) if text.startswith(headings[1]))
    edits = [edit(first, headings[0], "inline " + headings[0])]
    if fault == "swap": edits = [edit(first, headings[0], headings[1]), edit(second, headings[1], headings[0])]
    if fault == "duplicate": edits = [edit(first, headings[0], headings[0] + "\n\n" + headings[0])]
    if fault == "fenced": edits = [edit(first, headings[0], "```\n" + headings[0] + "\n```")]
    if fault == "too_large":
        # Valid report-size/block-count does not imply a legal final LLM request.
        edits = [edit(first + 1, inputs.source.blocks[first][1], inputs.source.blocks[first][1] + "字" * 21000)]
    if fault == "stale_source":
        inputs = replace(inputs, source=replace(inputs.source, report=req.report + "changed"))
        edits = []
    with pytest.raises(ValueError): editor.apply_edits(compact({"edits": edits}), inputs)


def test_requests_preserve_full_data_and_original_fifteen_without_io(case, monkeypatch):
    import socket
    read = Path.read_text
    def offline(path, *args, **kwargs):
        assert "data/runs/" not in path.as_posix() and path.name != ".env"
        return read(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", offline)
    monkeypatch.setattr(socket.socket, "connect", lambda *_: pytest.fail("unexpected network"))
    cases, _ = frozen_cases()
    for _, req in cases:
        inputs = build_inputs(req)
        request = editor.edit_request(inputs)
        baseline = RoleReviewWorkflow.make_request(inputs)
        assert body(request) == body(baseline) and request.messages[2] == baseline.messages[2]
        assert size(request) <= 63936
        assert editor.apply_edits('{"edits":[]}', inputs).report == req.report
        assert request.metadata["review_phase"] == editor.VERSION
        from app.runtime.reviewer_roles import role_for_request
        with pytest.raises(ValueError, match="role_phase_invalid"): role_for_request(request)
    inputs = case[1]
    findings = [{"block": 18, "explanation": "Untrusted prior finding."}]
    request = editor.edit_request(inputs, review_findings=findings)
    assert body(request).pop("review_findings") == findings


def test_exchange_binding_refuses_other_input_and_non_tool_response(case):
    from app.evaluation.golden_integrated_runtime import Exchange
    from app.providers.models import ChatResponse, TokenUsage, ToolCall
    _, inputs, _, _ = case
    prepared = editor.edit_request(inputs)
    response = ChatResponse(provider="zhipu", model="glm-5.3-flash", finish_reason="tool_calls",
        content=None, usage=TokenUsage(1, 1), tool_calls=(ToolCall(id="call_1", name=editor.SUBMIT_TOOL,
        arguments={"edits": []}),))
    exchange = Exchange(prepared, response, hashlib.sha256(validate_request(prepared, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
    outcome, _ = editor.inspect_exchange(prepared, exchange, inputs)
    assert not outcome["edit_changed"]
    wrong = build_inputs(replace(case[0], report=case[2]["reference_report"]))
    with pytest.raises(ValueError, match="source_edit_input_changed"):
        editor.inspect_exchange(prepared, exchange, wrong)
    with pytest.raises(ValueError, match="source_edit_exchange_identity"):
        editor.inspect_exchange(prepared, replace(exchange, receipt_request_sha256="0" * 64), inputs)
    with pytest.raises(ValueError, match="source_edit_tool_channel"):
        editor.inspect_exchange(prepared, replace(exchange, response=replace(response, content="PASS")), inputs)
