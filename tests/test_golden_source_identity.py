"""Historical match patches and authentic article timestamps; zero network."""
from datetime import datetime, timezone
import socket
from types import SimpleNamespace

import pytest

from app.evaluation.golden_sources import (
    GoldenMatchStaticData, official_patch_from_html, select_static_version,
)
from app.lol.data_dragon import DataDragonService

NOW = datetime(2026, 9, 10, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("source identity tests must remain offline")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def test_historical_patch_selection_never_uses_latest_unrelated_patch():
    assert select_static_version("16.17.900.1234", ["16.18.1", "16.17.2", "16.17.1", "lolpatch_7.20"]) == "16.17.2"
    with pytest.raises(ValueError, match="unavailable"):
        select_static_version("16.16.900.1234", ["16.18.1", "16.17.1"])


@pytest.mark.parametrize("value", [None, "16.17", "16.17.1/private", "patch 16.17", 1617])
def test_invalid_match_identity_rejected(value):
    with pytest.raises(ValueError, match="invalid"):
        select_static_version(value, ["16.17.1"])


def test_mixed_patches_select_per_match_and_per_match_timeline_without_fake_single_version():
    calls = []
    def factory(**kwargs):
        calls.append(kwargs)
        version = kwargs["version"]
        return SimpleNamespace(
            enrich_match_row=lambda row: {**row, "selected_static": version},
            enrich_item_purchases=lambda rows: [{**row, "selected_static": version} for row in rows],
        )
    service = GoldenMatchStaticData(language="zh_CN", cache_dir="unused",
        versions=["16.18.1", "16.17.1"], service_factory=factory)
    first = service.enrich_match_row({"game_version": "16.17.900.1"})
    assert first["data_dragon_version"] == "16.17.1"
    assert service.version == "16.17.1"
    assert service.enrich_item_purchases([{}])[0]["selected_static"] == "16.17.1"
    service.enrich_match_row({"game_version": "16.18.100.1"})
    assert service.version is None
    assert service.enrich_item_purchases([{}])[0]["selected_static"] == "16.18.1"
    service.enrich_match_row({"game_version": "16.17.900.2"})
    assert len(calls) == 2
    from app.evaluation.coach_real_data_golden_slice import _ddragon_snapshot
    assert _ddragon_snapshot(service, NOW) is None


def test_missing_historical_patch_does_not_reuse_prior_match_service():
    service = GoldenMatchStaticData(language="zh_CN", cache_dir="unused", versions=["16.17.1"],
        service_factory=lambda **kwargs: SimpleNamespace(enrich_match_row=lambda row: row))
    service.enrich_match_row({"game_version": "16.17.1"})
    with pytest.raises(ValueError, match="unavailable"):
        service.enrich_match_row({"game_version": "16.16.1"})
    with pytest.raises(ValueError, match="not_selected"):
        service.enrich_item_purchases([])


def test_pinned_static_service_skips_latest_feed_and_checks_cached_identity(tmp_path, monkeypatch):
    def latest(self):
        raise AssertionError("pinned static definitions must not select latest")
    monkeypatch.setattr(DataDragonService, "_load_latest_version", latest)
    seen = []
    def payload(self, url, path):
        seen.append(url)
        return [] if "runesReforged" in url else {"version": "16.17.1", "data": {}}
    monkeypatch.setattr(DataDragonService, "_get_json", payload)
    service = DataDragonService(cache_dir=tmp_path, version="16.17.1")
    assert service.version == "16.17.1"
    assert len(seen) == 4 and all("/16.17.1/" in url for url in seen)
    with pytest.raises(ValueError, match="mismatch"):
        DataDragonService(cache_dir=tmp_path, version="16.18.1")


def html(title="Patch 16.17 Notes", date="2026-09-01T12:00:00Z"):
    return f'<meta property="og:title" content="{title}"><meta property="article:published_time" content="{date}">'.encode()


def test_patch_article_preserves_publication_time_instead_of_fetch_time():
    evidence = official_patch_from_html(html(), patch="16.17", retrieved_at=NOW)
    assert evidence is not None
    assert evidence.published_at == datetime(2026, 9, 1, 12, tzinfo=timezone.utc)
    assert evidence.published_at != evidence.retrieved_at


@pytest.mark.parametrize("body", [
    b'["16.18.1", "16.17.1"]',
    html(title="Patch 16.18 Notes"),
    html(title="Patch 26.17 Notes"),  # No invented display/internal version mapping.
    html(date="2026-09-01"),
    html(date="2026-09-11T00:00:00Z"),
    html(date="unknown"),
    html() + b'<meta property="article:published_time" content="2026-09-02T00:00:00Z">',
])
def test_unverified_version_or_publication_time_does_not_create_evidence(body):
    assert official_patch_from_html(body, patch="16.17", retrieved_at=NOW) is None


def test_missing_patch_page_never_falls_back_to_version_feed(monkeypatch):
    import app.evaluation.coach_real_data_golden_slice as golden
    calls = []
    def missing(url):
        calls.append(url)
        return None
    monkeypatch.setattr(golden, "read_official_bytes", missing)
    assert golden._official_patch(patch="16.17", retrieved_at=NOW) is None
    assert calls == ["https://www.leagueoflegends.com/en-us/news/game-updates/patch-16-17-notes/"]
