from collections import Counter, defaultdict
from statistics import mean


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def mmss(timestamp_ms: int) -> str:
    total_seconds = timestamp_ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def find_target_participant(match_detail: dict, puuid: str) -> dict:
    for participant in match_detail["info"]["participants"]:
        if participant["puuid"] == puuid:
            return participant

    raise ValueError("Target participant not found in match detail.")


def extract_perk_ids_from_target(target: dict) -> list[int]:
    result = []
    perks = target.get("perks", {})

    for style in perks.get("styles", []):
        if "style" in style:
            result.append(style["style"])

        for selection in style.get("selections", []):
            if "perk" in selection:
                result.append(selection["perk"])

    return result


def analyze_match_detail(match_detail: dict, puuid: str) -> dict:
    info = match_detail.get("info") or {}
    metadata = match_detail.get("metadata") or {}
    participants = info.get("participants") or []

    if not metadata.get("matchId"):
        raise ValueError("Match detail is missing metadata.matchId.")
    if not participants:
        raise ValueError("Match detail has no participants.")

    target = find_target_participant(match_detail, puuid)

    duration_seconds = info.get("gameDuration")
    if not isinstance(duration_seconds, (int, float)) or duration_seconds <= 0:
        raise ValueError("Match duration must be a positive number.")
    duration_minutes = duration_seconds / 60

    team_id = target["teamId"]
    team_members = [p for p in participants if p["teamId"] == team_id]

    team_kills = sum(p["kills"] for p in team_members)
    team_damage = sum(p["totalDamageDealtToChampions"] for p in team_members)
    team_gold = sum(p["goldEarned"] for p in team_members)

    kills = target["kills"]
    deaths = target["deaths"]
    assists = target["assists"]

    cs = target["totalMinionsKilled"] + target["neutralMinionsKilled"]

    return {
        "match_id": metadata["matchId"],
        "game_version": info.get("gameVersion"),
        "queue_id": info.get("queueId"),
        "game_duration_seconds": duration_seconds,
        "game_duration_minutes": round(duration_minutes, 2),

        "riot_id": f'{target.get("riotIdGameName")}#{target.get("riotIdTagline")}',
        "participant_id": target["participantId"],

        "champion_id": target["championId"],
        "champion_name_en": target["championName"],
        "champion_name": target["championName"],

        "role": target.get("teamPosition") or target.get("individualPosition") or "UNKNOWN",
        "team_id": team_id,
        "win": target["win"],

        "summoner_spell_ids": [
            target.get("summoner1Id"),
            target.get("summoner2Id"),
        ],

        "perk_ids": extract_perk_ids_from_target(target),

        "kills": kills,
        "deaths": deaths,
        "assists": assists,
        "kda": round(safe_div(kills + assists, max(1, deaths)), 2),

        "cs": cs,
        "cs_per_min": round(safe_div(cs, duration_minutes), 2),

        "gold": target["goldEarned"],
        "gold_per_min": round(safe_div(target["goldEarned"], duration_minutes), 2),

        "damage_to_champions": target["totalDamageDealtToChampions"],
        "damage_per_min": round(
            safe_div(target["totalDamageDealtToChampions"], duration_minutes),
            2,
        ),

        "vision_score": target["visionScore"],

        "team_kills": team_kills,
        "kill_participation": round(
            safe_div(kills + assists, team_kills),
            4,
        ),

        "damage_share": round(
            safe_div(target["totalDamageDealtToChampions"], team_damage),
            4,
        ),

        "gold_share": round(
            safe_div(target["goldEarned"], team_gold),
            4,
        ),

        "items": [target.get(f"item{i}") for i in range(7)],
    }


def analyze_match_timeline(timeline: dict, participant_id: int) -> dict:
    info = timeline.get("info") or {}
    frames = info.get("frames") or []
    if not frames:
        raise ValueError("Timeline contains no frames.")

    death_times = []
    item_purchases = []
    objective_events = []

    gold_by_minute = []
    cs_by_minute = []
    xp_by_minute = []
    level_by_minute = []

    for minute_index, frame in enumerate(frames):
        participant_frame = frame.get("participantFrames", {}).get(str(participant_id))

        if participant_frame:
            minions = participant_frame.get("minionsKilled", 0)
            jungle_minions = participant_frame.get("jungleMinionsKilled", 0)

            gold_by_minute.append(
                {
                    "minute": minute_index,
                    "total_gold": participant_frame.get("totalGold", 0),
                    "current_gold": participant_frame.get("currentGold", 0),
                }
            )

            cs_by_minute.append(
                {
                    "minute": minute_index,
                    "cs": minions + jungle_minions,
                }
            )

            xp_by_minute.append(
                {
                    "minute": minute_index,
                    "xp": participant_frame.get("xp", 0),
                }
            )

            level_by_minute.append(
                {
                    "minute": minute_index,
                    "level": participant_frame.get("level", 0),
                }
            )

        for event in frame.get("events", []):
            event_type = event.get("type")
            timestamp = event.get("timestamp", 0)

            if event_type == "CHAMPION_KILL":
                if event.get("victimId") == participant_id:
                    death_times.append(timestamp)

            elif event_type == "ITEM_PURCHASED":
                if event.get("participantId") == participant_id:
                    item_purchases.append(
                        {
                            "time_ms": timestamp,
                            "time": mmss(timestamp),
                            "item_id": event.get("itemId"),
                        }
                    )

            elif event_type == "ELITE_MONSTER_KILL":
                objective_events.append(
                    {
                        "time_ms": timestamp,
                        "time": mmss(timestamp),
                        "monster": event.get("monsterType"),
                        "killer_id": event.get("killerId"),
                    }
                )

    death_buckets = {
        "0_5": 0,
        "5_10": 0,
        "10_15": 0,
        "15_20": 0,
        "20_25": 0,
        "25_plus": 0,
    }

    for t in death_times:
        minute = t // 1000 // 60

        if minute < 5:
            death_buckets["0_5"] += 1
        elif minute < 10:
            death_buckets["5_10"] += 1
        elif minute < 15:
            death_buckets["10_15"] += 1
        elif minute < 20:
            death_buckets["15_20"] += 1
        elif minute < 25:
            death_buckets["20_25"] += 1
        else:
            death_buckets["25_plus"] += 1

    return {
        "death_times": [mmss(t) for t in death_times],
        "death_count": len(death_times),
        "deaths_before_10": sum(1 for t in death_times if t <= 10 * 60 * 1000),
        "deaths_before_15": sum(1 for t in death_times if t <= 15 * 60 * 1000),
        "death_buckets": death_buckets,

        "item_purchases": item_purchases,
        "first_item_purchase": item_purchases[0] if item_purchases else None,
        "last_item_purchase": item_purchases[-1] if item_purchases else None,

        "objective_events": objective_events,

        "gold_by_minute": gold_by_minute,
        "cs_by_minute": cs_by_minute,
        "xp_by_minute": xp_by_minute,
        "level_by_minute": level_by_minute,
    }


def aggregate_recent_matches(match_rows: list[dict]) -> dict:
    if not match_rows:
        return {}

    wins = [row for row in match_rows if row["win"]]
    losses = [row for row in match_rows if not row["win"]]

    role_counter = Counter(row.get("role") or "UNKNOWN" for row in match_rows)
    champion_counter = Counter(row["champion_name"] for row in match_rows)

    def avg(rows: list[dict], key: str) -> float:
        values = [row[key] for row in rows if row.get(key) is not None]
        return round(mean(values), 2) if values else 0.0

    def avg_percent(rows: list[dict], key: str) -> float:
        values = [row[key] * 100 for row in rows if row.get(key) is not None]
        return round(mean(values), 1) if values else 0.0

    champion_stats = defaultdict(lambda: {"games": 0, "wins": 0})
    role_stats = defaultdict(lambda: {"games": 0, "wins": 0})

    for row in match_rows:
        champion = row["champion_name"]
        role = row["role"]

        champion_stats[champion]["games"] += 1
        champion_stats[champion]["wins"] += int(row["win"])

        role_stats[role]["games"] += 1
        role_stats[role]["wins"] += int(row["win"])

    champion_summary = []
    for champion, stat in champion_stats.items():
        champion_summary.append(
            {
                "champion": champion,
                "games": stat["games"],
                "wins": stat["wins"],
                "win_rate": round(stat["wins"] / stat["games"] * 100, 1),
            }
        )

    role_summary = []
    for role, stat in role_stats.items():
        role_summary.append(
            {
                "role": role,
                "games": stat["games"],
                "wins": stat["wins"],
                "win_rate": round(stat["wins"] / stat["games"] * 100, 1),
            }
        )

    return {
        "games_analyzed": len(match_rows),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(match_rows) * 100, 1),

        "main_role": role_counter.most_common(1)[0][0],
        "main_champions": [name for name, _ in champion_counter.most_common(5)],

        "averages": {
            "kda": avg(match_rows, "kda"),
            "cs_per_min": avg(match_rows, "cs_per_min"),
            "gold_per_min": avg(match_rows, "gold_per_min"),
            "damage_per_min": avg(match_rows, "damage_per_min"),
            "vision_score": avg(match_rows, "vision_score"),
            "kill_participation_percent": avg_percent(match_rows, "kill_participation"),
            "damage_share_percent": avg_percent(match_rows, "damage_share"),
            "gold_share_percent": avg_percent(match_rows, "gold_share"),
            "deaths_before_15": avg(match_rows, "deaths_before_15"),
        },

        "win_loss_comparison": {
            "wins": {
                "cs_per_min": avg(wins, "cs_per_min"),
                "gold_per_min": avg(wins, "gold_per_min"),
                "damage_per_min": avg(wins, "damage_per_min"),
                "vision_score": avg(wins, "vision_score"),
                "deaths_before_15": avg(wins, "deaths_before_15"),
            },
            "losses": {
                "cs_per_min": avg(losses, "cs_per_min"),
                "gold_per_min": avg(losses, "gold_per_min"),
                "damage_per_min": avg(losses, "damage_per_min"),
                "vision_score": avg(losses, "vision_score"),
                "deaths_before_15": avg(losses, "deaths_before_15"),
            },
        },

        "champion_summary": sorted(
            champion_summary,
            key=lambda x: x["games"],
            reverse=True,
        ),

        "role_summary": sorted(
            role_summary,
            key=lambda x: x["games"],
            reverse=True,
        ),
    }
