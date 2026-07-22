from datetime import datetime, timezone


SUMMARY_SCHEMA_VERSION = "1.0"


class SummaryValidationError(ValueError):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_summary_document(summary: dict) -> None:
    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        raise SummaryValidationError(
            f"Unsupported summary schema: {summary.get('schema_version')!r}"
        )

    for key in ("metadata", "player", "request", "recent_summary", "matches"):
        if key not in summary:
            raise SummaryValidationError(f"Summary is missing required field: {key}")

    player = summary["player"]
    for key in ("game_name", "tag_line", "riot_id"):
        if not player.get(key):
            raise SummaryValidationError(f"Player is missing required field: {key}")

    if not isinstance(summary["matches"], list):
        raise SummaryValidationError("matches must be a list")
    if not isinstance(summary.get("failed_matches", []), list):
        raise SummaryValidationError("failed_matches must be a list")
    if not isinstance(summary.get("excluded_matches", []), list):
        raise SummaryValidationError("excluded_matches must be a list")

    for row in summary["matches"]:
        for key in (
            "match_id",
            "game_duration_seconds",
            "champion_id",
            "champion_name",
            "role",
            "win",
            "timeline_status",
            "included_in_aggregate",
        ):
            if key not in row:
                raise SummaryValidationError(
                    f"Match row is missing required field {key}: {row.get('match_id')}"
                )


def build_summary_document(
    *,
    account: dict,
    puuid: str,
    request: dict,
    recent_summary: dict,
    matches: list[dict],
    failed_matches: list[dict],
    excluded_matches: list[dict],
) -> dict:
    document = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "metadata": {
            "generated_at_utc": utc_now_iso(),
            "source": "Riot API",
            "matches_requested": request.get("count"),
            "matches_received": len(matches) + len(failed_matches),
            "matches_analyzed": recent_summary.get("games_analyzed", 0),
        },
        "player": {
            "game_name": account.get("gameName"),
            "tag_line": account.get("tagLine"),
            "riot_id": f'{account.get("gameName")}#{account.get("tagLine")}',
            "puuid_prefix": puuid[:16] + "...",
        },
        "request": request,
        "recent_summary": recent_summary,
        "matches": matches,
        "failed_matches": failed_matches,
        "excluded_matches": excluded_matches,
    }
    validate_summary_document(document)
    return document
