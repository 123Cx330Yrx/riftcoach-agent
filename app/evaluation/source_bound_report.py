"""Offline responsibility prototype, not a registered Coach contract.

Only a declared slot may be rendered. Narrative text is never repaired here.
The editor must preserve the rendered ledger exactly; final review therefore
binds the editor's actual returned bytes without rebinding private workflow state.
"""
from dataclasses import dataclass, replace
import hashlib
import html
import re
from typing import Callable, Literal

from app.agent.draft import AgentDraftPreparationResult
from app.evaluation.coach_report import validate_revised_report
from app.evaluation.golden_role_review import RoleReviewWorkflow
from app.harness.knowledge import citation_retrieval_fields, knowledge_projection
from app.harness.steps import CoachDraft, DraftPreparationResult, KnowledgeEvidence
from app.evaluation.golden_review_experiment import compact
from app.report_validation import COACH_REPORT_HEADINGS


VERSION = "source-bound-report-offline-v1"
SLOT = "<!-- riftcoach:knowledge-sources -->"
START = "<!-- riftcoach:knowledge-sources:start -->"
END = "<!-- riftcoach:knowledge-sources:end -->"
GENERATION_INSTRUCTION = (
    "保留完整七节报告和第7节的数据边界分析。知识目录、文档版本/更新时间和实际检索时间"
    "由程序从本次来源记录呈现，不自由重写这些元数据；正文仍在实际使用知识处引用[K编号]。"
    "在第7节末尾另起一行输出 " + SLOT + "，此后不输出内容。"
    "正文的事实、身份/位置、归因、条件训练和外推边界仍适用全部原有要求。"
)
REVISION_INSTRUCTION = (
    "末尾 riftcoach:knowledge-sources:start/end 之间是本次来源记录的固定呈现，"
    "修订时连同标记逐字保留；只修正文中的真实问题，不能删除正文错误来替换为来源目录。"
    "若固定来源块本身与输入冲突，不编造或改写它。"
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cell(value: str | None) -> str:
    # Values are data, never Markdown, HTML or additional report citations.
    text = "未提供" if value is None else value
    text = html.escape(text, quote=True)
    for character in "\\`*_[]|":
        text = text.replace(character, f"&#{ord(character)};")
    return text.replace("\r", "&#13;").replace("\n", "&#10;")


def knowledge_ledger(knowledge: KnowledgeEvidence) -> str:
    """Render only attributed metadata; never turn unknown times into 'now'."""
    ids = [citation.citation_id for citation in knowledge.citations]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"K[1-9]\d*", key) for key in ids):
        raise ValueError("source_ledger_citation_identity_invalid")
    lines = [START, "检索资料目录（目录不代表正文已使用全部条目）：",
        "| 编号 | 来源 / 章节 | 文档版本 | 文档更新时间 | 检索来源 / 时间 |",
        "|---|---|---|---|---|"]
    for citation in knowledge.citations:
        retrievals = citation_retrieval_fields(knowledge, citation).get("retrievals", [])
        times = "；".join(_cell(row["provider"]) + " / " + _cell(row["retrieved_at"])
            for row in retrievals) or "未提供"
        lines.append(f"| {citation.citation_id} | {_cell(citation.source_id)} / {_cell(citation.title)} | "
            f"{_cell(citation.version)} | {_cell(citation.updated_at)} | {times} |")
    if not knowledge.citations:
        lines.append("未取得可列出的知识条目。")
    lines += ["时间按来源记录原样呈现；缓存沿用原检索时间，未知时间不由文档更新时间或外部快照推定。", END]
    return "\n".join(lines)


@dataclass(frozen=True)
class AssemblyRecord:
    phase: str
    raw_report: str
    assembled_report: str | None
    knowledge_sha256: str
    operation: str
    error: str | None = None

    def to_dict(self):
        return dict(version=VERSION, phase=self.phase, operation=self.operation, error=self.error,
            raw_report=self.raw_report, raw_sha256=_sha(self.raw_report),
            assembled_report=self.assembled_report,
            assembled_sha256=_sha(self.assembled_report) if self.assembled_report is not None else None,
            knowledge_sha256=self.knowledge_sha256, semantic_approval=False)


def _prefix(report: str, suffix: str) -> str:
    # Never strip user/model prose, normalize line endings or locate a vaguely
    # matching source paragraph. This slot must be the exact final logical line.
    tail = report[:-1] if report.endswith("\n") else report
    if not tail.endswith("\n" + suffix):
        raise ValueError("source_ledger_final_slot_required")
    prefix = tail[:-len(suffix)]
    if "riftcoach:knowledge-sources" in prefix:
        raise ValueError("source_ledger_duplicate_or_misplaced")
    headings = [line for line in prefix.splitlines() if line.startswith(("# ", "## "))]
    def heading_identity(line):
        return next((heading for heading in COACH_REPORT_HEADINGS if line == heading
            or any(line.startswith(heading + separator) for separator in ("：", ":", " "))), None)
    # Descriptive heading suffixes and existing intermediate subheadings are
    # valid report content (including assertions the reviewer must check).
    identities = tuple(filter(None, (heading_identity(line) for line in headings)))
    if identities != COACH_REPORT_HEADINGS or heading_identity(headings[-1]) != COACH_REPORT_HEADINGS[-1]:
        raise ValueError("source_ledger_section_required")
    # A slot inside a fenced block is not a report section attachment.
    if any(line.lstrip().startswith(("```", "~~~")) for line in prefix.splitlines()):
        raise ValueError("source_ledger_fenced_report_unsupported")
    return prefix


def assemble_report(raw: str, knowledge: KnowledgeEvidence, *, phase: Literal["draft", "revision"],
        record: Callable[[AssemblyRecord], None], original: str | None = None) -> str:
    """Record failures as well as accepted assembly; no claim of semantic repair."""
    knowledge_sha = _sha(compact(knowledge_projection(knowledge)))
    operation = "verify_unchanged_ledger"
    try:
        ledger = knowledge_ledger(knowledge)
        if phase == "draft":
            prefix = _prefix(raw, SLOT)
            assembled = prefix + ledger + ("\n" if raw.endswith("\n") else "")
            operation = "render_declared_slot"
            validate_revised_report(prefix, prefix)
        elif phase == "revision" and original is not None:
            prefix = _prefix(raw, ledger)
            before = _prefix(original, ledger)
            # Fixed host text must not inflate the historical 70% preservation
            # check. This is still a length guard, not a semantic edit proof.
            validate_revised_report(prefix, before)
            assembled = raw
        else:
            raise ValueError("source_ledger_phase_invalid")
    except ValueError as error:
        record(AssemblyRecord(phase, raw, None, knowledge_sha, "rejected", str(error)))
        raise
    record(AssemblyRecord(phase, raw, assembled, knowledge_sha, operation))
    return assembled


class SourceBoundDraftPreparer:
    """Reuse the actual preparer; no tool, runtime or source system is added."""
    def __init__(self, delegate, *, record):
        self.delegate, self.record = delegate, record

    def prepare(self, *args, **kwargs):
        result = self.delegate.prepare(*args, **kwargs)
        if not isinstance(result, (DraftPreparationResult, AgentDraftPreparationResult)):
            raise TypeError("draft preparation contract required")
        report = assemble_report(result.draft.report, result.knowledge, phase="draft", record=self.record)
        return replace(result, draft=CoachDraft(report))


class SourceBoundRoleWorkflow(RoleReviewWorkflow):
    """Offline-only integration seam; review policies and source binding stay intact."""
    def __init__(self, send, *, record_assembly, record=None):
        super().__init__(send, record=record)
        self.record_assembly = record_assembly
        self._revision_request = None

    def make_request(self, inputs, **kwargs):
        request = super().make_request(inputs, **kwargs)
        if kwargs.get("accepted") is not None:
            request = replace(request, messages=(replace(request.messages[0],
                content=request.messages[0].content + "\n" + REVISION_INSTRUCTION), *request.messages[1:]))
            from app.evaluation.golden_native_issues_review import budget_check
            request = budget_check(request)
        return request

    def revise(self, request):
        self._revision_request = request
        try:
            return super().revise(request)
        finally:
            self._revision_request = None

    def _call(self, prepared, phase):
        raw = super()._call(prepared, phase)
        if phase == "native_business_revision":
            request = self._revision_request
            # Validation happens before the base workflow binds expected_recheck.
            # Accepted revision bytes are returned unchanged, never rebound.
            return assemble_report(raw, request.knowledge, phase="revision", original=request.report,
                record=self.record_assembly)
        return raw
