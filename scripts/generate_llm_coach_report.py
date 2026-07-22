import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.rag.retriever import LocalKnowledgeRetriever, format_evidence
from app.artifacts import coach_report_path, deterministic_report_path
from app.lol.data_dragon import DataDragonService
from app.lol.summary_schema import validate_summary_document
from app.lol.terminology import TerminologyStore


SYSTEM_PROMPT = """
你是 RiftCoach，一个英雄联盟赛后复盘助手。

你需要用中文把确定性比赛统计和检索到的复盘知识整理成教练式报告。

硬性规则：
1. 比赛事实只能来自输入 JSON 和确定性报告；知识库只能用于解释指标和提出复盘方法。
2. 不允许编造比赛事件、英雄机制、对线细节、技能释放、兵线状态、玩家心理或操作意图。
3. 证据不足时必须明确说明“当前数据不足以判断”。
4. 不要放大很小的数值差异，不要把相关性表述成因果。
5. 两个指标同时下降时，只能说它们同时下降或可能相关。
6. 没有早期死亡只能说明前期生存结果较好，不能直接推断防抓或对线能力。
7. 未提供控制守卫数据时，不讨论具体买眼习惯。
8. 英雄和装备可以使用国服玩家熟悉的简称或外号；不确定时使用官方中文名。
9. 指标尽量使用中文：补刀/分钟、经济/分钟、伤害/分钟、视野分、参团率、输出占比、经济占比。KDA 可以保留。
10. 训练建议必须标明是基于统计现象提出的复盘假设，不是已经证明的原因。
11. 不提供实时辅助、隐藏信息追踪、脚本或自动化等不公平竞技建议。
12. 不得声称知识库包含当前版本 Meta；版本强度、胜率和主流出装需要独立 Meta 数据支持。
13. 报告末尾必须说明数据边界，并列出本次实际采用的知识来源。

输出 Markdown，固定结构：
# RiftCoach 教练式复盘报告
## 1. 总体结论
## 2. 当前表现亮点
## 3. 主要风险点
## 4. 赢局与输局差异
## 5. 下一步复盘建议
## 6. 训练计划
## 7. 数据边界与知识来源
""".strip()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def compact_summary(data: dict) -> dict:
    recent = data.get("recent_summary", {})
    compact_matches = []

    for row in data.get("matches", []):
        purchases = [
            {
                "time": item.get("time"),
                "item_name": item.get("item_name"),
            }
            for item in row.get("item_purchases", [])[:12]
        ]
        compact_matches.append(
            {
                "match_id": row.get("match_id"),
                "champion_name": row.get("champion_name"),
                "champion_name_en": row.get("champion_name_en"),
                "role": row.get("role"),
                "win": row.get("win"),
                "included_in_aggregate": row.get("included_in_aggregate"),
                "timeline_status": row.get("timeline_status"),
                "kda": f"{row.get('kills')}/{row.get('deaths')}/{row.get('assists')}",
                "cs_per_min": row.get("cs_per_min"),
                "gold_per_min": row.get("gold_per_min"),
                "damage_per_min": row.get("damage_per_min"),
                "vision_score": row.get("vision_score"),
                "kill_participation": row.get("kill_participation"),
                "damage_share": row.get("damage_share"),
                "gold_share": row.get("gold_share"),
                "deaths_before_15": row.get("deaths_before_15"),
                "death_times": row.get("death_times", []),
                "final_item_names": row.get("item_names", []),
                "summoner_spell_names": row.get("summoner_spell_names", []),
                "rune_names": row.get("rune_names", []),
                "item_purchases": purchases,
            }
        )

    return {
        "player": data.get("player", {}),
        "request": data.get("request", {}),
        "recent_summary": {
            key: recent.get(key)
            for key in (
                "games_analyzed",
                "wins",
                "losses",
                "win_rate",
                "main_role",
                "main_champions",
                "averages",
                "win_loss_comparison",
                "champion_summary",
                "role_summary",
            )
        },
        "matches": compact_matches,
        "excluded_matches": data.get("excluded_matches", []),
        "failed_matches": data.get("failed_matches", []),
    }


def build_retrieval_query(summary: dict) -> str:
    recent = summary.get("recent_summary", {})
    averages = recent.get("averages") or {}
    comparison = recent.get("win_loss_comparison") or {}
    roles = " ".join(
        row.get("role", "") for row in recent.get("role_summary") or []
    )
    return (
        f"英雄联盟赛后复盘 {roles} 多位置样本 样本量 "
        f"补刀每分钟 经济每分钟 伤害每分钟 视野分 参团率 "
        f"15分钟前死亡 赢局输局比较 训练计划 数据边界 "
        f"平均数据 {json.dumps(averages, ensure_ascii=False)} "
        f"胜负比较 {json.dumps(comparison, ensure_ascii=False)}"
    )


def build_user_prompt(
    summary: dict,
    deterministic_report: str,
    knowledge_evidence: str,
) -> str:
    return f"""
请根据以下三类输入生成中文教练式复盘报告。

使用边界：
- JSON 和确定性报告是本次玩家对局事实。
- RAG 证据是通用复盘方法，不是该玩家已经发生的事实。
- 不使用输入之外的版本 Meta、英雄胜率、装备胜率或 OP.GG 数据。
- 英雄与装备可以自行采用国服常用叫法，不需要逐字照抄官方名。
- 不要使用 CS/min、GPM、DPM、Vision Score 等英文指标名。

【结构化比赛数据】
{json.dumps(summary, ensure_ascii=False, indent=2)}

【确定性报告】
{deterministic_report}

【RAG 检索证据】
{knowledge_evidence}
""".strip()


def create_llm_client() -> tuple[OpenAI, str]:
    load_dotenv()
    provider = os.getenv("LLM_PROVIDER", "zhipu")
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("LLM_MODEL")

    missing = [
        name
        for name, value in (
            ("LLM_API_KEY", api_key),
            ("LLM_BASE_URL", base_url),
            ("LLM_MODEL", model),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing LLM configuration: {', '.join(missing)}")

    print("LLM Provider:", provider)
    print("LLM Base URL:", base_url)
    print("LLM Model:", model)
    return OpenAI(api_key=api_key, base_url=base_url), model


def main():
    parser = argparse.ArgumentParser(description="Generate a RAG-enhanced GLM coach report.")
    parser.add_argument("--summary", required=True)
    parser.add_argument(
        "--deterministic-report",
        help="Optional deterministic report path derived from the summary when omitted.",
    )
    parser.add_argument(
        "--knowledge-dir",
        default="data/rag_docs",
        help="Directory containing Markdown knowledge documents.",
    )
    parser.add_argument("--rag-top-k", type=int, default=5)
    parser.add_argument(
        "--terminology",
        default="data/terminology/cn_lol_terms.json",
    )
    parser.add_argument(
        "--output",
        help="Optional output path derived from the summary when omitted.",
    )
    args = parser.parse_args()

    summary_path = Path(args.summary)
    if not summary_path.exists():
        raise FileNotFoundError(f"Summary JSON not found: {summary_path}")

    raw_summary = read_json(summary_path)
    validate_summary_document(raw_summary)
    report_path = (
        Path(args.deterministic_report)
        if args.deterministic_report
        else deterministic_report_path(raw_summary)
    )
    if not report_path.exists():
        raise FileNotFoundError(f"Deterministic report not found: {report_path}")
    terminology = TerminologyStore(Path(args.terminology))
    ddragon = DataDragonService(language="zh_CN")
    display_summary = terminology.apply_to_summary(raw_summary, ddragon)
    summary = compact_summary(display_summary)
    deterministic_report = read_text(report_path)
    retriever = LocalKnowledgeRetriever(Path(args.knowledge_dir))
    evidence = retriever.search(build_retrieval_query(summary), top_k=args.rag_top_k)
    knowledge_evidence = format_evidence(evidence)

    print(f"RAG documents: {retriever.document_count}")
    print(f"RAG chunks: {retriever.chunk_count}")
    print("RAG sources:", ", ".join(item.source for item in evidence) or "none")

    client, model = create_llm_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_user_prompt(
                    summary,
                    deterministic_report,
                    knowledge_evidence,
                ),
            },
        ],
        temperature=0.3,
    )

    report = response.choices[0].message.content or ""
    output_path = Path(args.output) if args.output else coach_report_path(raw_summary)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print("GLM coach report generated:", output_path)


if __name__ == "__main__":
    main()
