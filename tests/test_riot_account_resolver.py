from __future__ import annotations

from collections.abc import Mapping

import pytest
import requests

from app.lol.account_resolver import (
    RiotAccountResolutionError,
    RiotAccountResolver,
)
from app.players.models import ResolvedRiotAccount, RoutingRegion


class FakeRiotAccountClient:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.calls: list[tuple[str, str, float]] = []

    def get_account_by_riot_id(
        self,
        game_name: str,
        tag_line: str,
        *,
        timeout_s: float,
    ) -> object:
        self.calls.append((game_name, tag_line, timeout_s))
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


class RecordingClientFactory:
    def __init__(self, client: FakeRiotAccountClient) -> None:
        self.client = client
        self.routing_calls: list[str] = []

    def __call__(self, routing_region: str) -> FakeRiotAccountClient:
        self.routing_calls.append(routing_region)
        return self.client


def _resolver(
    outcome: object,
    *,
    timeout_s: float = 7.5,
) -> tuple[RiotAccountResolver, RecordingClientFactory, FakeRiotAccountClient]:
    client = FakeRiotAccountClient(outcome)
    factory = RecordingClientFactory(client)
    return (
        RiotAccountResolver(client_factory=factory, timeout_s=timeout_s),
        factory,
        client,
    )


def _http_error(status_code: int, *, retry_after: str | None = None) -> Exception:
    response = requests.Response()
    response.status_code = status_code
    response.url = "https://asia.api.riotgames.com/private?token=secret"
    response._content = b"private upstream response secret"
    response.headers["X-Request-ID"] = "private-request-id"
    if retry_after is not None:
        response.headers["Retry-After"] = retry_after
    return requests.HTTPError(
        "private exception C:\\Users\\secret\\.env",
        response=response,
    )


def test_resolver_construction_is_no_io_and_success_is_strictly_normalized() -> None:
    resolver, factory, client = _resolver(
        {
            "puuid": "stable_puuid-123",
            "gameName": " Confirmed Player ",
            "tagLine": " KR1 ",
            "ignoredFutureField": "safe-to-ignore",
        }
    )

    assert factory.routing_calls == []
    assert client.calls == []

    result = resolver.resolve(
        routing_region=RoutingRegion.ASIA,
        game_name="Requested Player",
        tag_line="TEST",
    )

    assert result == ResolvedRiotAccount(
        routing_region=RoutingRegion.ASIA,
        puuid="stable_puuid-123",
        game_name="Confirmed Player",
        tag_line="KR1",
    )
    assert factory.routing_calls == ["asia"]
    assert client.calls == [("Requested Player", "TEST", 7.5)]


@pytest.mark.parametrize("routing_region", ("cn", "zh_CN", "ASIA", None))
def test_invalid_routing_never_reaches_client_factory(routing_region: object) -> None:
    resolver, factory, client = _resolver(
        {"puuid": "p", "gameName": "Player", "tagLine": "TAG"}
    )

    with pytest.raises(TypeError, match="routing_region"):
        resolver.resolve(
            routing_region=routing_region,  # type: ignore[arg-type]
            game_name="Player",
            tag_line="TAG",
        )

    assert factory.routing_calls == []
    assert client.calls == []


@pytest.mark.parametrize(
    "status_code, expected_code, expected_retryable",
    (
        (404, "player_not_found", False),
        (401, "riot_authentication_failed", False),
        (403, "riot_authentication_failed", False),
        (429, "riot_rate_limited", True),
        (500, "upstream_unavailable", True),
        (503, "upstream_unavailable", True),
        (400, "upstream_unavailable", True),
    ),
)
def test_http_failures_map_to_allowlisted_body_free_errors(
    status_code: int,
    expected_code: str,
    expected_retryable: bool,
) -> None:
    resolver, _, _ = _resolver(
        _http_error(status_code, retry_after="17" if status_code == 429 else None)
    )

    with pytest.raises(RiotAccountResolutionError) as caught:
        resolver.resolve(
            routing_region=RoutingRegion.ASIA,
            game_name="Player",
            tag_line="TAG",
        )

    error = caught.value
    assert error.failure.code == expected_code
    assert error.failure.retryable is expected_retryable
    assert error.retry_after_seconds == (17 if status_code == 429 else None)
    assert error.to_public_dict() == {
        "code": expected_code,
        "retryable": expected_retryable,
    }
    serialized = f"{error!r} {error} {vars(error)} {error.to_public_dict()}"
    assert "private" not in serialized
    assert "secret" not in serialized
    assert "request-id" not in serialized
    assert error.__context__ is None
    assert error.__cause__ is None


@pytest.mark.parametrize(
    "retry_after, expected",
    (
        ("1", 1),
        ("300", 300),
        (None, None),
        ("0", None),
        ("301", None),
        ("1.5", None),
        (" 17 ", None),
        ("１７", None),
        ("private", None),
    ),
)
def test_rate_limit_retry_after_is_bounded_ascii_only(
    retry_after: str | None,
    expected: int | None,
) -> None:
    resolver, _, _ = _resolver(_http_error(429, retry_after=retry_after))

    with pytest.raises(RiotAccountResolutionError) as caught:
        resolver.resolve(
            routing_region=RoutingRegion.ASIA,
            game_name="Player",
            tag_line="TAG",
        )

    assert caught.value.failure.code == "riot_rate_limited"
    assert caught.value.retry_after_seconds == expected


@pytest.mark.parametrize(
    "upstream_error, expected_code",
    (
        (requests.Timeout("private timeout secret"), "upstream_timeout"),
        (
            requests.ConnectionError("private connection request-id"),
            "upstream_unavailable",
        ),
        (requests.RequestException("private request body"), "upstream_unavailable"),
        (RuntimeError("private unexpected client error"), "upstream_unavailable"),
    ),
)
def test_transport_and_unexpected_failures_are_safely_classified(
    upstream_error: Exception,
    expected_code: str,
) -> None:
    resolver, _, _ = _resolver(upstream_error)

    with pytest.raises(RiotAccountResolutionError) as caught:
        resolver.resolve(
            routing_region=RoutingRegion.EUROPE,
            game_name="Player",
            tag_line="TAG",
        )

    error = caught.value
    assert error.failure.code == expected_code
    assert error.failure.retryable is True
    assert "private" not in repr(error)
    assert "private" not in str(error)
    assert error.__context__ is None
    assert error.__cause__ is None


@pytest.mark.parametrize(
    "response",
    (
        None,
        [],
        {},
        {"puuid": "p", "gameName": "Player"},
        {"puuid": 7, "gameName": "Player", "tagLine": "TAG"},
        {"puuid": "p", "gameName": " ", "tagLine": "TAG"},
        {"puuid": "p", "gameName": "Player", "tagLine": "\n"},
        {"puuid": "bad value", "gameName": "Player", "tagLine": "TAG"},
        {"puuid": "p" * 129, "gameName": "Player", "tagLine": "TAG"},
        {"puuid": "p", "gameName": "G" * 65, "tagLine": "TAG"},
        {"puuid": "p", "gameName": "Player", "tagLine": "T" * 33},
    ),
)
def test_invalid_account_response_fails_closed(response: object) -> None:
    resolver, _, _ = _resolver(response)

    with pytest.raises(RiotAccountResolutionError) as caught:
        resolver.resolve(
            routing_region=RoutingRegion.SEA,
            game_name="Player",
            tag_line="TAG",
        )

    assert caught.value.failure.code == "account_response_invalid"
    assert caught.value.failure.retryable is False
    assert caught.value.retry_after_seconds is None


def test_factory_failure_is_safe_and_does_not_retain_exception() -> None:
    def broken_factory(_routing_region: str) -> FakeRiotAccountClient:
        raise RuntimeError("private factory secret")

    resolver = RiotAccountResolver(client_factory=broken_factory)

    with pytest.raises(RiotAccountResolutionError) as caught:
        resolver.resolve(
            routing_region=RoutingRegion.AMERICAS,
            game_name="Player",
            tag_line="TAG",
        )

    assert caught.value.to_public_dict() == {
        "code": "upstream_unavailable",
        "retryable": True,
    }
    assert "private" not in repr(caught.value)
    assert "secret" not in str(caught.value)
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None


def test_response_must_be_a_mapping_not_a_mapping_like_object() -> None:
    class MappingLike:
        def get(self, _key: str) -> str:
            return "pretend"

    resolver, _, _ = _resolver(MappingLike())

    with pytest.raises(RiotAccountResolutionError) as caught:
        resolver.resolve(
            routing_region=RoutingRegion.ASIA,
            game_name="Player",
            tag_line="TAG",
        )

    assert caught.value.failure.code == "account_response_invalid"


def test_real_dict_satisfies_the_mapping_boundary() -> None:
    response: Mapping[str, object] = {
        "puuid": "p",
        "gameName": "Player",
        "tagLine": "TAG",
    }
    resolver, _, _ = _resolver(response)

    assert resolver.resolve(
        routing_region=RoutingRegion.ASIA,
        game_name="Player",
        tag_line="TAG",
    ).puuid == "p"
