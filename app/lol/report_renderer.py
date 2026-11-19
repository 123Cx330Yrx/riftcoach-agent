"""Pure deterministic Markdown rendering for a validated player Summary."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def percent(value):
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def fmt(value):
    if value is None:
        return "N/A"
    return str(value)


def build_findings(recent_summary: dict) -> list[str]:
    """Describe supplied sample aggregates without inventing skill or cause.

    This text is also consumed as evidence by Coach. Arithmetic over displayed
    aggregates is an observation, not a measure of stability or player ability.
    """
    games = recent_summary.get("games_analyzed", 0)
    findings = [f"以下仅描述本次纳入的 {games} 局，不能据此推断长期水平或胜负原因。"]
    rate = recent_summary.get("win_rate")
    if rate is not None:
        findings.append(f"本样本胜率为 {rate}%；胜率记录本次结果，不单独评价打法或能力。")

    roles = recent_summary.get("role_summary", [])
    if len(roles) >= 2:
        role_text = "、".join(f"{r['role']} {r['games']} 局" for r in roles)
        findings.append(f"样本包含多个位置：{role_text}。混合位置均值受位置构成影响，应按位置核对原始对局；不能将混合差异解释为某一位置的表现差距。")
        scope = "本次全部纳入比赛（混合位置）"
    elif roles:
        scope = f"本次 {roles[0]['role']} 样本"
    else:
        scope = "本次全部纳入比赛（位置资料缺失）"
        findings.append("位置资料缺失，不能将整体均值视为同位置对比。")

    champions = recent_summary.get("champion_summary", [])
    if champions and sum(r.get("games") == 1 for r in champions) >= len(champions) * 0.7:
        findings.append("本样本多数英雄仅出现 1 局，单英雄胜率不足以判断英雄强弱或英雄池能力。")

    deaths = recent_summary.get("averages", {}).get("deaths_before_15")
    if deaths is not None:
        findings.append(f"{scope}前 15 分钟平均死亡 {deaths} 次；具体原因需逐局核对。")

    if recent_summary.get("wins", 0) >= 2 and recent_summary.get("losses", 0) >= 2:
        comparison = recent_summary.get("win_loss_comparison", {})
        wins, losses = comparison.get("wins", {}), comparison.get("losses", {})
        for key, label in (("cs_per_min", "补刀/分钟"), ("gold_per_min", "经济/分钟"),
                           ("damage_per_min", "伤害/分钟"), ("vision_score", "视野分"),
                           ("deaths_before_15", "前 15 分钟死亡次数")):
            w, l = wins.get(key), losses.get(key)
            if w is None or l is None:
                continue
            difference = (Decimal(str(l)) - Decimal(str(w))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            relation = (f"输局均值比赢局{'高' if difference > 0 else '低'} {abs(difference):f}"
                        if difference else "两组均值相同")
            findings.append(f"{scope}{label}的赢局均值为 {w}、输局均值为 {l}，{relation}（按展示均值计算）。")
        findings.append("均值差异不代表逐局方向一致、表现稳定性、能力变化或因果关系；这些判断需要另行核对证据。")
    return findings


def render_deterministic_report(data: dict) -> str:
    player = data["player"]
    request = data["request"]
    recent = data["recent_summary"]
    matches = data["matches"]

    averages = recent.get("averages", {})
    comparison = recent.get("win_loss_comparison", {})
    champion_summary = recent.get("champion_summary", [])
    role_summary = recent.get("role_summary", [])

    findings = build_findings(recent)
    lines = []

    lines.append(f"# RiftCoach 近期对局复盘报告：{player['riot_id']}")
    lines.append("")
    lines.append("## 1. 样本概况")
    lines.append("")
    lines.append(f"- 分析场次：{recent.get('games_analyzed')} 局")
    excluded_count = len(data.get("excluded_matches", []))
    failed_count = len(data.get("failed_matches", []))
    if excluded_count:
        lines.append(f"- 未计入汇总的短局：{excluded_count} 局")
    if failed_count:
        lines.append(f"- 数据解析失败：{failed_count} 局")
    lines.append(f"- 队列：{request.get('queue')}")
    lines.append(f"- Data Dragon 版本：{request.get('data_dragon_version')}")
    lines.append(f"- 胜场 / 负场：{recent.get('wins')} / {recent.get('losses')}")
    lines.append(f"- 胜率：{percent(recent.get('win_rate'))}")
    lines.append(f"- 本样本出现最多的位置：{recent.get('main_role')}")
    lines.append(f"- 本样本出现较多的英雄：{', '.join(recent.get('main_champions', []))}")
    lines.append("")

    lines.append("## 2. 平均表现")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|---|---:|")
    lines.append(f"| KDA | {fmt(averages.get('kda'))} |")
    lines.append(f"| 补刀/分钟 | {fmt(averages.get('cs_per_min'))} |")
    lines.append(f"| 经济/分钟 | {fmt(averages.get('gold_per_min'))} |")
    lines.append(f"| 伤害/分钟 | {fmt(averages.get('damage_per_min'))} |")
    lines.append(f"| 视野分 | {fmt(averages.get('vision_score'))} |")
    lines.append(f"| 参团率 | {percent(averages.get('kill_participation_percent'))} |")
    lines.append(f"| 输出占比 | {percent(averages.get('damage_share_percent'))} |")
    lines.append(f"| 经济占比 | {percent(averages.get('gold_share_percent'))} |")
    lines.append(f"| 15分钟前死亡 | {fmt(averages.get('deaths_before_15'))} |")
    lines.append("")

    lines.append("## 3. 赢局 / 输局对比")
    lines.append("")
    lines.append("| 指标 | 赢局 | 输局 |")
    lines.append("|---|---:|---:|")
    win_stats = comparison.get("wins", {})
    loss_stats = comparison.get("losses", {})
    for key, name in [
        ("cs_per_min", "补刀/分钟"),
        ("gold_per_min", "经济/分钟"),
        ("damage_per_min", "伤害/分钟"),
        ("vision_score", "视野分"),
        ("deaths_before_15", "15分钟前死亡"),
    ]:
        lines.append(
            f"| {name} | {fmt(win_stats.get(key))} | {fmt(loss_stats.get(key))} |"
        )
    lines.append("")

    lines.append("## 4. 英雄池概况")
    lines.append("")
    lines.append("| 英雄 | 场次 | 胜场 | 胜率 |")
    lines.append("|---|---:|---:|---:|")
    for row in champion_summary:
        lines.append(
            f"| {row['champion']} | {row['games']} | {row['wins']} | {percent(row['win_rate'])} |"
        )
    lines.append("")

    lines.append("## 5. 分路概况")
    lines.append("")
    lines.append("| 位置 | 场次 | 胜场 | 胜率 |")
    lines.append("|---|---:|---:|---:|")
    for row in role_summary:
        lines.append(
            f"| {row['role']} | {row['games']} | {row['wins']} | {percent(row['win_rate'])} |"
        )
    lines.append("")

    lines.append("## 6. 样本统计观察")
    lines.append("")
    for item in findings:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 7. 单局摘要")
    lines.append("")
    lines.append(
        "| 对局 ID | 英雄 | 英文名 | 位置 | 胜负 | KDA | 补刀/分钟 | 经济/分钟 | 伤害/分钟 | 视野分 | 15分钟前死亡 | 死亡时间 | 当前装备 | 召唤师技能 |"
    )
    lines.append(
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|"
    )
    for row in matches:
        result = "胜" if row["win"] else "负"
        kda_text = f"{row['kills']}/{row['deaths']}/{row['assists']}"
        death_times = ", ".join(row.get("death_times", [])) or "-"
        item_names = "、".join(row.get("item_names", [])) or "-"
        spell_names = "、".join(row.get("summoner_spell_names", [])) or "-"
        lines.append(
            f"| {row['match_id']} | {row['champion_name']} | {row.get('champion_name_en', '')} | "
            f"{row['role']} | {result} | {kda_text} | {row['cs_per_min']} | "
            f"{row['gold_per_min']} | {row['damage_per_min']} | {row['vision_score']} | "
            f"{fmt(row.get('deaths_before_15'))} | {death_times} | {item_names} | {spell_names} |"
        )
    lines.append("")

    lines.append("## 8. 当前版本说明")
    lines.append("")
    lines.append(
        "这份报告只基于 Riot API 返回的赛后统计、timeline 事件和 Data Dragon 静态数据进行分析。"
        "Riot API 支持 KDA、补刀、经济、伤害、视野、死亡时间和装备购买事件等中等粒度复盘；"
        "Data Dragon 负责英雄、装备、召唤师技能和符文的静态中文映射。"
        "当前报告不能替代录像级复盘，暂不能判断具体换血、走位、技能命中和兵线细节。"
    )
    lines.append("")
    return "\n".join(lines)


# Compatibility name used by the existing CLI and historical callers.
build_report = render_deterministic_report


__all__ = [
    "build_findings",
    "build_report",
    "fmt",
    "percent",
    "render_deterministic_report",
]
