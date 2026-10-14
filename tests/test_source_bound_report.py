"""Responsibility/byte-binding witnesses, never model quality observations."""
from dataclasses import replace
import json
from pathlib import Path
import re

import pytest

from app.evaluation.source_bound_report import (
    SLOT, START, END, SourceBoundDraftPreparer, SourceBoundRoleWorkflow,
    assemble_report, knowledge_ledger,
)
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
from app.evaluation.golden_native_issues_review import build_inputs
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_role_review import RoleReviewWorkflow
from app.harness.models import ArtifactKind, HarnessConfig, RunStatus
from app.harness.runtime import ReviewHarness
from app.harness.steps import (
    CoachDraft, DraftPreparationResult, KnowledgeCitation, KnowledgeEvidence,
    KnowledgeRetrieval, RevisionRequest,
)
from app.harness.store import FileRunStore
from app.report_validation import COACH_REPORT_HEADINGS
from scripts.run_golden_native_review import prepare_claim_scope
from tests.test_golden_native_partitioned_tool_review import (
    exchange_provider, tool_response, valid_review,
)
from tests.test_native_editor_product_budget import offline


@pytest.fixture
def knowledge():
    return KnowledgeEvidence(context="视野分不证明因果。", source_ids=("review",), citations=(
        KnowledgeCitation("K1", "chunk1", "parent1", "review", "视野", "视野分不证明因果。",
            version="evergreen", updated_at="2026-07-23"),
        KnowledgeCitation("K2", "chunk2", "parent2", "review", "复盘", "需要复盘。"),
    ), retrievals=(
        KnowledgeRetrieval("local", "2026-09-23T07:31:33Z", ("chunk1",)),
        KnowledgeRetrieval("local", "2026-09-23T07:31:33Z", ("chunk1",)),
        KnowledgeRetrieval("legacy", None, ("chunk1",)),
        KnowledgeRetrieval("other", "2026-09-22T00:00:00Z", ()),
    ))


def template(text="仅描述所选比赛，不外推长期。[K1]"):
    return "\n\n".join(COACH_REPORT_HEADINGS) + "\n\n" + text + "\n\n" + SLOT + "\n"


def test_render_has_attributed_repeats_unknowns_and_no_implicit_citations(knowledge):
    ledger = knowledge_ledger(knowledge)
    k1, k2 = (line for line in ledger.splitlines() if line.startswith(("| K1", "| K2")))
    assert k1.count("2026-09-23T07:31:33Z") == 2
    assert "legacy / 未提供" in k1 and "2026-07-23" in k1
    assert "2026-09-23" not in k2 and "未提供" in k2
    assert "2026-09-22" not in ledger
    assert not re.findall(r"\[K\d+\]", ledger)
    records = []
    raw = template()
    assembled = assemble_report(raw, knowledge, phase="draft", record=records.append)
    assert assembled == raw.replace(SLOT, ledger)
    assert records[0].raw_report == raw and records[0].assembled_report == assembled
    assert records[0].to_dict()["semantic_approval"] is False
    assert records[0].to_dict()["raw_sha256"] != records[0].to_dict()["assembled_sha256"]


def test_source_values_cannot_create_citations_html_or_extra_rows(knowledge):
    citation = replace(knowledge.citations[0], source_id="review[K9].md",
        title="<script>x</script>\n| bad | `x` " + END)
    ledger = knowledge_ledger(replace(knowledge, citations=(citation,)))
    assert ledger.count(END) == 1 and "<script>" not in ledger
    assert "\n| bad" not in ledger and not re.findall(r"\[K\d+\]", ledger)


@pytest.mark.parametrize("change", [
    lambda text: text.replace(SLOT, ""),
    lambda text: text + "不能偷偷丢弃的正文。",
    lambda text: text.replace(SLOT, SLOT + "\n" + SLOT),
    lambda text: text.replace(COACH_REPORT_HEADINGS[-1], "text " + COACH_REPORT_HEADINGS[-1]),
    lambda text: text.replace(COACH_REPORT_HEADINGS[1], "TEMP").replace(
        COACH_REPORT_HEADINGS[2], COACH_REPORT_HEADINGS[1]).replace("TEMP", COACH_REPORT_HEADINGS[2]),
    lambda text: "```markdown\n" + text + "```",
])
def test_missing_misplaced_or_disguised_slot_keeps_raw_and_rejects(knowledge, change):
    raw, records = change(template()), []
    with pytest.raises(ValueError):
        assemble_report(raw, knowledge, phase="draft", record=records.append)
    assert records[0].raw_report == raw and records[0].assembled_report is None


def test_editor_must_preserve_exact_ledger_and_cannot_hide_body_deletion(knowledge):
    raw = template("原有分析及条件行动。[K1]" * 100)
    original = assemble_report(raw, knowledge, phase="draft", record=lambda _: None)
    for changed in (original.replace("2026-09-23", "2026-09-10"), original.replace(START, ""),
            template().replace(SLOT, knowledge_ledger(knowledge))):
        records = []
        with pytest.raises(ValueError):
            assemble_report(changed, knowledge, phase="revision", original=original, record=records.append)
        assert records[0].raw_report == changed and records[0].assembled_report is None
    assert assemble_report(original, knowledge, phase="revision", original=original,
        record=lambda _: None) == original


def test_historical_without_metadata_remains_unknown(knowledge):
    old = replace(knowledge, retrievals=())
    ledger = knowledge_ledger(old)
    assert "2026-07-23" in ledger and "2026-09-23" not in ledger
    assert "未提供" in ledger
    assert "未取得可列出的知识条目" in knowledge_ledger(KnowledgeEvidence.empty())


def test_unrelated_fact_errors_remain_in_the_complete_review_input(knowledge):
    # Assembly must not erase contradictions, wrong populations, identity,
    # attribution, invented training goals, or long-term extrapolation.
    errors = (
        "知识检索时间2026-09-10。", "全部五局都是中单。", "这些数据证明阅读者水平不足。",
        "辅助局造成了全部中单伤害差距。", "你的训练目标已经确定为辅助。", "未来所有比赛一定获胜。",
    )
    _, req = prepare_claim_scope(4)
    raw = template("\n".join(errors) + "[K1]")
    assembled = assemble_report(raw, knowledge, phase="draft", record=lambda _: None)
    inputs = build_inputs(replace(req, report=assembled, knowledge=knowledge))
    built = RoleReviewWorkflow.make_request(inputs)
    assert inputs.source.report == assembled
    assert all(error in built.messages[1].content for error in errors)


def test_appended_directory_cannot_satisfy_body_citation_floor(knowledge):
    _, req = prepare_claim_scope(4)
    report = assemble_report(template("正文没有引用。"), knowledge, phase="draft", record=lambda _: None)
    with pytest.raises(ValueError, match="native_missing_knowledge_citation_unreported"):
        RoleReviewWorkflow.validate_review(compact(valid_review()), build_inputs(replace(req,
            report=report, knowledge=knowledge)))


def test_harness_revision_and_publication_use_same_bytes(tmp_path):
    _, req = prepare_claim_scope(4)
    records = []
    raw = req.report + "\n\n" + SLOT + "\n"
    original = assemble_report(raw, req.knowledge, phase="draft", record=lambda _: None)
    revised = original.replace(COACH_REPORT_HEADINGS[-1],
        COACH_REPORT_HEADINGS[-1] + "\n\n离线编辑见证，非模型质量结果。[K1]")
    provider = exchange_provider([tool_response(valid_review(issue=True)), revised, tool_response(valid_review())])
    flow = SourceBoundRoleWorkflow(BudgetedReviewSender(provider, clock=lambda: 1000), record_assembly=records.append)
    class Preparer:
        def prepare(self, request):
            return DraftPreparationResult(CoachDraft(raw), req.knowledge)
    store = FileRunStore(tmp_path, "offline-source-assembly")
    harness = ReviewHarness(store=store,
        draft_preparer=SourceBoundDraftPreparer(Preparer(), record=records.append),
        evaluator=flow, reviser=flow, config=HarnessConfig(allow_deterministic_fallback=False))
    manifest = harness.run(player_summary=req.player_summary, deterministic_report=req.deterministic_report,
        user_utterance=req.user_utterance)
    assert manifest.status is RunStatus.PUBLISHED and flow.calls == 3 and flow.revisions == 1
    assert len(records) == 2 and records[1].raw_report == records[1].assembled_report == revised
    final = next(row for row in manifest.artifacts if row["kind"] == ArtifactKind.FINAL_REPORT.value)
    assert store.read_artifact(final).decode("utf-8") == revised
    assert flow._expected_recheck.source.report == revised
    assert flow.last_journal["report_sha256"] == records[1].to_dict()["assembled_sha256"]
    assert json.loads(provider.requests[-1].messages[1].content.split("[UNTRUSTED DATA]\n")[1].split(
        "\n[END UNTRUSTED DATA]")[0])["user_utterance"] == req.user_utterance


def test_bad_editor_output_stops_before_final_review_and_retains_raw():
    _, req = prepare_claim_scope(4)
    original = assemble_report(req.report + "\n" + SLOT, req.knowledge, phase="draft", record=lambda _: None)
    bad = original.replace(END, "tampered")
    records = []
    provider = exchange_provider([tool_response(valid_review(issue=True)), bad])
    flow = SourceBoundRoleWorkflow(BudgetedReviewSender(provider, clock=lambda: 1000), record_assembly=records.append)
    req = replace(req, report=original)
    result = flow.evaluate(req)
    with pytest.raises(ValueError, match="source_ledger_final_slot_required"):
        flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, original, result))
    assert flow.stopped and flow.calls == 2 and records[-1].raw_report == bad
    assert records[-1].assembled_report is None


def test_original_failure_and_all_frozen_inputs_remain_counterexamples_without_io(monkeypatch):
    import socket
    from scripts.check_source_bound_report import audit
    original_read = Path.read_text
    def read(path, *args, **kwargs):
        assert "data/runs/" not in path.as_posix() and path.name != ".env"
        return original_read(path, *args, **kwargs)
    def denied(*args, **kwargs):
        raise AssertionError("offline prototype attempted network access")
    monkeypatch.setattr(Path, "read_text", read)
    monkeypatch.setattr(socket.socket, "connect", denied)
    result = audit()
    assert result["negative_control"]["validator_verdict"] == "pass"
    assert not result["negative_control"]["host_accepted"]
    assert result["negative_control"]["retained"]
    assert len(result["frozen_15_preservation"]) == 15
    assert all(row["full_original_preserved"] and not row["model_observed"]
        for row in result["frozen_15_preservation"])
    saved = json.loads(Path("data/evaluation/results/golden_source_responsibility_audit_v1.json").read_text(encoding="utf-8"))
    assert result == saved


def test_actual_role_runtime_keeps_shared_five_call_budget_with_assembly(tmp_path, monkeypatch):
    # Real product compilation, knowledge tools, budget, Trace and file readback;
    # test-only injected assembly and scripted replies, NOT candidate admission.
    from tests import test_role_coach_application as product
    from tests.test_reviewer_role_proposal import providers
    from app.evaluation.source_bound_report import START
    from app.runtime.review_sender import SharedBudgetReviewSender
    from app.runtime.store import RuntimeTraceStore
    from app.product.run_receipts import FileRunReceiptStore

    records, flows = [], []
    def adapted_providers(**kwargs):
        generator, reviewer = providers(**kwargs)
        original_chat = generator.chat
        def chat(request):
            response = original_chat(request)
            if request.metadata.get("agent_loop_iteration") == 2:
                response = replace(response, content=response.content + "\n\n" + SLOT)
            elif request.metadata.get("review_phase") == "native_business_revision":
                ledger = START + flows[0]._revision_request.report.split(START, 1)[1]
                response = replace(response, content=response.content + "\n\n" + ledger)
            generator.last_exchange = replace(generator.last_exchange, response=response)
            return response
        generator.chat = chat
        return generator, reviewer
    monkeypatch.setattr(product, "providers", adapted_providers)
    app, factory, _ = product.application(tmp_path, charge_ceiling=True)
    execution_factory = app._runtime._execution_factory
    def workflow(runtime, provider):
        flow = SourceBoundRoleWorkflow(SharedBudgetReviewSender(provider), record_assembly=records.append)
        flows.append(flow)
        return flow
    monkeypatch.setattr(execution_factory, "_review_workflow_factory", workflow)
    original_build = execution_factory.build
    def build(**kwargs):
        bundle = original_build(**kwargs)
        return replace(bundle, draft_preparer=SourceBoundDraftPreparer(bundle.draft_preparer,
            record=records.append))
    monkeypatch.setattr(execution_factory, "build", build)
    result = product.run(app, "offline_source_bound_roles")
    assert result.publication_status.value == "published", result.terminal_reason
    delegate, flow = factory.providers["offline_source_bound_roles"], flows[0]
    assert [row["role"] for row in delegate.attempts] == ["generation", "generation", "review", "revision", "review"]
    assert flow.send.provider.calls == 5 and flow.send.provider.tokens <= 401920
    assert flow.calls == 3 and len(records) == 2
    assert records[-1].raw_report == records[-1].assembled_report
    assert flow._expected_recheck.source.report == records[-1].assembled_report
    trace = RuntimeTraceStore(tmp_path, "offline_source_bound_roles").read_trace(result.trace_reference)
    receipt = FileRunReceiptStore(tmp_path).read_receipt("offline_source_bound_roles")
    assert trace and receipt
