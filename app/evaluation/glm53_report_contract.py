"""Explicit development-only report contract; historical prompts stay unchanged."""

import hashlib

from app.agent.context import CANDIDATE_CONTEXT_SAFETY_POLICY_V1
from app.evaluation.coach_report import build_revision_prompt
from app.rag.coaching_query import COACHING_QUERY_GUIDANCE_V1
from app.report_validation import COACH_REPORT_HEADINGS

REPORT_CONTRACT_ID = "coach-markdown-generation-revision-v1"
DEVELOPMENT_PLAN_ID = "glm53-report-contract-development"
DEVELOPMENT_SNAPSHOT_ID = "glm53-report-contract-development-context-v1"
REPORT_POLICY = (
    "可信报告结构合同：" + REPORT_CONTRACT_ID + "\n"
    "初稿和修订版都必须输出完整 Markdown，保留以下标题及顺序，不使用外层代码块：\n"
    + "\n".join(COACH_REPORT_HEADINGS)
    + "\n各节只写数据和检索证据支持的内容；无对应数据就明确说明未知或样本不足，"
    "不要为填满章节捏造事实。保留有效的 [K编号] 引用，不新增未知引用。"
    "修订只改评测指出的问题及直接受影响的上下文，保留其他内容；"
    "修订版不得短于原报告字符数的 70%，不得以重复填充规避该要求。"
)
REPORT_CONTRACT_SHA256 = hashlib.sha256(REPORT_POLICY.encode("utf-8")).hexdigest()


def require_report_contract(contract_id: str | None) -> None:
    if contract_id is not None and contract_id != REPORT_CONTRACT_ID:
        raise ValueError("unsupported report contract")


def candidate_context_policy(contract_id: str | None = None) -> str:
    require_report_contract(contract_id)
    sections = [CANDIDATE_CONTEXT_SAFETY_POLICY_V1, COACHING_QUERY_GUIDANCE_V1]
    if contract_id is not None:
        sections.append(REPORT_POLICY)
    return "\n\n".join(sections)


def build_aligned_revision_prompt(report: str, evaluation: dict) -> str:
    return build_revision_prompt(report, evaluation) + "\n\n" + REPORT_POLICY
