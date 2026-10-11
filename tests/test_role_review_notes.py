"""Offline contract checks; synthetic notes never establish model quality."""
from copy import deepcopy
from dataclasses import fields, replace
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from app.evaluation import role_qualification as qualification
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_native_partitioned_tool_review import PartitionedReview
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_notes import RoleNoteReview, RoleNoteReviewWorkflow
from app.evaluation.golden_role_review import RoleReviewWorkflow
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.harness.steps import (
    EvaluationRequest, EvaluationVerdict, KnowledgeCitation, KnowledgeEvidence,
    KnowledgeRetrieval, RevisionRequest,
)
from app.providers.models import ChatResponse, TokenUsage, ToolCall
from scripts.export_partitioned_review import public_response


RESULTS = qualification.ROOT / "data/evaluation/results"


def request_data(request):
    content = request.messages[1].content
    start, end = "[UNTRUSTED DATA]\n", "\n[END UNTRUSTED DATA]"
    assert start in content and content.endswith(end)
    return json.loads(content.partition(start)[2][:-len(end)])


def note_review():
    # Host-authored structural fixture, not a transformed historical opinion.
    return dict(score=96, verdict="pass", issues=[], issue_resolutions=[],
        advisories=[dict(block=18, source_ids=[9, 11, 13, 15],
            explanation="可在本段再次写明中单样本范围，以便阅读。")])


def tool_response(value):
    return ChatResponse(content=None, model="glm-5.3", provider="zhipu",
        finish_reason="tool_calls", usage=TokenUsage(10, 10),
        tool_calls=(ToolCall("offline-review", "submit_report_review", value),))


class OfflineSender:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        response = next(self.responses)
        return Exchange(request, response, hashlib.sha256(
            validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())


@pytest.fixture(scope="module")
def frozen_cases():
    return qualification.frozen_cases()[0]


@pytest.fixture(scope="module")
def historical_review():
    saved = json.loads((RESULTS / "golden_role_source_metadata_result_v1.json")
        .read_text(encoding="utf-8"))
    public = saved["public_json_contents"]
    markdown = saved["original_markdown_contents"]
    raw_request = public["transport/review/request-003.json"]
    content = raw_request["messages"][1]["content"]
    data = json.loads(content.partition("[UNTRUSTED DATA]\n")[2]
        .removesuffix("\n[END UNTRUSTED DATA]"))
    stored = public["reports/knowledge/retrieval_evidence.json"]
    citation_fields = {field.name for field in fields(KnowledgeCitation)}
    knowledge = KnowledgeEvidence(context=stored["context"],
        source_ids=tuple(stored["source_ids"]), abstained=stored["abstained"],
        diagnostics=stored["diagnostics"],
        citations=tuple(KnowledgeCitation(**{key: value for key, value in citation.items()
            if key in citation_fields}) for citation in stored["citations"]),
        retrievals=tuple(KnowledgeRetrieval(**dict(retrieval,
            chunk_ids=tuple(retrieval["chunk_ids"]))) for retrieval in stored["retrievals"]))
    source = EvaluationRequest(public["reports/inputs/player_summary.json"],
        markdown["reports/inputs/deterministic_report.md"], knowledge,
        markdown["reports/drafts/coach_draft_attempt_0.md"], data["user_utterance"])
    inputs = RoleReviewWorkflow.build_inputs(source)
    journal = saved["reconstructed_review_journal"]
    response = public_response(public["transport/review/response-003.json"])
    assert compact(response["tool_calls"][0]["arguments"]) == journal["raw"]
    assert digest(journal["raw"]) == journal["raw_sha256"]
    assert digest(inputs.data_json) == journal["input_sha256"]
    return saved, source, inputs


def test_schema_changes_only_advisory_correction_and_keeps_issue_contract():
    old, new = PartitionedReview.model_json_schema(), RoleNoteReview.model_json_schema()
    assert issubclass(RoleNoteReview, PartitionedReview)
    assert issubclass(RoleNoteReviewWorkflow, RoleReviewWorkflow)
    assert set(new["properties"]) == set(old["properties"])
    assert new["required"] == old["required"]
    for name in ("score", "verdict", "issues", "issue_resolutions"):
        assert new["properties"][name] == old["properties"][name]
    for name in ("Problem", "IssueResolution"):
        assert new["$defs"][name] == old["$defs"][name]
    note_name = new["properties"]["advisories"]["items"]["$ref"].rsplit("/", 1)[1]
    note = new["$defs"][note_name]
    assert set(note["properties"]) == set(note["required"]) == {
        "block", "source_ids", "explanation"}
    assert note["additionalProperties"] is False
    assert "suggested_correction" in new["$defs"]["Problem"]["required"]


def test_old_public_response_replays_unchanged_and_is_rejected_by_new_schema(historical_review):
    saved, _, inputs = historical_review
    original = saved["reconstructed_review_journal"]
    raw = original["raw"]
    payload, wire, journal = RoleReviewWorkflow.validate_review(raw, inputs)
    assert journal == original
    assert payload.verdict == "pass" and payload.issues == []
    assert wire.advisories[1].source_ids == [9, 11, 13, 15]
    assert "伤害减半" in wire.advisories[1].suggested_correction
    assert saved["host_review"]["host_report_semantic_accepted"] is True
    assert saved["host_review"]["complete_review_output_accepted"] is False
    finding, = saved["host_review"]["review_findings"]
    assert finding["kind"] == "incomplete_selected_sources"
    assert finding["absent_supporting_ids"] == [10, 14]
    with pytest.raises(ValueError, match="suggested_correction"):
        RoleNoteReviewWorkflow.validate_review(raw, inputs)
    assert original["raw"] == raw and digest(raw) == original["raw_sha256"]


def test_new_note_is_nonblocking_without_expanding_sources_or_approving_semantics(historical_review):
    saved, source, inputs = historical_review
    value = note_review()
    payload, wire, journal = RoleNoteReviewWorkflow.validate_review(compact(value), inputs)
    assert payload.verdict == "pass" and payload.issues == []
    assert wire.model_dump(mode="json") == value
    selected = journal["advisories"][0]["selected_sources"]
    assert selected == saved["reconstructed_review_journal"]["advisories"][1]["selected_sources"]
    assert [entry["source_id"] for entry in selected] == [9, 11, 13, 15]
    assert all(entry["kind"] == "role_statistic" for entry in selected)
    assert all(set(entry["value"]) == {"games", "valid", "missing_or_invalid", "mean"}
        for entry in selected)
    assert not journal["semantic_approval"] and not journal["production_admitted"]
    assert all(entry["semantic_approval"] is False for entry in selected)
    assert "suggested_correction" not in journal["advisories"][0]
    sender = OfflineSender(tool_response(value))
    flow = RoleNoteReviewWorkflow(sender)
    result = flow.evaluate(source)
    assert result.verdict is EvaluationVerdict.PASS and result.issues == ()
    assert flow.calls == len(sender.requests) == 1 and flow.revisions == 0
    assert not hasattr(result, "advisories")
    assert sender.requests[0].tools[0].input_schema == RoleNoteReview.model_json_schema()
    assert flow.last_journal["policy_sha256"] == digest(sender.requests[0].messages[0].content)


@pytest.mark.parametrize("source_ids", [[999], [9, 9]])
def test_note_still_rejects_unknown_and_duplicate_source_ids(historical_review, source_ids):
    _, _, inputs = historical_review
    value = note_review()
    value["advisories"][0]["source_ids"] = source_ids
    with pytest.raises(ValueError, match="source|duplicate"):
        RoleNoteReviewWorkflow.validate_review(compact(value), inputs)


def test_real_issue_keeps_correction_and_editor_excludes_note(frozen_cases):
    sources = {frozen["key"]: source for frozen, source in frozen_cases}
    source, corrected = sources["attribution:1"], sources["claim-scope:1"]
    previous = json.loads((RESULTS / "golden_explicit_source_pair_result_0c061b2.json")
        .read_text(encoding="utf-8"))["original_json_contents"]
    original = public_response(previous["attribution_original-baseline/response.json"])
    value = deepcopy(original["tool_calls"][0]["arguments"])
    value["advisories"] = [dict(block=4, source_ids=[1],
        explanation="本段已明确观摩对象与阅读者不同，可选地压缩重复措辞。")]
    issue, = value["issues"]
    assert issue["block"] == 14 and issue["category"] == "causality"
    inputs = RoleNoteReviewWorkflow.build_inputs(source)
    missing_correction = deepcopy(value)
    del missing_correction["issues"][0]["suggested_correction"]
    with pytest.raises(ValueError, match="suggested_correction"):
        RoleNoteReviewWorkflow.validate_review(compact(missing_correction), inputs)
    edited = ChatResponse(content=corrected.report, model="glm-5.3-flash", provider="zhipu",
        finish_reason="stop", usage=TokenUsage(10, 10))
    sender = OfflineSender(tool_response(value), edited, tool_response(dict(
        score=97, verdict="pass", issues=[], issue_resolutions=[], advisories=[])))
    flow = RoleNoteReviewWorkflow(sender)
    result = flow.evaluate(source)
    assert result.verdict is EvaluationVerdict.NEEDS_REVISION
    assert len(result.issues) == 1
    assert result.issues[0]["suggested_correction"] == issue["suggested_correction"]
    draft = flow.revise(RevisionRequest(source.player_summary, source.deterministic_report,
        source.knowledge, source.report, result))
    accepted = request_data(sender.requests[1])["accepted_review"]
    assert "advisories" not in accepted and accepted["issues"] == value["issues"]
    assert draft.report == corrected.report
    final = flow.evaluate(replace(source, report=draft.report))
    assert final.verdict is EvaluationVerdict.PASS
    assert flow.calls == 3 and flow.revisions == 1


def test_reassessment_preserves_malformed_raw_instead_of_stripping_old_field(historical_review):
    saved, source, _ = historical_review
    original = saved["reconstructed_review_journal"]["raw"]
    malformed = json.loads(original)
    corrected = note_review()  # Independent host-authored response, not raw repair.
    sender = OfflineSender(tool_response(malformed), tool_response(corrected))
    records = []
    flow = RoleNoteReviewWorkflow(sender, record=lambda phase, exchange: records.append((phase, exchange)))
    result = flow.evaluate(source)
    assert result.verdict is EvaluationVerdict.PASS and flow.calls == 2
    reassessment = request_data(sender.requests[1])
    assert reassessment["previous_review"] == malformed
    assert reassessment["previous_raw_sha256"] == digest(original)
    assert reassessment["previous_review"]["advisories"][1]["suggested_correction"]
    assert any(error["type"] == "extra_forbidden"
        and error["loc"][-1] == "suggested_correction"
        for error in reassessment["diagnostics"])
    assert flow.last_journal["previous_raw"] == original
    assert flow.last_journal["raw"] == compact(corrected)
    assert flow.last_journal["parsed_review"] == corrected
    assert not flow.last_journal["semantic_approval"]
    assert flow.last_journal["policy_sha256"] == digest(sender.requests[1].messages[0].content)
    assert sender.requests[1].tools[0].input_schema == RoleNoteReview.model_json_schema()
    initial_data = request_data(sender.requests[0])
    assert {key: reassessment[key] for key in initial_data} == initial_data
    assert [phase for phase, _ in records] == ["native_business_review", "native_business_reassessment"]
    assert compact(dict(records[0][1].response.tool_calls[0].arguments)) == original


def test_all_fifteen_sources_restore_without_runs_and_are_unchanged(tmp_path, frozen_cases):
    paths = [qualification.COVERAGE, *qualification.DATASETS.values(),
        Path("tests/fixtures/native_missing_block_reassessment.json"),
        Path("tests/fixtures/native_heading_recheck_failure.json")]
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(qualification.ROOT / path, target)
    restored, aliases = qualification.frozen_cases(root=tmp_path)
    assert not (tmp_path / "data/runs").exists()
    assert restored == frozen_cases and len(restored) == 15
    assert aliases == qualification.frozen_cases()[1]
    for frozen, source in restored:
        old_inputs = RoleReviewWorkflow.build_inputs(source)
        new_inputs = RoleNoteReviewWorkflow.build_inputs(source)
        assert old_inputs == new_inputs
        assert digest(new_inputs.data_json) == frozen["input_sha256"]
        old_request = RoleReviewWorkflow.make_request(old_inputs)
        new_request = RoleNoteReviewWorkflow.make_request(new_inputs)
        assert request_data(new_request) == request_data(old_request)
        assert new_request.messages[2].content == old_request.messages[2].content
        assert (new_request.max_tokens, new_request.timeout_s) == (
            old_request.max_tokens, old_request.timeout_s)
