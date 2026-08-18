from __future__ import annotations

import math

import pytest

from app.workers.polling import PollingPolicy


def test_polling_policy_grows_exponentially_and_caps_without_jitter() -> None:
    policy = PollingPolicy(
        initial_delay_s=0.1,
        maximum_delay_s=0.5,
        multiplier=2.0,
        jitter_ratio=0.0,
    )

    delays = [
        policy.delay_for_idle(idle_count=count, jitter_unit=0.5)
        for count in range(1, 7)
    ]

    assert delays == pytest.approx([0.1, 0.2, 0.4, 0.5, 0.5, 0.5])


def test_polling_jitter_is_deterministic_and_never_exceeds_policy_bounds() -> None:
    policy = PollingPolicy(
        initial_delay_s=1.0,
        maximum_delay_s=4.0,
        multiplier=2.0,
        jitter_ratio=0.25,
    )

    assert policy.delay_for_idle(idle_count=1, jitter_unit=0.0) == pytest.approx(
        0.75
    )
    assert policy.delay_for_idle(idle_count=1, jitter_unit=1.0) == pytest.approx(
        1.25
    )
    assert policy.delay_for_idle(idle_count=9, jitter_unit=0.0) == pytest.approx(
        3.0
    )
    assert policy.delay_for_idle(idle_count=9, jitter_unit=1.0) == pytest.approx(
        4.0
    )

    for idle_count in range(1, 100):
        for jitter_unit in (0.0, 0.1, 0.5, 0.9, 1.0):
            delay = policy.delay_for_idle(
                idle_count=idle_count,
                jitter_unit=jitter_unit,
            )
            assert math.isfinite(delay)
            assert 0.0 < delay <= policy.maximum_delay_s


@pytest.mark.parametrize(
    "kwargs",
    (
        {"initial_delay_s": 0.0},
        {"initial_delay_s": -0.1},
        {"initial_delay_s": 2.0, "maximum_delay_s": 1.0},
        {"multiplier": 0.99},
        {"jitter_ratio": -0.01},
        {"jitter_ratio": 1.0},
        {"jitter_ratio": 1.01},
        {"maximum_delay_s": float("inf")},
    ),
)
def test_polling_policy_rejects_invalid_or_unbounded_configuration(
    kwargs: dict[str, float],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        PollingPolicy(**kwargs)


@pytest.mark.parametrize(
    ("idle_count", "jitter_unit"),
    (
        (0, 0.5),
        (-1, 0.5),
        (True, 0.5),
        (1, -0.01),
        (1, 1.01),
        (1, float("nan")),
    ),
)
def test_polling_delay_rejects_invalid_runtime_inputs(
    idle_count: int,
    jitter_unit: float,
) -> None:
    policy = PollingPolicy()

    with pytest.raises((TypeError, ValueError)):
        policy.delay_for_idle(
            idle_count=idle_count,
            jitter_unit=jitter_unit,
        )
