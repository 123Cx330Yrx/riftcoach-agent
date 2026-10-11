import json

from app.runtime.coach_context import CoachContextBuilder
from app.runtime.coach_contract import BATCH_COACH_CONTRACT
from tests.test_context_builder import validated_execution, demo_summary, demo_report


def test_compaction_preserves_every_fact_policy_and_match():
    execution = validated_execution(
        utterance="复盘最近几局", run_id="compact_offline_001",
        payload={"player_summary": demo_summary(), "deterministic_report": demo_report(), "focus": "overall"},
    )
    regular = CoachContextBuilder(coach_contract=BATCH_COACH_CONTRACT).build(execution)
    compact = CoachContextBuilder(coach_contract=BATCH_COACH_CONTRACT, compact_json=True).build(execution)
    assert compact.estimated_tokens < regular.estimated_tokens
    assert compact.max_context_tokens == regular.max_context_tokens
    assert compact.omitted_section_ids == regular.omitted_section_ids == ()
    assert [s.section_id for s in regular.sections] == [s.section_id for s in compact.sections]
    for left, right in zip(regular.sections, compact.sections):
        assert (left.trust, left.required, left.source) == (right.trust, right.required, right.source)
        if left.section_id.startswith("facts:") and left.section_id != "facts:deterministic_report":
            assert json.loads(left.content) == json.loads(right.content)
        else:
            assert left.content == right.content
    # Outer envelopes still point to the exact selected section content.
    emitted = [s for m in compact.messages for s in json.loads(m.content)["sections"]]
    assert {s["section_id"]: s["content"] for s in emitted} == {s.section_id: s.content for s in compact.sections}


def test_compact_option_goes_through_actual_application_and_quality_gate(tmp_path):
    from app.product.coach_composition import build_coach_application
    from tests.test_coach_application_composition import dependencies, product_request
    app = build_coach_application(**dependencies(), runs_root=tmp_path, compact_context_json=True)
    result = app.review(product_request(), run_id="compact_application_001")
    assert result.publication_status.value == "published", result.terminal_reason
    assert "[K1]" in result.output.report
