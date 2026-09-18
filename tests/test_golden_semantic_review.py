"""Synthetic native-review control flow; no test proves model semantic quality."""
from copy import deepcopy
from dataclasses import replace

import pytest

from app.evaluation import golden_semantic_review as candidate
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_semantic_sources import source_catalog
from app.harness.steps import EvaluationRequest, RevisionRequest, KnowledgeEvidence, KnowledgeCitation
from app.providers.errors import ProviderResponseError
from app.report_validation import COACH_REPORT_HEADINGS
from tests.test_golden_fact_candidate import summary
from tests.test_golden_integrated_review import ReplayProvider
from tests.test_golden_review_source_catalog import source_input


def source_id(inputs, key="source/official_patch"):
    return next(n for n, entry in source_catalog(inputs).items() if entry.key == key)


def fragment_inputs(report="官方补丁16.17。"):
    """Pure patch fragments intentionally have no retrieved coaching knowledge."""
    return candidate.NativeBusinessReviewWorkflow.build_inputs(evaluation_request(report))


def retrieved_knowledge():
    citation = KnowledgeCitation(citation_id="K1", chunk_id="single-match-check", parent_id=None,
        source_id="review-method.md", title="单局核对", content="建议核对单局实际证据；单局不能证明长期能力。")
    return KnowledgeEvidence(context=citation.content, source_ids=(citation.source_id,), citations=(citation,))


def problem(**changes):
    result = dict(severity="medium", category="fact_error", explanation="报告补丁与官方来源字段不一致。",
        suggested_correction="按来源改为16.17。")
    result.update(changes)
    return result


def opinion(inputs, *, failed=False):
    root = source_id(inputs)
    knowledge = {entry.key: n for n, entry in source_catalog(inputs).items() if entry.kind == "knowledge"}
    rows = [dict(block=n, kind="navigation" if text.startswith("#") else "content",
        source_ids=[] if text.startswith("#") else [knowledge.get("knowledge/K1", root) if "[K1]" in text else root],
        explanation="合成来源判断，只证明协议可达，不证明这段话已获语义核实。", issues=[])
        for n, (_, text) in enumerate(inputs.source.blocks, 1)]
    if failed:
        next(r for r in rows if r["kind"] == "content")["issues"] = [problem()]
    return dict(reviews=rows, score=70 if failed else 95, verdict="needs_revision" if failed else "pass",
        summary="脚本化评估", passed_checks=[], issue_resolutions=[])


def request_data(request):
    return candidate.strict_json(request.messages[1].content.split("[UNTRUSTED DATA]\n")[1].split("\n[END UNTRUSTED DATA]")[0])


def evaluation_request(report="官方补丁16.17。", *, knowledge=None):
    data = candidate.strict_json(source_input().data_json)
    return EvaluationRequest(summary(), data["deterministic_source_facts"], knowledge or KnowledgeEvidence.empty(), report,
        "复核观摩报告；观摩对象不是阅读者本人。")


def flow_with(replies, *, clock=None):
    provider = ReplayProvider(lambda _, n: replies[n - 1])
    sender = BudgetedReviewSender(provider, clock=clock)
    return candidate.NativeBusinessReviewWorkflow(sender), provider, sender


def resolution(inputs, *, disposition="retained", final_issue=1, previous_id=1):
    return dict(previous_id=previous_id, disposition=disposition, final_issue=final_issue,
        source_ids=[source_id(inputs)], explanation="根据原始来源明确处置首评问题。")


def test_complete_out_of_order_blocks_keep_actual_sources_and_original_raw():
    inputs = fragment_inputs("## 来源\n\n官方补丁16.17。\n\n当前补丁16.17。")
    value = opinion(inputs)
    value["reviews"].reverse()
    raw = compact(value)
    payload, _, journal = candidate.validate(raw, inputs)
    assert payload.verdict == "pass" and journal["raw"] == raw
    assert journal["raw_sha256"] == digest(raw)
    assert [r["block"] for r in journal["selected_sources"]] == [3, 2, 1]
    selected = journal["selected_sources"][0]["selected_sources"][0]
    assert selected["key"] == "source/official_patch" and selected["kind"] == "official_patch"
    assert selected["value"]["patch_version"] == "16.17"
    assert not journal["semantic_approval"] and not journal["production_admitted"]


@pytest.mark.parametrize("change", ["missing", "duplicate", "unknown"])
def test_block_inventory_cannot_omit_duplicate_or_invent_a_block(change):
    inputs = fragment_inputs("## 来源\n\n官方补丁16.17。")
    value = opinion(inputs)
    if change == "missing": value["reviews"].pop()
    if change == "duplicate": value["reviews"].append(deepcopy(value["reviews"][0]))
    if change == "unknown": value["reviews"][1]["block"] = 3
    with pytest.raises(ValueError, match="native_block_inventory"):
        candidate.validate(compact(value), inputs)


def test_body_cannot_escape_review_as_navigation_and_navigation_cannot_hide_issues():
    inputs = fragment_inputs("## 来源\n\n官方补丁16.17。")
    value = opinion(inputs)
    value["reviews"][1]["kind"] = "navigation"
    with pytest.raises(ValueError, match="native_navigation_not_heading"):
        candidate.validate(compact(value), inputs)
    value = opinion(inputs)
    value["reviews"][0]["issues"] = [problem()]
    with pytest.raises(ValueError, match="native_navigation_not_heading"):
        candidate.validate(compact(value), inputs)


@pytest.mark.parametrize("change,code", [("pass_with_issues", "pass_with_issues"),
    ("revision_without_issues", "revision_without_issues"), ("empty_sources", "native_supported_source_required"),
    ("unknown_source", "semantic_source_id_unknown"), ("duplicate_source", "semantic_source_ids_duplicate")])
def test_verdict_and_selected_source_contracts_are_enforced(change, code):
    inputs = fragment_inputs()
    value = opinion(inputs)
    if change == "pass_with_issues": value["reviews"][0]["issues"] = [problem()]
    if change == "revision_without_issues": value["verdict"] = "needs_revision"
    if change == "empty_sources": value["reviews"][0]["source_ids"] = []
    if change == "unknown_source": value["reviews"][0]["source_ids"] = [999]
    if change == "duplicate_source": value["reviews"][0]["source_ids"] *= 2
    with pytest.raises(ValueError, match=code): candidate.validate(compact(value), inputs)


def test_no_evidence_can_be_reported_as_a_problem_without_fabricated_source():
    inputs = fragment_inputs()
    value = opinion(inputs, failed=True)
    value["reviews"][0]["source_ids"] = []
    payload, _, journal = candidate.validate(compact(value), inputs)
    assert payload.verdict == "needs_revision" and payload.issues
    assert journal["selected_sources"][0]["selected_sources"] == []


@pytest.mark.parametrize("case,code", [("missing", "native_missing_knowledge_citation_unreported"),
    ("invented_id", "native_unknown_knowledge_citation_unreported"),
    ("no_retrieval", "native_unknown_knowledge_citation_unreported")])
def test_pass_cannot_ignore_supplied_knowledge_or_invent_citation_markers(case, code):
    text = "建议核对单局。" if case == "missing" else "建议核对单局。[K2]" if case == "invented_id" else "建议核对单局。[K1]"
    knowledge = KnowledgeEvidence.empty() if case == "no_retrieval" else retrieved_knowledge()
    req = evaluation_request(text, knowledge=knowledge)
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(req)
    with pytest.raises(ValueError, match=code): candidate.validate(compact(opinion(inputs)), inputs)


def test_actual_retrieved_citation_is_bound_to_original_knowledge_in_final_ledger():
    req = evaluation_request("建议核对单局。[K1]", knowledge=retrieved_knowledge())
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(req)
    value = opinion(inputs)
    payload, _, journal = candidate.validate(compact(value), inputs)
    assert payload.verdict == "pass"
    selected = journal["selected_sources"][0]["selected_sources"][0]
    assert selected["key"] == "knowledge/K1" and selected["kind"] == "knowledge"
    assert selected["value"]["content"] == req.knowledge.citations[0].content
    assert not journal["semantic_approval"]  # Existence alone does not certify relevance.


def test_missing_citation_can_be_reported_by_correction_without_mutating_the_report():
    req = evaluation_request("建议核对单局。", knowledge=retrieved_knowledge())
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(req)
    initial, corrected = opinion(inputs), opinion(inputs, failed=True)
    corrected["reviews"][0]["source_ids"] = [source_id(inputs, "knowledge/K1")]
    corrected["reviews"][0]["issues"] = [problem(category="other",
        explanation="建议使用了所提供的单局核对知识，但没有标明引用。",
        suggested_correction="核对建议与知识内容后添加实际K1引用。")]
    flow, provider, _ = flow_with([compact(initial), compact(corrected)])
    result = flow.evaluate(req)
    assert result.verdict.value == "needs_revision" and len(provider.requests) == 2
    assert result.issues[0]["quote"] == req.report
    assert flow.last_journal["report_sha256"] == digest(req.report)
    assert flow.last_feedback == [{"code": "native_missing_knowledge_citation_unreported"}]


def test_valid_review_completes_with_one_provider_call_and_no_compulsory_second_opinion():
    req = evaluation_request()
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(req)
    raw = compact(opinion(inputs))
    flow, provider, sender = flow_with([raw])
    result = flow.evaluate(req)
    assert result.verdict.value == "pass"
    assert flow.calls == sender.budget.calls == len(provider.requests) == 1
    assert flow.last_journal["raw"] == raw and flow.last_journal["previous_raw"] is None
    with pytest.raises(ValueError, match="order_invalid"): flow.evaluate(req)
    assert len(provider.requests) == 1


@pytest.mark.parametrize("change", ["schema", "contract"])
def test_one_complete_correction_retains_first_raw_and_diagnostics(change):
    req = evaluation_request()
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(req)
    first, final = opinion(inputs), opinion(inputs)
    if change == "schema":
        first["score"] = "95"
        first["untrusted_extra"] = {"keep": "完整首评字段"}
    else:
        first["reviews"][0]["source_ids"] = []
    raw = compact(first)
    flow, provider, _ = flow_with([raw, compact(final)])
    result = flow.evaluate(req)
    assert result.verdict.value == "pass" and len(provider.requests) == 2
    correction = request_data(provider.requests[1])
    assert correction["previous_raw_sha256"] == digest(raw) and correction["previous_review"] == first
    assert "previous_raw" not in correction  # Raw bytes stay in the journal; no duplicate prompt copy.
    assert correction["diagnostics"] and flow.last_journal["previous_raw"] == raw
    if change == "contract": assert correction["diagnostics"] == [{"code": "native_supported_source_required"}]


@pytest.mark.parametrize("change", ["bad_json", "conflicting_keys", "high_injection"])
def test_terminal_first_response_never_spends_a_correction_call(change):
    req = evaluation_request()
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(req)
    value = opinion(inputs)
    if change == "high_injection":
        value["score"] = "also malformed"
        value["reviews"][0]["issues"] = [problem(category="prompt_injection", severity="high")]
    raw = compact(value)
    if change == "bad_json": raw = raw[:-1]
    if change == "conflicting_keys": raw = '{"score":0,' + raw[1:]
    flow, provider, _ = flow_with([raw])
    with pytest.raises(ValueError): flow.evaluate(req)
    assert flow.stopped and len(provider.requests) == 1
    with pytest.raises(ValueError): flow.evaluate(req)
    assert len(provider.requests) == 1


def test_second_invalid_response_stops_without_third_attempt():
    req = evaluation_request()
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(req)
    value = opinion(inputs)
    value["score"] = "95"
    flow, provider, _ = flow_with([compact(value), compact(value)])
    with pytest.raises(ValueError): flow.evaluate(req)
    assert flow.stopped and len(provider.requests) == 2
    with pytest.raises(ValueError): flow.evaluate(req)


@pytest.mark.parametrize("disposition", ["retained", "replaced", "withdrawn"])
def test_all_first_issues_need_explicit_disposition_with_real_sources(disposition):
    inputs = fragment_inputs()
    before = opinion(inputs, failed=True)
    final = deepcopy(before)
    if disposition == "replaced": final["reviews"][0]["issues"][0]["explanation"] = "纠正后的具体问题。"
    if disposition == "withdrawn": final = opinion(inputs)
    with pytest.raises(ValueError, match="native_issue_resolution_inventory"):
        candidate.validate(compact(final), inputs, previous_raw=compact(before))
    final["issue_resolutions"] = [resolution(inputs, disposition=disposition,
        final_issue=None if disposition == "withdrawn" else 1)]
    payload, _, journal = candidate.validate(compact(final), inputs, previous_raw=compact(before))
    assert payload.verdict == ("pass" if disposition == "withdrawn" else "needs_revision")
    assert journal["previous_issues"][0]["issue"] == before["reviews"][0]["issues"][0]
    final["issue_resolutions"][0]["source_ids"] = [999]
    with pytest.raises(ValueError, match="semantic_source_id_unknown"):
        candidate.validate(compact(final), inputs, previous_raw=compact(before))


@pytest.mark.parametrize("change", ["content", "source", "wrong_target", "duplicate_resolution", "withdrawal_target"])
def test_issue_disposition_cannot_misrepresent_retention_or_point_to_nonexistent_issue(change):
    inputs = fragment_inputs()
    before = opinion(inputs, failed=True)
    final = deepcopy(before)
    final["issue_resolutions"] = [resolution(inputs)]
    if change == "content": final["reviews"][0]["issues"][0]["explanation"] = "不能称作原样保留。"
    if change == "source": final["reviews"][0]["source_ids"] = [source_id(inputs, "source/data_dragon")]
    if change == "wrong_target": final["issue_resolutions"][0]["final_issue"] = 2
    if change == "duplicate_resolution": final["issue_resolutions"] *= 2
    if change == "withdrawal_target": final["issue_resolutions"][0]["disposition"] = "withdrawn"
    with pytest.raises(ValueError): candidate.validate(compact(final), inputs, previous_raw=compact(before))


def test_malformed_and_legacy_first_findings_are_not_lost_during_correction():
    inputs = fragment_inputs()
    before = opinion(inputs)
    before["reviews"][0]["issues"] = ["malformed original finding"]
    before["issues"] = [dict(problem(), unexpected="legacy extra value")]
    final = opinion(inputs, failed=True)
    final["issue_resolutions"] = [resolution(inputs, disposition="replaced"),
        resolution(inputs, disposition="withdrawn", final_issue=None, previous_id=2)]
    _, _, journal = candidate.validate(compact(final), inputs, previous_raw=compact(before))
    assert journal["previous_issues"][0]["issue"] == "malformed original finding"
    assert journal["previous_issues"][1]["issue"] == before["issues"][0]


def test_recursive_malformed_issue_containers_preserve_every_identifiable_finding():
    req = evaluation_request()
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(req)
    before = dict(reviews={"unexpected": {"block": 1, "issues": "原始非列表问题"}},
        extra={"nested": {"issues": [dict(problem(), extra="保留嵌套原值")]}})
    final = opinion(inputs)
    final["issue_resolutions"] = [resolution(inputs, disposition="withdrawn", final_issue=None, previous_id=n)
        for n in (1, 2)]
    flow, provider, _ = flow_with([compact(before), compact(final)])
    assert flow.evaluate(req).verdict.value == "pass"
    previous = request_data(provider.requests[1])["previous_issues"]
    assert [entry["issue"] for entry in previous] == ["原始非列表问题", before["extra"]["nested"]["issues"][0]]
    assert flow.last_journal["previous_issues"] == previous


@pytest.mark.parametrize("container", ["nonlist_issues", "malformed_reviews", "unrelated_nested_field"])
def test_high_injection_cannot_hide_inside_malformed_first_containers(container):
    req = evaluation_request()
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(req)
    before = opinion(inputs)
    injected = problem(category="prompt_injection", severity="high")
    if container == "nonlist_issues": before["reviews"][0]["issues"] = injected
    if container == "malformed_reviews": before["reviews"] = {"unexpected": {"issues": injected}}
    if container == "unrelated_nested_field": before["unexpected"] = {"nested": [injected]}
    flow, provider, _ = flow_with([compact(before)])
    with pytest.raises(ValueError, match="native_security_terminal"): flow.evaluate(req)
    assert flow.stopped and len(provider.requests) == 1


def test_direct_validation_cannot_withdraw_a_previous_high_injection_outside_workflow():
    inputs = fragment_inputs()
    before = opinion(inputs, failed=True)
    before["reviews"][0]["issues"] = [problem(category="prompt_injection", severity="high")]
    final = opinion(inputs)
    final["issue_resolutions"] = [resolution(inputs, disposition="withdrawn", final_issue=None)]
    with pytest.raises(ValueError, match="native_security_terminal"):
        candidate.validate(compact(final), inputs, previous_raw=compact(before))


def test_workflow_compiles_validated_opgg_roots_and_rejects_invalid_snapshot_before_io():
    from app.evaluation.golden_contextual_sources import MARKER
    from app.evaluation.golden_integrated_review import ReviewInput
    from tests.test_golden_contextual_recovery import external

    req = evaluation_request()
    prefix, encoded = req.deterministic_report.split(MARKER)
    sources = candidate.strict_json(encoded)
    sources["opgg"] = external()["opgg"]
    req = replace(req, deterministic_report=prefix + MARKER + compact(sources))
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(req)
    key = "legacy/external:opgg:00:00"
    external_id = source_id(inputs, key)
    assert len(source_catalog(inputs)) == len(source_catalog(ReviewInput.build(req))) + 1
    value = opinion(inputs)
    value["reviews"][0]["source_ids"] = [external_id]
    flow, provider, _ = flow_with([compact(value)])
    assert flow.evaluate(req).verdict.value == "pass"
    selected = flow.last_journal["selected_sources"][0]["selected_sources"][0]
    assert selected["key"] == key and selected["value"]["champion"] == "Syndra"
    assert selected["value"]["allowed_uses"] == ["current_snapshot_recommendation"]
    sources["opgg"][0]["expires_at"] = sources["opgg"][0]["retrieved_at"]
    bad_req = replace(req, deterministic_report=prefix + MARKER + compact(sources))
    blocked, unused, _ = flow_with([])
    with pytest.raises(ValueError, match="contextual_external_source_invalid"): blocked.evaluate(bad_req)
    assert not unused.requests


@pytest.mark.parametrize("corrected", [False, True])
def test_three_or_five_call_revision_recheck_uses_same_sources_and_actual_native_evaluation(corrected):
    bad, good = "官方补丁16.18。", "官方补丁16.17。"
    report = "\n\n".join(COACH_REPORT_HEADINGS) + "\n\n" + bad + "\n\n建议核对单局。[K1]"
    fixed = report.replace(bad, good)
    req = evaluation_request(report, knowledge=retrieved_knowledge())
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(req)
    fixed_inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(replace(req, report=fixed))
    first, final = opinion(inputs, failed=True), opinion(fixed_inputs)
    replies = [compact(first), fixed, compact(final)]
    if corrected:
        broken_first, broken_final = deepcopy(first), deepcopy(final)
        broken_first["score"] = "70"
        broken_final["score"] = "95"
        first["issue_resolutions"] = [resolution(inputs)]
        replies = [compact(broken_first), compact(first), fixed, compact(broken_final), compact(final)]
    flow, provider, sender = flow_with(replies)
    initial = flow.evaluate(req)
    assert initial.verdict.value == "needs_revision"
    revision = RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, report, initial)
    # Equal-looking evaluations from another execution are not accepted identities.
    with pytest.raises(ValueError, match="revision_order_invalid"):
        flow.revise(replace(revision, evaluation=replace(initial)))
    with pytest.raises(ValueError, match="revision_source_changed"):
        flow.revise(replace(revision, deterministic_report="changed"))
    draft = flow.revise(revision)
    revision_request = provider.requests[2 if corrected else 1]
    assert request_data(revision_request)["accepted_review"] == first
    with pytest.raises(ValueError, match="recheck_source_changed"):
        flow.evaluate(replace(req, report=draft.report, user_utterance="changed"))
    accepted = flow.evaluate(replace(req, report=draft.report))
    assert accepted.verdict.value == "pass"
    expected = 5 if corrected else 3
    assert flow.calls == sender.budget.calls == len(provider.requests) == expected
    assert sender.budget.tokens == expected * 20
    assert flow.last_journal["report_sha256"] == digest(fixed)
    assert not flow.last_journal["semantic_approval"]
    with pytest.raises(ValueError): flow.revise(revision)
    with pytest.raises(ValueError): flow.evaluate(req)
    assert len(provider.requests) == expected


def test_mutated_accepted_evaluation_is_rejected_before_revision_io():
    req = evaluation_request("官方补丁16.18。")
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(req)
    flow, provider, _ = flow_with([compact(opinion(inputs, failed=True))])
    result = flow.evaluate(req)
    result.issues[0]["explanation"] = "forged nested value"
    revision = RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, result)
    with pytest.raises(ValueError, match="accepted_evaluation_changed"): flow.revise(revision)
    assert len(provider.requests) == 1


def test_total_deadline_exhaustion_stops_before_revision_provider_call():
    now = [0]
    req = evaluation_request("官方补丁16.18。")
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(req)
    flow, provider, _ = flow_with([compact(opinion(inputs, failed=True))], clock=lambda: now[0])
    initial = flow.evaluate(req)
    now[0] = 901
    with pytest.raises(ProviderResponseError, match="timeout"):
        flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, initial))
    assert flow.stopped and len(provider.requests) == 1


def test_oversized_first_opinion_cannot_trigger_over_budget_second_request():
    req = evaluation_request()
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(req)
    first = opinion(inputs)
    first["reviews"][0]["explanation"] = "必须保留的首评长原值" * 20000
    flow, provider, _ = flow_with([compact(first)])
    with pytest.raises(ValueError, match="request_budget_exceeded"): flow.evaluate(req)
    assert flow.stopped and len(provider.requests) == 1
