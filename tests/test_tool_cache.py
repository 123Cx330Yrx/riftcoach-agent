from app.tools.cache import TTLCache, make_cache_key


class FakeClock:
    def __init__(self, now: float = 100.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_cache_hit_and_expiration():
    clock = FakeClock()
    cache = TTLCache(max_entries=10, clock=clock)

    cache.set("key", {"value": 1}, ttl_s=5)

    assert cache.get("key") == {"value": 1}
    clock.advance(4.9)
    assert cache.get("key") == {"value": 1}
    clock.advance(0.2)
    assert cache.get("key") is None
    assert len(cache) == 0


def test_zero_ttl_does_not_store():
    cache = TTLCache(max_entries=10, clock=FakeClock())

    cache.set("key", {"value": 1}, ttl_s=0)

    assert cache.get("key") is None
    assert len(cache) == 0


def test_cache_key_is_stable_for_equivalent_nested_parameters():
    first = make_cache_key(
        "riot.recent_matches",
        "1.0.0",
        {"count": 10, "player": {"tag": "KR1", "name": "Demo"}},
    )
    second = make_cache_key(
        "riot.recent_matches",
        "1.0.0",
        {"player": {"name": "Demo", "tag": "KR1"}, "count": 10},
    )

    assert first == second
    assert "Demo" not in first
    assert "KR1" not in first


def test_different_tool_version_produces_different_cache_key():
    params = {"message": "same"}

    assert make_cache_key("system.echo", "1.0.0", params) != make_cache_key(
        "system.echo", "2.0.0", params
    )


def test_capacity_evicts_least_recently_used_entry():
    clock = FakeClock()
    cache = TTLCache(max_entries=2, clock=clock)
    cache.set("first", {"value": 1}, ttl_s=60)
    clock.advance(1)
    cache.set("second", {"value": 2}, ttl_s=60)

    assert cache.get("first") == {"value": 1}
    clock.advance(1)
    cache.set("third", {"value": 3}, ttl_s=60)

    assert cache.get("first") == {"value": 1}
    assert cache.get("second") is None
    assert cache.get("third") == {"value": 3}


def test_invalid_cache_configuration_is_rejected():
    for invalid_size in (0, -1):
        try:
            TTLCache(max_entries=invalid_size)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid max_entries should fail")

    cache = TTLCache(max_entries=1)
    try:
        cache.set("key", {"value": 1}, ttl_s=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative ttl should fail")

