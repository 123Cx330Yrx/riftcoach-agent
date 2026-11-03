"""Request delivery checks, not real-model semantic qualification."""
from dataclasses import replace
import hashlib
import json

import pytest

from app.evaluation.golden_role_notes import RoleNoteReviewWorkflow
from app.evaluation.golden_role_tool_delivery import DELIVERY_ID, RoleToolDeliveryReviewWorkflow
from app.evaluation.golden_native_issues_review import schema_notation
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import REQUEST, RESPONSE, validate_request, REVIEW_MODEL_TRANSPORT_ID
from app.evaluation.role_qualification import ROOT, frozen_cases, replay_case, replay_legacy_note_case
from scripts.prepare_review_model_comparison import sdk_arguments, mock_wire


@pytest.fixture(scope="module")
def cases():
    return {row["key"]: (row, source) for row, source in frozen_cases()[0]}


def test_all_fifteen_only_remove_text_schema_header_and_bind_delivery(cases):
    for _, source in cases.values():
        inputs = RoleNoteReviewWorkflow.build_inputs(source)
        before = RoleNoteReviewWorkflow.make_request(inputs)
        after = RoleToolDeliveryReviewWorkflow.make_request(inputs)
        header = schema_notation(before.tools[0].input_schema) + "\n"
        assert before.messages[1].content == header + after.messages[1].content
        assert after.messages[1].content.startswith("[UNTRUSTED DATA]\n")
        assert after.metadata == {**before.metadata, "review_delivery": DELIVERY_ID}
        assert replace(after, messages=before.messages, metadata=before.metadata) == before
        assert "severity" in after.tools[0].input_schema["$defs"]["Problem"]["required"]
        validate_request(after, transport_id=REVIEW_MODEL_TRANSPORT_ID)


def test_sdk_receives_one_complete_schema_and_full_original_source(cases):
    inputs = RoleNoteReviewWorkflow.build_inputs(cases["claim-scope:1"][1])
    before = RoleNoteReviewWorkflow.make_request(inputs)
    after = RoleToolDeliveryReviewWorkflow.make_request(inputs)
    old, new = [mock_wire(sdk_arguments(req)) for req in (before, after)]
    assert old["tools"] == new["tools"]
    assert new["tools"][0]["function"]["parameters"] == after.tools[0].input_schema
    assert new["tool_choice"] == "auto" and "response_format" not in new
    assert old["messages"][0] == new["messages"][0]
    assert old["messages"][2:] == new["messages"][2:]
    assert new["messages"][1]["content"] == after.messages[1].content
    old["messages"] = new["messages"]
    assert old == new


def test_recovery_keeps_entire_bad_response_and_diagnostics(cases):
    inputs = RoleNoteReviewWorkflow.build_inputs(cases["claim-scope:1"][1])
    saved = json.loads((ROOT / "data/evaluation/results/golden_role_note_qualification_pair_result_v1.json")
        .read_text(encoding="utf-8"))["public_json_contents"]
    original = saved["transport/claim-scope-1/review/response-001.json"]["tool_calls"][0]["arguments"]
    raw = compact(original)
    with pytest.raises(ValueError, match="severity"):
        RoleToolDeliveryReviewWorkflow.validate_review(raw, inputs)
    kwargs = dict(previous_raw=raw, diagnostics=[{"type": "missing", "loc": ["issues", 0, "severity"]}])
    before = RoleNoteReviewWorkflow.make_request(inputs, **kwargs)
    after = RoleToolDeliveryReviewWorkflow.make_request(inputs, **kwargs)
    header = schema_notation(before.tools[0].input_schema) + "\n"
    assert before.messages[1].content == header + after.messages[1].content
    data = json.JSONDecoder().raw_decode(after.messages[1].content.split("[UNTRUSTED DATA]\n", 1)[1])[0]
    assert data["previous_review"] == original
    assert data["diagnostics"] == kwargs["diagnostics"]


def test_editor_request_is_byte_identical(cases):
    inputs = RoleNoteReviewWorkflow.build_inputs(cases["attribution:1"][1])
    saved = json.loads((ROOT / "data/evaluation/results/golden_role_note_qualification_pair_result_v1.json")
        .read_text(encoding="utf-8"))["public_json_contents"]
    raw = compact(saved["transport/attribution-1/review/response-001.json"]["tool_calls"][0]["arguments"])
    _, accepted, _ = RoleNoteReviewWorkflow.validate_review(raw, inputs)
    assert RoleToolDeliveryReviewWorkflow.make_request(inputs, accepted=accepted) == (
        RoleNoteReviewWorkflow.make_request(inputs, accepted=accepted))


def test_legacy_first_request_matches_frozen_original_bytes(cases):
    evidence = json.loads((ROOT / "data/evaluation/results/golden_role_note_qualification_pair_result_v1.json")
        .read_text(encoding="utf-8"))
    for key in ("attribution:1", "claim-scope:1"):
        inputs = RoleNoteReviewWorkflow.build_inputs(cases[key][1])
        raw = validate_request(RoleNoteReviewWorkflow.make_request(inputs), transport_id=REVIEW_MODEL_TRANSPORT_ID)
        path = key.replace(":", "-") + "-prepared-request.json"
        assert hashlib.sha256(raw).hexdigest() == evidence["original_file_sha256"][path]
        projected = json.loads(raw)
        for message in projected["messages"]:
            assert message.pop("reasoning_content", None) in (None, "")
        assert projected == evidence["public_json_contents"][path]


def test_real_legacy_correction_replays_exact_journals_but_cannot_qualify_current(cases):
    # Committed public business projections suffice for semantic replay. Private
    # reasoning and local ignored runs are neither needed nor reconstructed.
    evidence = json.loads((ROOT / "data/evaluation/results/golden_role_note_qualification_pair_result_v1.json")
        .read_text(encoding="utf-8"))
    saved = evidence["public_json_contents"]
    expected = evidence["qualification_replay"]["attribution:1"]
    calls = []
    for ordinal, role in ((1, "review"), (2, "generation"), (3, "review")):
        prefix = f"transport/attribution-1/{role}"
        raw = saved[f"{prefix}/request-{ordinal:03d}.json"]
        request = REQUEST.validate_json(json.dumps(raw))
        request = replace(request, **{k: raw[k] for k in ("temperature", "timeout_s", "top_p")})
        calls.append(dict(request=request,
            response=RESPONSE.validate_json(json.dumps(saved[f"{prefix}/response-{ordinal:03d}.json"])),
            binding=saved[f"transport/attribution-1/call-{ordinal:03d}.json"],
            artifact_sha256=expected["artifact_sha256"][ordinal - 1]))
    frozen, source = cases["attribution:1"]
    actual = replay_legacy_note_case(frozen, source, calls)
    assert actual == {k: expected[k] for k in actual}
    # The default must not downgrade from old metadata, even for a real accepted
    # history with the same business schema and nominal contract version.
    with pytest.raises(ValueError, match="role_qualification_replayed_request_mismatch"):
        replay_case(frozen, source, calls)
