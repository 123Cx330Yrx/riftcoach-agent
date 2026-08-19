from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from typing import Protocol

import requests

from app.players.models import (
    PlayerLinkFailure,
    ResolvedRiotAccount,
    RoutingRegion,
)


_MAX_RETRY_AFTER_SECONDS = 300


class RiotAccountClient(Protocol):
    def get_account_by_riot_id(
        self,
        game_name: str,
        tag_line: str,
        *,
        timeout_s: float,
    ) -> object: ...


RiotAccountClientFactory = Callable[[str], RiotAccountClient]


class RiotAccountResolutionError(RuntimeError):
    """Safe, body-free failure produced by the Account-V1 boundary."""

    def __init__(
        self,
        failure: PlayerLinkFailure,
        *,
        retry_after_seconds: int | None = None,
    ) -> None:
        if not isinstance(failure, PlayerLinkFailure):
            raise TypeError("failure must be a PlayerLinkFailure")
        if retry_after_seconds is not None:
            if (
                failure.code != "riot_rate_limited"
                or isinstance(retry_after_seconds, bool)
                or not isinstance(retry_after_seconds, int)
                or not 1 <= retry_after_seconds <= _MAX_RETRY_AFTER_SECONDS
            ):
                raise ValueError("retry_after_seconds is not safely bounded")

        self.failure = failure
        self.retry_after_seconds = retry_after_seconds
        # Keep Exception.args body-free. Raw upstream exceptions, responses,
        # URLs, and request identifiers are intentionally never retained.
        super().__init__(failure.code)

    def to_public_dict(self) -> dict[str, str | bool]:
        return {
            "code": self.failure.code,
            "retryable": self.failure.retryable,
        }


class RiotAccountResolver:
    """Resolve one Riot ID into a strict account value through Account-V1.

    Client construction is deferred until ``resolve`` so importing or
    constructing this adapter performs no configuration or network I/O.
    """

    def __init__(
        self,
        *,
        client_factory: RiotAccountClientFactory,
        timeout_s: float = 15.0,
    ) -> None:
        if not callable(client_factory):
            raise TypeError("client_factory must be callable")
        if (
            isinstance(timeout_s, bool)
            or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s)
            or timeout_s <= 0
        ):
            raise ValueError("timeout_s must be a positive finite number")

        self._client_factory = client_factory
        self._timeout_s = float(timeout_s)

    def resolve(
        self,
        *,
        routing_region: RoutingRegion,
        game_name: str,
        tag_line: str,
    ) -> ResolvedRiotAccount:
        if not isinstance(routing_region, RoutingRegion):
            raise TypeError("routing_region must be a RoutingRegion")
        if not isinstance(game_name, str):
            raise TypeError("game_name must be a string")
        if not isinstance(tag_line, str):
            raise TypeError("tag_line must be a string")

        safe_error: RiotAccountResolutionError | None = None
        response: object | None = None
        try:
            client = self._client_factory(routing_region.value)
            response = client.get_account_by_riot_id(
                game_name,
                tag_line,
                timeout_s=self._timeout_s,
            )
        except requests.HTTPError as error:
            safe_error = _map_http_error(error)
        except requests.Timeout:
            safe_error = _resolution_error("upstream_timeout")
        except (requests.ConnectionError, requests.RequestException):
            safe_error = _resolution_error("upstream_unavailable")
        except Exception:
            safe_error = _resolution_error("upstream_unavailable")

        # Raise outside the ``except`` suite so Python does not chain or retain
        # an unsafe upstream exception as this safe error's context.
        if safe_error is not None:
            response = None
            raise safe_error

        account: ResolvedRiotAccount | None = None
        if isinstance(response, Mapping):
            try:
                account = ResolvedRiotAccount(
                    routing_region=routing_region,
                    puuid=response.get("puuid"),
                    game_name=response.get("gameName"),
                    tag_line=response.get("tagLine"),
                )
            except Exception:
                account = None

        # Drop the untrusted response before emitting a safe validation error.
        response = None
        if account is None:
            raise _resolution_error("account_response_invalid")
        return account


def _resolution_error(code: str) -> RiotAccountResolutionError:
    return RiotAccountResolutionError(
        PlayerLinkFailure(
            code=code,
            retryable=code
            in {"riot_rate_limited", "upstream_timeout", "upstream_unavailable"},
        )
    )


def _map_http_error(error: requests.HTTPError) -> RiotAccountResolutionError:
    response = error.response
    status_code = response.status_code if response is not None else None
    if status_code == 404:
        return _resolution_error("player_not_found")
    if status_code in {401, 403}:
        return _resolution_error("riot_authentication_failed")
    if status_code == 429:
        return RiotAccountResolutionError(
            PlayerLinkFailure(code="riot_rate_limited", retryable=True),
            retry_after_seconds=_retry_after_seconds(response),
        )
    return _resolution_error("upstream_unavailable")


def _retry_after_seconds(response: requests.Response | None) -> int | None:
    if response is None:
        return None
    raw_value = response.headers.get("Retry-After")
    if (
        not isinstance(raw_value, str)
        or not raw_value.isascii()
        or not raw_value.isdigit()
    ):
        return None
    value = int(raw_value)
    if not 1 <= value <= _MAX_RETRY_AFTER_SECONDS:
        return None
    return value


__all__ = [
    "RiotAccountClient",
    "RiotAccountClientFactory",
    "RiotAccountResolutionError",
    "RiotAccountResolver",
]
