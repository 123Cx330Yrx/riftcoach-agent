import argparse
import os
import sys
import time
from urllib.parse import quote

import requests
from dotenv import load_dotenv


def load_config():
    load_dotenv()

    api_key = os.getenv("RIOT_API_KEY")
    region = os.getenv("RIOT_REGION", "asia")

    if not api_key:
        raise RuntimeError(
            "RIOT_API_KEY is missing. Please put it in your .env file."
        )

    return api_key, region


def riot_get(url: str, api_key: str, timeout: int = 15):
    headers = {"X-Riot-Token": api_key}

    response = requests.get(url, headers=headers, timeout=timeout)

    # 简单处理一次限流
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", "3"))
        print(f"[WARN] Rate limited. Sleeping {retry_after} seconds...")
        time.sleep(retry_after)
        response = requests.get(url, headers=headers, timeout=timeout)

    if response.status_code >= 400:
        print("\n[ERROR] Riot API request failed.")
        print("URL:", url)
        print("Status:", response.status_code)
        print("Response:", response.text[:500])
        response.raise_for_status()

    return response.json()


def get_account_by_riot_id(api_key: str, region: str, game_name: str, tag_line: str):
    encoded_game_name = quote(game_name, safe="")
    encoded_tag_line = quote(tag_line, safe="")

    url = (
        f"https://{region}.api.riotgames.com"
        f"/riot/account/v1/accounts/by-riot-id/"
        f"{encoded_game_name}/{encoded_tag_line}"
    )

    return riot_get(url, api_key)


def get_recent_match_ids(
    api_key: str,
    region: str,
    puuid: str,
    count: int = 5,
    queue: int | None = 420,
):
    query = f"start=0&count={count}"

    if queue is not None:
        query += f"&queue={queue}"

    url = (
        f"https://{region}.api.riotgames.com"
        f"/lol/match/v5/matches/by-puuid/{puuid}/ids?"
        f"{query}"
    )

    return riot_get(url, api_key)


def get_match_detail(api_key: str, region: str, match_id: str):
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    return riot_get(url, api_key)


def get_match_timeline(api_key: str, region: str, match_id: str):
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
    return riot_get(url, api_key)


def find_target_participant(match_detail: dict, puuid: str):
    participants = match_detail["info"]["participants"]

    for participant in participants:
        if participant["puuid"] == puuid:
            return participant

    raise ValueError("Target participant not found in this match.")


def print_match_summary(match_detail: dict, target: dict):
    participants = match_detail["info"]["participants"]
    duration_seconds = match_detail["info"]["gameDuration"]
    duration_minutes = duration_seconds / 60

    team_id = target["teamId"]
    team_members = [p for p in participants if p["teamId"] == team_id]

    team_kills = sum(p["kills"] for p in team_members)
    team_damage = sum(p["totalDamageDealtToChampions"] for p in team_members)
    team_gold = sum(p["goldEarned"] for p in team_members)

    cs = target["totalMinionsKilled"] + target["neutralMinionsKilled"]

    k = target["kills"]
    d = target["deaths"]
    a = target["assists"]

    kda = (k + a) / max(1, d)
    cs_per_min = cs / duration_minutes
    gold_per_min = target["goldEarned"] / duration_minutes
    damage_per_min = target["totalDamageDealtToChampions"] / duration_minutes

    kill_participation = (k + a) / team_kills if team_kills > 0 else 0
    damage_share = (
        target["totalDamageDealtToChampions"] / team_damage
        if team_damage > 0
        else 0
    )
    gold_share = target["goldEarned"] / team_gold if team_gold > 0 else 0

    print("\n=== Match Detail Summary ===")
    print("Game Version:", match_detail["info"].get("gameVersion"))
    print("Game Duration:", round(duration_minutes, 1), "minutes")
    print("Queue ID:", match_detail["info"].get("queueId"))

    print("\n=== Target Player ===")
    print("Summoner Name:", target.get("summonerName"))
    print("Riot ID:", f'{target.get("riotIdGameName")}#{target.get("riotIdTagline")}')
    print("Champion:", target["championName"])
    print("Role:", target.get("teamPosition") or target.get("individualPosition"))
    print("Win:", target["win"])

    print("\n=== Basic Stats ===")
    print("K / D / A:", k, d, a)
    print("KDA:", round(kda, 2))
    print("CS:", cs)
    print("CS/min:", round(cs_per_min, 2))
    print("Gold:", target["goldEarned"])
    print("Gold/min:", round(gold_per_min, 2))
    print("Damage to Champions:", target["totalDamageDealtToChampions"])
    print("Damage/min:", round(damage_per_min, 2))
    print("Vision Score:", target["visionScore"])

    print("\n=== Share Stats ===")
    print("Kill Participation:", f"{round(kill_participation * 100, 1)}%")
    print("Damage Share:", f"{round(damage_share * 100, 1)}%")
    print("Gold Share:", f"{round(gold_share * 100, 1)}%")

    print("\n=== Items ===")
    items = [target.get(f"item{i}") for i in range(7)]
    print(items)


def mmss(timestamp_ms: int):
    total_seconds = timestamp_ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def analyze_timeline(timeline: dict, target_participant_id: int):
    frames = timeline["info"].get("frames", [])

    death_times = []
    item_purchases = []
    objective_events = []

    for frame in frames:
        for event in frame.get("events", []):
            event_type = event.get("type")
            timestamp = event.get("timestamp", 0)

            if event_type == "CHAMPION_KILL":
                if event.get("victimId") == target_participant_id:
                    death_times.append(timestamp)

            elif event_type == "ITEM_PURCHASED":
                if event.get("participantId") == target_participant_id:
                    item_purchases.append(
                        {
                            "time": timestamp,
                            "item_id": event.get("itemId"),
                        }
                    )

            elif event_type == "ELITE_MONSTER_KILL":
                objective_events.append(
                    {
                        "time": timestamp,
                        "monster": event.get("monsterType"),
                        "killer_id": event.get("killerId"),
                    }
                )

    deaths_before_15 = sum(1 for t in death_times if t <= 15 * 60 * 1000)

    print("\n=== Timeline Analysis ===")
    print("Target Participant ID:", target_participant_id)

    print("\nDeath Times:")
    if death_times:
        print([mmss(t) for t in death_times])
    else:
        print("No deaths recorded.")

    print("Deaths Before 15min:", deaths_before_15)

    print("\nItem Purchase Times:")
    if item_purchases:
        for item in item_purchases[:20]:
            print(f'{mmss(item["time"])} -> itemId={item["item_id"]}')
    else:
        print("No item purchase events found.")

    print("\nObjective Events:")
    if objective_events:
        for obj in objective_events[:20]:
            print(f'{mmss(obj["time"])} -> {obj["monster"]}, killerId={obj["killer_id"]}')
    else:
        print("No elite monster events found.")


def main():
    parser = argparse.ArgumentParser(description="Riot API probe for RiftCoach Agent.")
    parser.add_argument("--game-name", required=True)
    parser.add_argument("--tag-line", required=True)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument(
        "--queue",
        type=int,
        default=420,
        help="420 means ranked solo/duo. Use -1 to disable queue filter.",
    )

    args = parser.parse_args()

    api_key, region = load_config()

    queue = None if args.queue == -1 else args.queue

    print("=== Riot API Probe ===")
    print("Region:", region)
    print("Game Name:", args.game_name)
    print("Tag Line:", args.tag_line)
    print("Queue:", queue if queue is not None else "No queue filter")

    account = get_account_by_riot_id(
        api_key=api_key,
        region=region,
        game_name=args.game_name,
        tag_line=args.tag_line,
    )

    puuid = account["puuid"]

    print("\n=== Account ===")
    print("gameName:", account.get("gameName"))
    print("tagLine:", account.get("tagLine"))
    print("puuid:", puuid[:16] + "...")

    match_ids = get_recent_match_ids(
        api_key=api_key,
        region=region,
        puuid=puuid,
        count=args.count,
        queue=queue,
    )

    if not match_ids and queue is not None:
        print("\n[WARN] No matches found with queue filter. Retrying without queue filter...")
        match_ids = get_recent_match_ids(
            api_key=api_key,
            region=region,
            puuid=puuid,
            count=args.count,
            queue=None,
        )

    print("\n=== Recent Match IDs ===")
    for mid in match_ids:
        print(mid)

    if not match_ids:
        print("\nNo recent matches found. Try another Riot ID.")
        sys.exit(0)

    match_id = match_ids[0]
    print("\nUsing first match:", match_id)

    match_detail = get_match_detail(api_key, region, match_id)
    target = find_target_participant(match_detail, puuid)

    print_match_summary(match_detail, target)

    try:
        timeline = get_match_timeline(api_key, region, match_id)
        analyze_timeline(timeline, target["participantId"])
    except Exception as exc:
        print("\n[WARN] Timeline unavailable or failed to parse.")
        print("Reason:", str(exc))

    print("\nDONE.")


if __name__ == "__main__":
    main()
