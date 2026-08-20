"""Build a versioned recent-match Summary from injected Riot/static data."""

from __future__ import annotations

from typing import Any, Protocol

from app.lol.match_analyzer import (
    aggregate_recent_matches,
    analyze_match_detail,
    analyze_match_timeline,
)
from app.lol.summary_schema import build_summary_document


class RiotMatchClient(Protocol):
    def get_account_by_riot_id(self, game_name: str, tag_line: str) -> dict: ...

    def get_recent_match_ids(
        self,
        puuid: str,
        count: int,
        queue: int | None,
    ) -> list[str]: ...

    def get_match_detail(self, match_id: str) -> dict: ...

    def get_match_timeline(self, match_id: str) -> dict: ...


class MatchStaticDataService(Protocol):
    version: str
    language: str

    def enrich_match_row(self, row: dict) -> dict: ...

    def enrich_item_purchases(self, purchases: list[dict]) -> list[dict]: ...


def timeline_fallback(error: Exception) -> dict[str, Any]:
    """Preserve a local diagnostic while marking timeline facts unavailable."""

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
    client: RiotMatchClient,
    ddragon: MatchStaticDataService,
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
    client: RiotMatchClient,
    ddragon: MatchStaticDataService,
    game_name: str,
    tag_line: str,
    count: int,
    queue: int | None,
    min_duration_seconds: int,
) -> dict:
    account = client.get_account_by_riot_id(game_name, tag_line)
    puuid = account["puuid"]
    return _build_player_summary_for_account(
        client=client,
        ddragon=ddragon,
        account=account,
        puuid=puuid,
        count=count,
        queue=queue,
        min_duration_seconds=min_duration_seconds,
    )


def build_player_summary_by_puuid(
    *,
    client: RiotMatchClient,
    ddragon: MatchStaticDataService,
    puuid: str,
    game_name: str,
    tag_line: str,
    count: int,
    queue: int | None,
    min_duration_seconds: int,
) -> dict:
    """Build from a server-trusted subject without Account-V1 lookup."""

    if not all(
        isinstance(value, str) and value.strip()
        for value in (puuid, game_name, tag_line)
    ):
        raise ValueError("trusted player identity must contain visible text")
    account = {
        "gameName": game_name,
        "tagLine": tag_line,
        "puuid": puuid,
    }
    return _build_player_summary_for_account(
        client=client,
        ddragon=ddragon,
        account=account,
        puuid=puuid,
        count=count,
        queue=queue,
        min_duration_seconds=min_duration_seconds,
    )


def _build_player_summary_for_account(
    *,
    client: RiotMatchClient,
    ddragon: MatchStaticDataService,
    account: dict,
    puuid: str,
    count: int,
    queue: int | None,
    min_duration_seconds: int,
) -> dict:
    match_ids = client.get_recent_match_ids(
        puuid=puuid,
        count=count,
        queue=queue,
    )

    effective_queue = queue
    queue_fallback_used = False
    if not match_ids and queue is not None:
        match_ids = client.get_recent_match_ids(
            puuid=puuid,
            count=count,
            queue=None,
        )
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

    aggregate_rows = [
        row for row in match_rows if row["included_in_aggregate"]
    ]
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


class RiotPlayerSummaryBuilder:
    """Bind long-lived upstream dependencies without reading configuration."""

    def __init__(
        self,
        *,
        client: RiotMatchClient,
        ddragon: MatchStaticDataService,
        min_duration_seconds: int = 300,
    ) -> None:
        if (
            isinstance(min_duration_seconds, bool)
            or not isinstance(min_duration_seconds, int)
            or min_duration_seconds < 0
        ):
            raise ValueError("min_duration_seconds must be a non-negative integer")
        self._client = client
        self._ddragon = ddragon
        self._min_duration_seconds = min_duration_seconds

    def build(
        self,
        *,
        game_name: str,
        tag_line: str,
        count: int,
        queue: int | None,
    ) -> dict:
        return build_player_summary(
            client=self._client,
            ddragon=self._ddragon,
            game_name=game_name,
            tag_line=tag_line,
            count=count,
            queue=queue,
            min_duration_seconds=self._min_duration_seconds,
        )

    def build_by_puuid(
        self,
        *,
        puuid: str,
        game_name: str,
        tag_line: str,
        count: int,
        queue: int | None,
    ) -> dict:
        return build_player_summary_by_puuid(
            client=self._client,
            ddragon=self._ddragon,
            puuid=puuid,
            game_name=game_name,
            tag_line=tag_line,
            count=count,
            queue=queue,
            min_duration_seconds=self._min_duration_seconds,
        )


__all__ = [
    "MatchStaticDataService",
    "RiotMatchClient",
    "RiotPlayerSummaryBuilder",
    "build_player_summary",
    "build_player_summary_by_puuid",
    "process_match",
    "timeline_fallback",
]
