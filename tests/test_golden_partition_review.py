"""Partition contracts and known semantic limits; all judgments are scripted."""
from copy import deepcopy
from dataclasses import replace

import pytest
from pydantic import ValidationError

from app.evaluation import golden_partition_review as candidate
from app.evaluation.golden_bounded_correction_requests import source_data
from app.evaluation.golden_contextual_requests import restore
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_review_experiment import compact
from tests.test_golden_bounded_correction import issue
from tests.test_golden_comparison_reassessment import assessment, inputs_for
from tests.test_golden_typed_review import check, source_scenario, values


def source_choices(references):
    """The scripted model chooses addresses; native kinds remain in fixtures."""
    choices = deepcopy(references)
    for reference in choices: reference.pop("kind")
    return choices


def packets(inputs, native):
    """Explicit synthetic model packets, with no model-produced operand lists."""
    output = []
    for index, assigned in enumerate(candidate.allocation(inputs)):
        value = dict(
            heading_reviews=[deepcopy(h) for h in native["heading_reviews"] if h["block_id"] in assigned],
            audits=[dict(kind=a["kind"], claims=[deepcopy(c) for c in a["claims"]
                if c["quote_ref"]["block"] in assigned]) for a in native["audits"]],
            source_checks=[deepcopy(c) for c in native["source_checks"] if c["quote_ref"]["block"] in assigned],
            issues=[deepcopy(i) for i in native["issues"] if i["quote_ref"]["block"] in assigned],
        )
        for audit in value["audits"]:
            for claim in audit["claims"]:
                for operation in claim["comparisons"] + claim["summaries"]:
                    operation.pop("operand_refs")
        if index:
            value.update({k: deepcopy(native[k]) for k in ("issues", "score", "verdict", "summary", "passed_checks")})
            value.update(replacements=[], issue_resolutions=deepcopy(native["issue_resolutions"]))
        for source_check in value["source_checks"]:
            source_check["sources"] = source_choices(source_check["sources"])
            for literal in source_check["literals"]:
                literal["source"] = source_choices([literal["source"]])[0]
        for resolution in value.get("issue_resolutions", []):
            resolution["sources"] = source_choices(resolution["sources"])
        output.append(value)
    return output


def replacement(block, complete):
    return dict(block=block,
        heading_review=next((deepcopy(h) for h in complete["heading_reviews"] if h["block_id"] == block), None),
        audits=[dict(kind=a["kind"], claims=[deepcopy(c) for c in a["claims"]
            if c["quote_ref"]["block"] == block]) for a in complete["audits"]],
        source_checks=[deepcopy(c) for c in complete["source_checks"] if c["quote_ref"]["block"] == block])


def request_data(request):
    return strict_json(request.messages[1].content.split("[UNTRUSTED DATA]\n")[1].split("\n[END UNTRUSTED DATA]")[0])


def test_single_body_has_valid_empty_second_assignment_and_only_second_global_decision():
    inputs, _, native = source_scenario()
    first, second = packets(inputs, native)
    assert candidate.allocation(inputs) == ((1,), ())
    assert not {"score", "verdict", "summary", "passed_checks"}.intersection(first)
    second.update(score=91, summary="第二批核查首批及全篇后给出的裁决")
    result, journal = candidate.apply(candidate.prepare(compact(first), inputs), compact(second), inputs=inputs)
    assert result.score == 91 and result.summary == second["summary"]
    assert journal["provisional_values"] == first
    assert not journal["semantic_approval"] and not journal["live_qualified"]
    assert "score" not in candidate.request(inputs).response_contract.schema_dict()["properties"]
    assert "score" in candidate.request(inputs, state=candidate.prepare(compact(first), inputs)).response_contract.schema_dict()["properties"]


@pytest.mark.parametrize("defect", ["bad_reference", "duplicate_rows", "wrong_lane"])
def test_whole_block_replacement_corrects_first_defects_without_rewriting_history(defect):
    inputs, _, native = source_scenario()
    first, second = packets(inputs, native)
    complete = deepcopy(first)
    if defect == "bad_reference":
        first["source_checks"][0]["quote_ref"].update(head="不存在的长引用" * 10)
        first["source_checks"][0]["unexpected"] = ["preserve", {"nested": True}]
    elif defect == "duplicate_rows":
        first["source_checks"].append(deepcopy(first["source_checks"][0]))
    else:
        first["source_checks"] = []
        first["audits"][0]["claims"] = [dict(quote_ref=dict(block=1),
            decision="wrong provisional category", evidence_refs=[1], explanation="首批错分，仍需完整纠正")]
    raw = compact(first)
    state = candidate.prepare(raw, inputs)
    # Admission must not revalidate the imperfect first packet strictly.
    data = request_data(candidate.request(inputs, state=state))
    assert candidate.table_partial(data["first_partial"], restore=True) == first
    with pytest.raises(ValueError): candidate.apply(state, compact(second), inputs=inputs)
    second["replacements"] = [replacement(1, complete)]
    result, journal = candidate.apply(state, compact(second), inputs=inputs)
    assert result.verdict == "pass"
    assert journal["first_raw"] == raw and journal["provisional_values"] == first
    assert len(journal["source_checks"]) == 1
    assert all(not audit.claims for audit in result.audits)


def test_unauthorized_first_global_fields_are_preserved_only_as_provisional_extras():
    inputs, _, native = source_scenario()
    first, second = packets(inputs, native)
    first.update(score=0, verdict="fail", summary="首批越权裁决，不得成为最终结论")
    state = candidate.prepare(compact(first), inputs)
    assert state.diagnostics
    result, journal = candidate.apply(state, compact(second), inputs=inputs)
    assert result.score == second["score"] and result.verdict == second["verdict"]
    assert journal["provisional_values"] == first


def test_identical_duplicate_first_keys_retained_but_final_duplicate_keys_rejected():
    inputs, _, native = source_scenario()
    first, second = packets(inputs, native)
    raw = compact(first).replace('"block":1', '"block":1,"block":1')
    state = candidate.prepare(raw, inputs)
    assert state.diagnostics and state.raw == raw
    _, journal = candidate.apply(state, compact(second), inputs=inputs)
    assert journal["first_raw"] == raw
    with pytest.raises(ValueError, match="compact_duplicate_key"):
        candidate.apply(state, '{"score":0,' + compact(second)[1:], inputs=inputs)


@pytest.mark.parametrize("defect", ["unknown_block", "conflicting_duplicate", "high_injection"])
def test_terminal_first_defects_stop_before_second_request(defect):
    inputs, _, native = source_scenario()
    first, _ = packets(inputs, native)
    if defect == "unknown_block": first["source_checks"][0]["quote_ref"]["block"] = 999
    if defect == "high_injection":
        first["issues"] = [dict(issue(inputs, inputs.source.report), category="prompt_injection", severity="high")]
    raw = compact(first)
    if defect == "conflicting_duplicate": raw = raw.replace('"block":1', '"block":1,"block":2')
    with pytest.raises(ValueError): candidate.prepare(raw, inputs)


def test_first_issue_cannot_disappear_and_bad_issue_values_survive_explicit_resolution():
    inputs, _, native = source_scenario()
    first, second = packets(inputs, native)
    old = issue(inputs, inputs.source.report, "fact_error")
    old["quote_ref"]["head"] = "错误且超过限长的首批定位" * 8
    old["extra"] = "原始错误字段必须保留"
    first["issues"] = [old]
    state = candidate.prepare(compact(first), inputs)
    data = request_data(candidate.request(inputs, state=state))
    assert candidate.table_partial(data["first_partial"], restore=True)["issues"] == [old]
    with pytest.raises(ValueError, match="issue_disposition"):
        candidate.apply(state, compact(second), inputs=inputs)
    second["issue_resolutions"] = [dict(target_id="i001", evidence_refs=[],
        sources=source_choices(native["source_checks"][0]["sources"]), explanation="原始官方补丁字段说明该首批问题是误报。")]
    _, journal = candidate.apply(state, compact(second), inputs=inputs)
    assert journal["resolved_issues"][0]["before"] == old
    expanded = strict_json(journal["native_final"])
    assert expanded["source_checks"] == native["source_checks"]
    assert expanded["issue_resolutions"][0]["sources"] == native["source_checks"][0]["sources"]


@pytest.mark.parametrize("location", ["source", "literal"])
@pytest.mark.parametrize("bad_key", ["unknown", "match_as_ordinary"])
def test_host_catalog_kinds_do_not_allow_unknown_or_match_sources_as_ordinary_facts(location, bad_key):
    inputs, _, native = source_scenario()
    first, second = packets(inputs, native)
    source_check = first["source_checks"][0]
    target = source_check["sources"][0] if location == "source" else source_check["literals"][0]["source"]
    if bad_key == "unknown":
        target["key"] = "source/does-not-exist"
    else:
        match = next(key for key in inputs.source.evidence_keys if key.startswith("facts:recent_match:"))
        target.update(key="legacy/" + match, path=[])
    # Address syntax is valid; host expansion must still obey the real catalog.
    candidate.Partial.model_validate(first, strict=True)
    expected = "review_source_unknown_key" if bad_key == "unknown" else "typed_source_match_requires_audit"
    with pytest.raises(ValueError, match=expected):
        candidate.apply(candidate.prepare(compact(first), inputs), compact(second), inputs=inputs)


@pytest.mark.parametrize("location", ["source", "literal"])
def test_unexpected_first_source_kind_requires_explicit_replacement_and_is_never_overwritten(location):
    inputs, _, native = source_scenario()
    first, second = packets(inputs, native)
    corrected = deepcopy(first)
    source_check = first["source_checks"][0]
    target = source_check["sources"][0] if location == "source" else source_check["literals"][0]["source"]
    target["kind"] = "external_snapshot"
    state = candidate.prepare(compact(first), inputs)
    assert state.diagnostics
    restored = candidate.table_partial(request_data(candidate.request(inputs, state=state))["first_partial"], restore=True)
    assert restored == first
    with pytest.raises(ValidationError):
        candidate.apply(state, compact(second), inputs=inputs)
    second["replacements"] = [replacement(1, corrected)]
    _, journal = candidate.apply(state, compact(second), inputs=inputs)
    assert journal["provisional_values"] == first
    assert strict_json(journal["native_final"])["source_checks"] == native["source_checks"]
    assert all(item["kind"] == "official_patch" for item in journal["source_kind_expansion"])


def test_full_body_in_both_assignments_required_even_when_first_omits_entire_block():
    inputs, _, native = source_scenario("官方补丁16.17。\n\n当前官方版本16.17。")
    native["source_checks"] = [check(dict(block=1)), check(dict(block=2))]
    first, second = packets(inputs, native)
    complete = deepcopy(first)
    first["source_checks"] = []
    state = candidate.prepare(compact(first), inputs)
    assert any(d["code"] == "omitted_first_body_blocks" for d in state.diagnostics)
    with pytest.raises(ValueError, match="reviewed_source_lost"):
        candidate.apply(state, compact(second), inputs=inputs)
    second["replacements"] = [replacement(1, complete)]
    candidate.apply(state, compact(second), inputs=inputs)
    second["source_checks"] = []
    with pytest.raises(ValueError, match="reviewed_source_lost"):
        candidate.apply(state, compact(second), inputs=inputs)


def test_correct_prefix_cannot_hide_unreviewed_tail_in_a_body_block():
    inputs, _, native = source_scenario("官方补丁16.17。以后必定相同。")
    native["source_checks"][0]["quote_ref"] = dict(block=1, head="官方补丁16.17。")
    first, second = packets(inputs, native)
    with pytest.raises(ValueError, match="reviewed_source_lost"):
        candidate.apply(candidate.prepare(compact(first), inputs), compact(second), inputs=inputs)


def test_navigation_heading_can_be_corrected_and_assertion_cannot_escape_audit():
    inputs, _, native = source_scenario("## 资料\n\n官方补丁16.17。")
    native["heading_reviews"] = [dict(block_id=1, kind="navigation")]
    native["source_checks"][0]["quote_ref"] = dict(block=2)
    first, second = packets(inputs, native)
    complete = deepcopy(first)
    first["heading_reviews"][0]["kind"] = "invalid provisional classification"
    second["replacements"] = [replacement(1, complete)]
    state = candidate.prepare(compact(first), inputs)
    result, _ = candidate.apply(state, compact(second), inputs=inputs)
    assert result.verdict == "pass"
    second["replacements"][0]["heading_review"]["kind"] = "assertion"
    with pytest.raises(ValueError): candidate.apply(state, compact(second), inputs=inputs)


@pytest.mark.parametrize("defect", ["foreign_replacement", "cross_block_content", "duplicate_replacement"])
def test_replacement_cannot_change_another_assigned_block_or_replace_twice(defect):
    inputs, _, native = source_scenario("官方补丁16.17。\n\n当前官方版本16.17。")
    native["source_checks"] = [check(dict(block=1)), check(dict(block=2))]
    first, second = packets(inputs, native)
    change = replacement(1, first)
    if defect == "foreign_replacement": change["block"] = 2
    if defect == "cross_block_content": change["source_checks"][0]["quote_ref"]["block"] = 2
    second["replacements"] = [change, deepcopy(change)] if defect == "duplicate_replacement" else [change]
    with pytest.raises(ValueError):
        candidate.apply(candidate.prepare(compact(first), inputs), compact(second), inputs=inputs)


def test_host_uses_selected_cohort_without_inventing_missing_evidence_citations():
    inputs = inputs_for()
    _, native = values(inputs)
    first, second = packets(inputs, native)
    claim = first["audits"][1]["claims"][0]
    missing_ref = claim["evidence_refs"].pop()
    expanded, ledger = candidate.expand_operands(first, inputs)
    assert missing_ref in expanded["audits"][1]["claims"][0]["comparisons"][0]["operand_refs"]
    assert missing_ref not in expanded["audits"][1]["claims"][0]["evidence_refs"]
    assert ledger[0]["cohort"] == "MIDDLE"
    with pytest.raises(ValueError):
        candidate.apply(candidate.prepare(compact(first), inputs), compact(second), inputs=inputs)


def test_wrong_same_direction_sample_can_pass_structure_but_never_claims_semantic_approval():
    inputs = inputs_for()
    _, native = values(inputs)
    _, wrong = assessment(inputs, cohort="selected")
    native["audits"] = wrong["audits"]
    for audit in native["audits"]:
        for claim in audit["claims"]: claim["summaries"] = []
    first, second = packets(inputs, native)
    result, journal = candidate.apply(candidate.prepare(compact(first), inputs), compact(second), inputs=inputs)
    assert result.verdict == "pass"
    assert all(item["cohort"] == "selected" for item in journal["operand_expansion"])
    assert not journal["semantic_approval"] and not journal["live_qualified"]
    # Four MIDDLE is the report's real scope; host arithmetic cannot choose it.


@pytest.mark.parametrize("defect", ["source", "state_value", "state_diagnostics"])
def test_changed_input_or_provisional_state_cannot_be_reused(defect):
    inputs, _, native = source_scenario()
    first, second = packets(inputs, native)
    state = candidate.prepare(compact(first), inputs)
    if defect == "source": inputs = replace(inputs, data_json=inputs.data_json + " ")
    if defect == "state_value": state = replace(state, value_json=state.value_json + " ")
    if defect == "state_diagnostics": state = replace(state, diagnostics=({"forged": True},))
    with pytest.raises(ValueError, match="partition_state_changed"):
        candidate.request(inputs, state=state)
    with pytest.raises(ValueError, match="partition_state_changed"):
        candidate.apply(state, compact(second), inputs=inputs)


def test_both_requests_preserve_all_source_context_and_provisional_extras():
    inputs, _, native = source_scenario()
    first, _ = packets(inputs, native)
    first["extra"] = {"keep": [1, "untrusted provisional value"]}
    first["source_checks"][0]["extra"] = {"nested": "unchanged"}
    state = candidate.prepare(compact(first), inputs)
    for request in (candidate.request(inputs), candidate.request(inputs, state=state)):
        data = request_data(request)
        data["deterministic_source_facts"] = strict_json(inputs.data_json)["deterministic_source_facts"]
        restored = restore(data)
        for key, value in source_data(inputs).items(): assert restored[key] == value
    projected = request_data(candidate.request(inputs, state=state))["first_partial"]
    assert candidate.table_partial(projected, restore=True) == first


@pytest.mark.parametrize("field", ["quote_ref", "scope_source"])
def test_nested_reference_projection_preserves_missing_null_malformed_and_extra_values(field):
    inputs = inputs_for()
    _, native = values(inputs)
    first, _ = packets(inputs, native)
    original = first["audits"][1]["claims"][0]
    reference_shapes = [None, {}, {"block": 1}, {"block": 1, "head": None},
        {"block": 1, "tail": "without head"}, {"block": 1, "head": "a", "tail": None},
        {"block": 1, "head": "a", "extra": {"nested": [2, 1]}},
        {"Block": 1}, {"block": "1"}, {"unparsed": ["original", "wrapper-shaped value"]},
        [1, "a", "b"], "not an object", False]
    missing = deepcopy(original)
    missing.pop(field, None)
    missing["explanation"] = "missing field must remain missing"
    first["audits"][1]["claims"] = [missing] + [dict(deepcopy(original),
        **{field: ref, "explanation": f"original position {index}"})
        for index, ref in enumerate(reference_shapes)]
    untouched = deepcopy(first)
    projected = candidate.table_partial(first)
    restored = candidate.table_partial(projected, restore=True)
    assert first == untouched  # Projection must not mutate stored original values.
    assert restored == untouched  # Includes missing versus null and exact list order.
    assert field not in restored["audits"][1]["claims"][0]


@pytest.mark.parametrize("field", ["comparisons", "summaries"])
def test_nested_operation_projection_preserves_bad_shapes_duplicates_and_order(field):
    inputs = inputs_for()
    _, native = values(inputs)
    first, _ = packets(inputs, native)
    template = first["audits"][1]["claims"][0]
    valid = dict(cohort="MIDDLE", metric="gold_per_min")
    if field == "summaries": valid.update(operation="mean", reported="8.91")
    variants = [deepcopy(valid), None, {}, "not an operation", ["MIDDLE", "gold_per_min"],
        {"cohort": "MIDDLE"}, dict(valid, Metric=valid["metric"]),
        dict(valid, extra={"operand_refs": [6, 2, 4, 5]}),
        {"unparsed": {"cohort": "TOP"}}, deepcopy(valid)]
    missing = deepcopy(template)
    missing.pop(field)
    first["audits"][1]["claims"] = [missing] + [dict(deepcopy(template),
        **{field: value, "explanation": f"original shape {index}"})
        for index, value in enumerate([None, "not a list", {"wrong": []}, variants])]
    untouched = deepcopy(first)
    projected = candidate.table_partial(first)
    assert candidate.table_partial(projected, restore=True) == untouched
    assert first == untouched


def test_individually_valid_batches_cannot_exceed_combined_native_source_capacity():
    report = "\n\n".join("【" + "甲" * n + "】官方补丁16.17。" for n in range(1, 35))
    inputs, _, native = source_scenario(report)
    native["source_checks"] = [check(dict(block=b)) for b in range(1, 35)]
    first, second = packets(inputs, native)
    sizes = [len(value["source_checks"]) for value in (first, second)]
    assert sum(sizes) == 34 and all(0 < count <= 32 for count in sizes)
    candidate.Partial.model_validate(first, strict=True)
    candidate.FinalPartial.model_validate(second, strict=True)
    state = candidate.prepare(compact(first), inputs)
    with pytest.raises(ValidationError) as failure:
        candidate.apply(state, compact(second), inputs=inputs)
    assert any(error["type"] == "too_long" and error["loc"] == ("source_checks",)
        for error in failure.value.errors())


def test_oversized_first_result_stops_before_second_provider_call():
    from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
    from tests.test_golden_comparison_workflow import make_request
    from tests.test_golden_integrated_review import ReplayProvider

    inputs, _, native = source_scenario()
    req = replace(make_request(inputs), deterministic_report=strict_json(inputs.data_json)["deterministic_source_facts"])
    first, _ = packets(inputs, native)
    first["source_checks"][0]["explanation"] = "长首批待核查原值不得被截断" * 30000
    provider = ReplayProvider(lambda *_: compact(first))
    flow = candidate.ComputedPartitionWorkflow(BudgetedReviewSender(provider))
    with pytest.raises(ValueError, match="request_budget_exceeded"):
        flow.evaluate(req)
    assert flow.stopped and len(provider.requests) == 1
    with pytest.raises(ValueError): flow.evaluate(req)
    assert len(provider.requests) == 1


def test_offline_status_blocks_runner_before_inputs_ci_credentials_or_provider(monkeypatch):
    from types import SimpleNamespace
    import dotenv
    from scripts import run_golden_integrated_review as runner

    monkeypatch.setattr(candidate, "LIVE_STATUS", "offline_only")
    monkeypatch.setattr(candidate, "LIVE_BLOCK_REASON", "test_partition_offline_hold")
    monkeypatch.setattr(runner, "load_inputs", lambda *_: pytest.fail("loaded inputs"))
    monkeypatch.setattr(runner, "verify_public_ci", lambda *_: pytest.fail("called CI"))
    monkeypatch.setattr(dotenv, "dotenv_values", lambda *_: pytest.fail("read credentials"))
    monkeypatch.setattr(runner, "ReceiptedStreamProvider", lambda **_: pytest.fail("constructed Provider"))
    with pytest.raises(ValueError, match=candidate.LIVE_BLOCK_REASON):
        runner.run(SimpleNamespace(execute=True), partition=True)


def test_five_call_workflow_revises_validated_native_review_and_rechecks_same_sources():
    from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
    from app.harness.steps import EvaluationRequest, RevisionRequest, KnowledgeEvidence
    from app.report_validation import COACH_REPORT_HEADINGS
    from tests.test_golden_fact_candidate import summary
    from tests.test_golden_integrated_review import ReplayProvider
    from tests.test_golden_review_source_catalog import source_input

    good, bad, advice = "官方补丁16.17。", "官方补丁16.18。", "建议核对单局。[K1]"
    report = "\n\n".join(COACH_REPORT_HEADINGS) + "\n\n" + bad + "\n\n" + advice
    revised = report.replace(bad, good)
    data = strict_json(source_input().data_json)
    req = EvaluationRequest(summary(), data["deterministic_source_facts"], KnowledgeEvidence.empty(), report, "检查观摩报告")
    inputs = candidate.ComputedPartitionWorkflow.build_inputs(req)
    corrected_inputs = candidate.ComputedPartitionWorkflow.build_inputs(replace(req, report=revised))

    def responses(current, text, failed):
        _, native = values(current)
        for audit in native["audits"]: audit["claims"] = []
        source_check = check(current.source.reference(text), reported="16.18" if failed else "16.17")
        source_check["disposition"] = "unsupported" if failed else "supported"
        native["source_checks"] = [source_check, dict(quote_ref=current.source.reference(advice),
            kind="advice", disposition="supported", literals=[],
            sources=[dict(key="source/deterministic", kind="source_declaration", path=[])],
            explanation="仅脚本化控制流样本，不证明这段建议受来源语义支持。")]
        if failed: native.update(issues=[issue(current, text, "fact_error")], verdict="needs_revision", score=70)
        return packets(current, native)

    first, second = responses(inputs, bad, True)
    fixed_first, fixed_second = responses(corrected_inputs, good, False)
    replies = [compact(first), compact(second), revised, compact(fixed_first), compact(fixed_second)]
    provider = ReplayProvider(lambda _, n: replies[n - 1])
    sender = BudgetedReviewSender(provider)
    flow = candidate.ComputedPartitionWorkflow(sender)
    initial = flow.evaluate(req)
    assert initial.verdict.value == "needs_revision"
    accepted, journal = candidate.apply(candidate.prepare(compact(first), inputs), compact(second), inputs=inputs)
    with pytest.raises(ValueError, match="evaluation_changed"):
        flow.build_revision(None, accepted.model_copy(update={"summary": "forged"}), inputs)
    draft = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, report, initial))
    sent = request_data(provider.requests[2])
    expected_review = candidate.typed.TypedReview.model_validate(strict_json(journal["native_final"]), strict=True)
    assert sent["accepted_evaluation"] == expected_review.model_dump(mode="json")
    with pytest.raises(ValueError, match="source_changed"):
        flow.evaluate(replace(req, report=draft.report, deterministic_report="changed"))
    assert len(provider.requests) == 3
    final = flow.evaluate(replace(req, report=draft.report))
    assert final.verdict.value == "pass"
    assert flow.calls == sender.budget.calls == len(provider.requests) == 5
    assert sender.budget.tokens == 100
    assert not flow.last_journal["semantic_approval"]
    with pytest.raises(ValueError): flow.evaluate(req)
