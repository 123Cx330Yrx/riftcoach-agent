"""Tool definitions adapting the existing Riot API client."""

from __future__ import annotations

from typing import Any, Callable, Mapping

import requests

from ..errors import ToolError
from ..models import (
    CachePolicy,
    CircuitBreakerPolicy,
    RetryPolicy,
    ToolContext,
    ToolDefinition,
    ToolPolicy,
)


def _riot_policy(*, cache_ttl_s: float) -> ToolPolicy:
    return ToolPolicy(
        timeout_s=30.0,
        retry=RetryPolicy(
            max_attempts=3,
            base_delay_s=0.25,
            max_delay_s=1.0,
        ),
        cache=CachePolicy(ttl_s=cache_ttl_s),
        circuit_breaker=CircuitBreakerPolicy(
            failure_threshold=3,
            recovery_s=30.0,
        ),
    )


def _safe_riot_call(call: Callable[[], Any]) -> Any:
    try:
        return call()
    except requests.Timeout as exc:
        raise ToolError(
            "Riot API request timed out",
            tool_name="riot.api",
            code="riot_timeout",
            retryable=True,
        ) from exc
    except requests.ConnectionError as exc:
        raise ToolError(
            "Riot API connection failed",
            tool_name="riot.api",
            code="riot_connection_failed",
            retryable=True,
        ) from exc
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 0
        if status in (401, 403):
            code, retryable = "riot_authentication_failed", False
        elif status == 429:
            code, retryable = "riot_rate_limited", True
        elif status >= 500:
            code, retryable = "riot_service_unavailable", True
        else:
            code, retryable = "riot_request_rejected", False
        raise ToolError(
            "Riot API rejected the request",
            tool_name="riot.api",
            code=code,
            retryable=retryable,
        ) from exc


def _object_wrapper_schema(field_name: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {field_name: {"type": "object"}},
        "required": [field_name],
        "additionalProperties": False,
    }


def build_riot_tools(client: Any) -> tuple[ToolDefinition, ...]:
    def account_handler(
        params: Mapping[str, Any],
        context: ToolContext,
    ) -> Mapping[str, Any]:
        account = _safe_riot_call(
            lambda: client.get_account_by_riot_id(
                params["game_name"],
                params["tag_line"],
                timeout_s=context.remaining_s(),
            )
        )
        return {"account": account}

    def matches_handler(
        params: Mapping[str, Any],
        context: ToolContext,
    ) -> Mapping[str, Any]:
        match_ids = _safe_riot_call(
            lambda: client.get_recent_match_ids(
                params["puuid"],
                params["count"],
                params.get("queue"),
                timeout_s=context.remaining_s(),
            )
        )
        return {"match_ids": match_ids}

    def detail_handler(
        params: Mapping[str, Any],
        context: ToolContext,
    ) -> Mapping[str, Any]:
        match = _safe_riot_call(
            lambda: client.get_match_detail(
                params["match_id"],
                timeout_s=context.remaining_s(),
            )
        )
        return {"match": match}

    def timeline_handler(
        params: Mapping[str, Any],
        context: ToolContext,
    ) -> Mapping[str, Any]:
        timeline = _safe_riot_call(
            lambda: client.get_match_timeline(
                params["match_id"],
                timeout_s=context.remaining_s(),
            )
        )
        return {"timeline": timeline}

    riot_id_input = {
        "type": "object",
        "properties": {
            "game_name": {"type": "string", "minLength": 1},
            "tag_line": {"type": "string", "minLength": 1},
        },
        "required": ["game_name", "tag_line"],
        "additionalProperties": False,
    }
    recent_input = {
        "type": "object",
        "properties": {
            "puuid": {"type": "string", "minLength": 1},
            "count": {"type": "integer", "minimum": 1, "maximum": 100},
            "queue": {"type": ["integer", "null"]},
        },
        "required": ["puuid", "count", "queue"],
        "additionalProperties": False,
    }
    match_input = {
        "type": "object",
        "properties": {"match_id": {"type": "string", "minLength": 1}},
        "required": ["match_id"],
        "additionalProperties": False,
    }

    return (
        ToolDefinition(
            name="riot.account_by_riot_id",
            version="1.0.0",
            description="Resolve a Riot ID to a Riot account.",
            handler=account_handler,
            input_schema=riot_id_input,
            output_schema=_object_wrapper_schema("account"),
            policy=_riot_policy(cache_ttl_s=60.0),
        ),
        ToolDefinition(
            name="riot.recent_match_ids",
            version="1.0.0",
            description="Fetch recent match IDs for one PUUID.",
            handler=matches_handler,
            input_schema=recent_input,
            output_schema={
                "type": "object",
                "properties": {
                    "match_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    }
                },
                "required": ["match_ids"],
                "additionalProperties": False,
            },
            policy=_riot_policy(cache_ttl_s=15.0),
        ),
        ToolDefinition(
            name="riot.match_detail",
            version="1.0.0",
            description="Fetch immutable post-game match detail.",
            handler=detail_handler,
            input_schema=match_input,
            output_schema=_object_wrapper_schema("match"),
            policy=_riot_policy(cache_ttl_s=300.0),
        ),
        ToolDefinition(
            name="riot.match_timeline",
            version="1.0.0",
            description="Fetch immutable post-game match timeline.",
            handler=timeline_handler,
            input_schema=match_input,
            output_schema=_object_wrapper_schema("timeline"),
            policy=_riot_policy(cache_ttl_s=300.0),
        ),
    )
