import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.artifacts import summary_path
from app.lol.data_dragon import DataDragonService
from app.lol.match_analyzer import (
    aggregate_recent_matches,
    analyze_match_detail,
    analyze_match_timeline,
)
from app.lol.riot_client import RiotClient
from app.lol.summary_schema import build_summary_document


def parse_riot_id(value: str) -> tuple[str, str]:
    game_name, separator, tag_line = value.rpartition("#")
    if not separator or not game_name.strip() or not tag_line.strip():
        raise argparse.ArgumentTypeError("Riot ID must use the format gameName#tagLine.")
    return game_name.strip(), tag_line.strip()


def timeline_fallback(error: Exception) -> dict:
    return {
        "timeline_available": False,
        "timeline_status": "unavailable",
        "timeline_error": str(error),
        "death_times": [],
        "deaths_before_10": None,
        "deaths_before_15": None,
        "death_buckets": {},
        "item_purchases": [],
        "objective_events": [],
    }


def process_match(
    *,
    client: RiotClient,
    ddragon: DataDragonService,
    match_id: str,
    puuid: str,
    min_duration_seconds: int,
) -> dict:
    detail = analyze_match_detail(client.get_match_detail(match_id), puuid)
    detail = ddragon.enrich_match_row(detail)

    is_short_game = detail["game_duration_seconds"] < min_duration_seconds
    detail.update(
        {
            "is_short_game": is_short_game,
            "included_in_aggregate": not is_short_game,
            "exclusion_reason": (
                f"game_duration_below_{min_duration_seconds}_seconds"
                if is_short_game
                else None
            ),
        }
    )

    try:
        timeline_row = analyze_match_timeline(
            client.get_match_timeline(match_id),
            detail["participant_id"],
        )
        detail.update(
            {
                "timeline_available": True,
                "timeline_status": "available",
                "timeline_error": None,
                "death_times": timeline_row["death_times"],
                "deaths_before_10": timeline_row["deaths_before_10"],
                "deaths_before_15": timeline_row["deaths_before_15"],
                "death_buckets": timeline_row["death_buckets"],
                "item_purchases": ddragon.enrich_item_purchases(
                    timeline_row["item_purchases"]
                ),
                "objective_events": timeline_row["objective_events"],
            }
        )
    except Exception as error:
        detail.update(timeline_fallback(error))

    return detail


def build_player_summary(
    *,
    client: RiotClient,
    ddragon: DataDragonService,
    game_name: str,
    tag_line: str,
    count: int,
    queue: int | None,
    min_duration_seconds: int,
) -> dict:
    account = client.get_account_by_riot_id(game_name, tag_line)
    puuid = account["puuid"]
    match_ids = client.get_recent_match_ids(puuid=puuid, count=count, queue=queue)

    effective_queue = queue
    queue_fallback_used = False
    if not match_ids and queue is not None:
        match_ids = client.get_recent_match_ids(puuid=puuid, count=count, queue=None)
        effective_queue = None
        queue_fallback_used = True

    match_rows = []
    failed_matches = []
    for match_id in match_ids:
        try:
            match_rows.append(
                process_match(
                    client=client,
                    ddragon=ddragon,
                    match_id=match_id,
                    puuid=puuid,
                    min_duration_seconds=min_duration_seconds,
                )
            )
        except Exception as error:
            failed_matches.append(
                {
                    "match_id": match_id,
                    "stage": "match_detail",
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )

    aggregate_rows = [row for row in match_rows if row["included_in_aggregate"]]
    excluded_matches = [
        {
            "match_id": row["match_id"],
            "reason": row["exclusion_reason"],
            "game_duration_seconds": row["game_duration_seconds"],
        }
        for row in match_rows
        if not row["included_in_aggregate"]
    ]

    return build_summary_document(
        account=account,
        puuid=puuid,
        request={
            "count": count,
            "queue": effective_queue,
            "requested_queue": queue,
            "queue_fallback_used": queue_fallback_used,
            "min_duration_seconds": min_duration_seconds,
            "data_dragon_version": ddragon.version,
            "data_dragon_language": ddragon.language,
        },
        recent_summary=aggregate_recent_matches(aggregate_rows),
        matches=match_rows,
        failed_matches=failed_matches,
        excluded_matches=excluded_matches,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a versioned RiftCoach player summary."
    )
    parser.add_argument(
        "--riot-id",
        required=True,
        help="Riot ID in gameName#tagLine format.",
    )
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument(
        "--queue",
        type=int,
        default=420,
        help="420 means ranked solo/duo. Use -1 to disable the filter.",
    )
    parser.add_argument(
        "--min-duration-seconds",
        type=int,
        default=300,
        help="Shorter matches remain in the output but are excluded from aggregates.",
    )
    parser.add_argument("--output", help="Optional output JSON path.")
    args = parser.parse_args()

    if args.count < 1 or args.count > 100:
        parser.error("--count must be between 1 and 100.")
    if args.min_duration_seconds < 0:
        parser.error("--min-duration-seconds cannot be negative.")

    game_name, tag_line = parse_riot_id(args.riot_id)
    queue = None if args.queue == -1 else args.queue
    client = RiotClient()
    ddragon = DataDragonService(language="zh_CN")

    print("=== Build Player Summary ===")
    print("Riot ID:", f"{game_name}#{tag_line}")
    print("Count:", args.count)
    print("Queue:", queue if queue is not None else "No queue filter")
    print("Minimum aggregate duration:", args.min_duration_seconds)
    print("Data Dragon Version:", ddragon.version)

    output = build_player_summary(
        client=client,
        ddragon=ddragon,
        game_name=game_name,
        tag_line=tag_line,
        count=args.count,
        queue=queue,
        min_duration_seconds=args.min_duration_seconds,
    )

    player = output["player"]
    output_path = Path(args.output) if args.output else summary_path(
        player["game_name"], player["tag_line"]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    timeline_failures = sum(
        row["timeline_status"] != "available" for row in output["matches"]
    )
    print("\n=== DONE ===")
    print("Saved to:", output_path)
    print("Matches received:", output["metadata"]["matches_received"])
    print("Matches analyzed:", output["metadata"]["matches_analyzed"])
    print("Short matches excluded:", len(output["excluded_matches"]))
    print("Timeline unavailable:", timeline_failures)
    print("Detail failures:", len(output["failed_matches"]))


if __name__ == "__main__":
    main()
