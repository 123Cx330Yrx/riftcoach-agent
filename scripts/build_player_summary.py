import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.artifacts import summary_path
from app.lol.data_dragon import DataDragonService
from app.lol.player_summary import build_player_summary
from app.lol.riot_client import RiotClient


def parse_riot_id(value: str) -> tuple[str, str]:
    game_name, separator, tag_line = value.rpartition("#")
    if not separator or not game_name.strip() or not tag_line.strip():
        raise argparse.ArgumentTypeError("Riot ID must use the format gameName#tagLine.")
    return game_name.strip(), tag_line.strip()


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
