"""Pure deterministic Markdown rendering for a validated player Summary."""

from __future__ import annotations


def percent(value):
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def fmt(value):
    if value is None:
        return "N/A"
    return str(value)


def build_findings(recent_summary: dict) -> list[str]:
    findings = []

    games = recent_summary.get("games_analyzed", 0)
    wins_count = recent_summary.get("wins", 0)
    losses_count = recent_summary.get("losses", 0)
    win_rate = recent_summary.get("win_rate", 0)

    averages = recent_summary.get("averages", {})
    comparison = recent_summary.get("win_loss_comparison", {})
    wins = comparison.get("wins", {})
    losses = comparison.get("losses", {})

    role_summary = recent_summary.get("role_summary", [])
    champion_summary = recent_summary.get("champion_summary", [])

    def diff(key: str):
        win_value = wins.get(key)
        loss_value = losses.get(key)
        if win_value is None or loss_value is None:
            return None
        return round(loss_value - win_value, 2)

    def has_both_win_loss_sample():
        return wins_count >= 2 and losses_count >= 2

    if games < 10:
        findings.append(
            f"当前只分析了 {games} 局，样本偏小，适合做初步观察，不适合下稳定结论。"
        )
    else:
        findings.append(
            f"当前样本为 {games} 局，可以用于初步复盘，但英雄池和单个英雄胜率仍需要更多样本验证。"
        )

    if win_rate >= 65:
        findings.append(
            f"最近样本胜率为 {win_rate}%，整体表现较好，复盘重点不应只找问题，也应总结当前有效打法。"
        )
    elif win_rate < 45:
        findings.append(
            f"最近样本胜率为 {win_rate}%，整体结果偏低，需要重点排查输局中反复出现的指标差异。"
        )
    else:
        findings.append(
            f"最近样本胜率为 {win_rate}%，整体表现处于中间区间，建议重点比较赢局和输局的发育、视野与死亡节奏差异。"
        )

    if len(role_summary) >= 2:
        role_text = "、".join(
            f"{row['role']} {row['games']} 局" for row in role_summary
        )
        findings.append(
            f"样本包含多个位置：{role_text}。由于不同位置的 CS、视野、伤害职责不同，后续更适合增加按位置过滤的复盘。"
        )

    one_game_champions = [
        row["champion"] for row in champion_summary if row.get("games") == 1
    ]
    if champion_summary and len(one_game_champions) >= len(champion_summary) * 0.7:
        findings.append(
            "当前大多数英雄都只出现 1 局，单个英雄胜率没有统计稳定性，暂时不建议根据单英雄胜率判断英雄池强弱。"
        )

    avg_deaths_15 = averages.get("deaths_before_15")
    death_diff = diff("deaths_before_15")

    if avg_deaths_15 is not None and avg_deaths_15 >= 1:
        findings.append(
            f"前 15 分钟平均死亡 {avg_deaths_15} 次，说明样本中前中期确实存在较多死亡事件，值得在单局复盘中继续追踪。"
        )

    if has_both_win_loss_sample() and death_diff is not None:
        if death_diff >= 0.5:
            findings.append(
                f"输局前 15 分钟死亡比赢局高 {death_diff} 次，早期死亡可能是输局的重要区分因素。"
            )
        elif abs(death_diff) < 0.2:
            findings.append(
                f"输局与赢局的前 15 分钟死亡差异只有 {abs(death_diff)} 次，当前不能把早期死亡直接判定为胜负的主要分界点。"
            )

    cs_diff = diff("cs_per_min")
    if has_both_win_loss_sample() and cs_diff is not None:
        if cs_diff <= -0.5:
            findings.append(
                f"输局补刀/分钟比赢局低 {abs(cs_diff)}，发育稳定性在输局中有所下降。"
            )
        elif abs(cs_diff) < 0.3:
            findings.append(
                "赢局和输局补刀/分钟差异较小，补刀本身可能不是当前样本最主要的胜负分界点。"
            )

    gpm_diff = diff("gold_per_min")
    if has_both_win_loss_sample() and gpm_diff is not None:
        if gpm_diff <= -40:
            findings.append(
                f"输局经济/分钟比赢局低 {abs(gpm_diff)}，经济获取效率是当前输赢差异中比较明显的一项。"
            )
        elif abs(gpm_diff) < 25:
            findings.append(
                "赢局和输局的经济/分钟差异不大，经济获取效率暂时不是最突出的分界点。"
            )

    dpm_diff = diff("damage_per_min")
    if has_both_win_loss_sample() and dpm_diff is not None and dpm_diff <= -100:
        findings.append(
            f"输局伤害/分钟比赢局低 {abs(dpm_diff)}，说明输局中输出转化能力或参团环境明显变差。"
        )

    vision_diff = diff("vision_score")
    if has_both_win_loss_sample() and vision_diff is not None and vision_diff <= -8:
        findings.append(
            f"输局视野分比赢局低 {abs(vision_diff)}，目标前布控、边线保护和信息获取可能是需要重点分析的方向。"
        )

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
    lines.append(f"- 主要位置：{recent.get('main_role')}")
    lines.append(f"- 常用英雄：{', '.join(recent.get('main_champions', []))}")
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

    lines.append("## 6. 初步问题判断")
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
