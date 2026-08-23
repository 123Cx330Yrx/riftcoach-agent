"""Run one bounded, body-free Riot Account/Match validation.

This command is intentionally separate from the public no-I/O CI path. It reads
the local Riot key only when ``--execute`` is supplied, performs one account
lookup, one recent-match query and one match-detail lookup, and persists only
allowlisted facts/digests. It never writes a PUUID, raw match response, raw
exception, or API key.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import quote

import requests

from app.lol.riot_client import RiotClient


ROOT = Path(__file__).resolve().parents[1]
_MAX_GAME_NAME_LENGTH = 64
_MAX_TAG_LINE_LENGTH = 32
_REGIONS = frozenset({"americas", "asia", "europe", "sea"})
_ROLES = frozenset({"self", "observed"})


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_riot_id(value: str) -> tuple[str, str, str]:
    if not isinstance(value, str):
        raise ValueError("riot_id must be a string")
    normalized = value.strip()
    game_name, separator, tag_line = normalized.rpartition("#")
    game_name = game_name.strip()
    tag_line = tag_line.strip()
    if (
        not separator
        or not game_name
        or not tag_line
        or len(game_name) > _MAX_GAME_NAME_LENGTH
        or len(tag_line) > _MAX_TAG_LINE_LENGTH
        or any(ord(character) < 32 for character in normalized)
    ):
        raise ValueError("riot_id must use a bounded gameName#tagLine")
    return game_name, tag_line, f"{game_name}#{tag_line}"


def _safe_failure(error: BaseException) -> str:
    if isinstance(error, requests.HTTPError):
        response = error.response
        status = response.status_code if response is not None else None
        if status in {401, 403}:
            return "riot_authentication_failed"
        if status == 404:
            return "player_not_found"
        if status == 429:
            return "riot_rate_limited"
        return "riot_http_error"
    if isinstance(error, requests.Timeout):
        return "upstream_timeout"
    if isinstance(error, requests.ConnectionError):
        return "upstream_unavailable"
    if isinstance(error, requests.RequestException):
        return "upstream_unavailable"
    if isinstance(error, RuntimeError) and "RIOT_API_KEY" in str(error):
        return "riot_key_missing"
    return "validation_failed"


def _match_projection(match: Mapping[str, Any], *, puuid: str) -> dict[str, Any]:
    info = match.get("info")
    if not isinstance(info, Mapping):
        raise ValueError("match info is invalid")
    participants = info.get("participants")
    if not isinstance(participants, list):
        raise ValueError("match participants are invalid")
    participant = next(
        (
            item
            for item in participants
            if isinstance(item, Mapping) and item.get("puuid") == puuid
        ),
        None,
    )
    if not isinstance(participant, Mapping):
        raise ValueError("target participant is missing")
    kills = participant.get("kills")
    deaths = participant.get("deaths")
    assists = participant.get("assists")
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in (kills, deaths, assists)):
        raise ValueError("target combat facts are invalid")
    return {
        "game_version": info.get("gameVersion") if isinstance(info.get("gameVersion"), str) else None,
        "queue_id": info.get("queueId") if isinstance(info.get("queueId"), int) else None,
        "game_duration_seconds": (
            info.get("gameDuration")
            if isinstance(info.get("gameDuration"), int)
            else None
        ),
        "participant_count": len(participants),
        "target": {
            "champion_id": (
                participant.get("championId")
                if isinstance(participant.get("championId"), int)
                else None
            ),
            "champion": participant.get("championName") if isinstance(participant.get("championName"), str) else None,
            "role": (
                participant.get("teamPosition")
                if isinstance(participant.get("teamPosition"), str)
                else participant.get("individualPosition")
                if isinstance(participant.get("individualPosition"), str)
                else None
            ),
            "win": participant.get("win") if isinstance(participant.get("win"), bool) else None,
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
        },
    }


def run_validation(
    *,
    riot_id: str,
    region: str,
    relationship_role: str,
    count: int = 1,
    queue: int | None = 420,
    client_factory: Callable[..., RiotClient] = RiotClient,
) -> dict[str, Any]:
    game_name, tag_line, normalized_riot_id = parse_riot_id(riot_id)
    if region not in _REGIONS:
        raise ValueError("region is not an admitted Riot regional routing")
    if relationship_role not in _ROLES:
        raise ValueError("relationship_role is invalid")
    if isinstance(count, bool) or not 1 <= count <= 3:
        raise ValueError("count must be between one and three")

    started = time.perf_counter()
    calls = {"account": 0, "recent_match_ids": 0, "match_detail": 0}
    try:
        client = client_factory(region=region)
        calls["account"] += 1
        account = client.get_account_by_riot_id(game_name, tag_line, timeout_s=15)
        if not isinstance(account, Mapping) or not isinstance(account.get("puuid"), str):
            raise ValueError("account response is invalid")
        puuid = account["puuid"]
        resolved_name = account.get("gameName")
        resolved_tag = account.get("tagLine")
        if not isinstance(resolved_name, str) or not isinstance(resolved_tag, str):
            raise ValueError("account display identity is invalid")

        calls["recent_match_ids"] += 1
        match_ids = client.get_recent_match_ids(
            puuid,
            count=count,
            queue=queue,
            timeout_s=15,
        )
        if not isinstance(match_ids, list) or not all(isinstance(item, str) for item in match_ids):
            raise ValueError("recent match response is invalid")
        if not match_ids:
            raise LookupError("no recent matches")

        selected_match_id = match_ids[0]
        calls["match_detail"] += 1
        match_detail = client.get_match_detail(selected_match_id, timeout_s=15)
        if not isinstance(match_detail, Mapping):
            raise ValueError("match detail response is invalid")
        projection = _match_projection(match_detail, puuid=puuid)
        result: dict[str, Any] = {
            "schema_version": "1.0",
            "result": "passed",
            "body_free": True,
            "source": "riot_official_api",
            "relationship_role": relationship_role,
            "requested_riot_id": normalized_riot_id,
            "resolved_riot_id": f"{resolved_name.strip()}#{resolved_tag.strip()}",
            "routing_region": region,
            "identity": {"puuid_digest": _digest(puuid)},
            "matches": {
                "returned_count": len(match_ids),
                "match_ids_digest": _digest("\n".join(match_ids)),
                "selected_match_id_digest": _digest(selected_match_id),
            },
            "match": projection,
            "calls": calls,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "external_io": {
                "riot_calls": sum(calls.values()),
                "opgg_tools_call_calls": 0,
                "llm_provider_calls": 0,
                "key_reads": 1,
            },
            "limitations": [
                "account_control_not_verified",
                "single_match_observation",
                "timeline_not_requested",
                "raw_response_not_persisted",
            ],
        }
        return result
    except LookupError:
        error_code = "no_recent_matches"
    except BaseException as error:  # noqa: BLE001 - sanitize every boundary error
        error_code = _safe_failure(error)
    return {
        "schema_version": "1.0",
        "result": "failed",
        "body_free": True,
        "source": "riot_official_api",
        "relationship_role": relationship_role,
        "requested_riot_id": normalized_riot_id,
        "routing_region": region,
        "calls": calls,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "external_io": {
            "riot_calls": sum(calls.values()),
            "opgg_tools_call_calls": 0,
            "llm_provider_calls": 0,
            "key_reads": 1,
        },
        "error_code": error_code,
        "limitations": ["raw_response_not_persisted"],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--riot-id", required=True)
    parser.add_argument("--region", choices=sorted(_REGIONS), required=True)
    parser.add_argument("--relationship-role", choices=sorted(_ROLES), default="observed")
    parser.add_argument("--count", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--queue", type=int, default=420, help="Use -1 to disable queue filtering.")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.execute:
        raise SystemExit("refusing external I/O without --execute")
    output = args.output.resolve()
    try:
        output.relative_to(ROOT)
    except ValueError as error:
        raise SystemExit("output must be inside the repository") from error
    if output.exists():
        raise SystemExit("refusing to overwrite an existing validation result")
    result = run_validation(
        riot_id=args.riot_id,
        region=args.region,
        relationship_role=args.relationship_role,
        count=args.count,
        queue=None if args.queue == -1 else args.queue,
    )
    result["observed_at"] = datetime.now(timezone.utc).isoformat()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": result["result"], "body_free": True, "output": str(output)}, sort_keys=True))
    return 0 if result["result"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
