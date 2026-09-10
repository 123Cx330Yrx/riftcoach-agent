"""Strict source selection for the explicit golden slice, not production defaults."""
from datetime import datetime
import hashlib
from html.parser import HTMLParser
import json
import re

import requests

from app.evidence.fusion import OfficialPatchEvidence
from app.lol.data_dragon import DataDragonService

_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
_LEGACY_VERSION = re.compile(r"lolpatch_[0-9]+\.[0-9]+")
_GAME_VERSION = re.compile(r"([0-9]+)\.([0-9]+)(?:\.[0-9]+){1,2}")


def select_static_version(game_version, versions):
    match = _GAME_VERSION.fullmatch(game_version) if isinstance(game_version, str) else None
    if match is None:
        raise ValueError("match_patch_invalid")
    if not isinstance(versions, list) or not 1 <= len(versions) <= 5000 or any(
        not isinstance(v, str) or len(v) > 64 or not (_VERSION.fullmatch(v) or _LEGACY_VERSION.fullmatch(v)) for v in versions
    ):
        raise ValueError("static_version_catalog_invalid")
    candidates = [v for v in versions if _VERSION.fullmatch(v) and v.split(".")[:2] == list(match.groups())]
    if not candidates:
        raise ValueError("historical_static_version_unavailable")
    return max(candidates, key=lambda v: tuple(map(int, v.split("."))))


def read_official_bytes(url, *, max_bytes=1_048_576):
    # URLs come exclusively from fixed official origins at the two call sites.
    with requests.get(url, timeout=20, stream=True, allow_redirects=False) as response:
        if response.status_code != 200:
            return None
        body = bytearray()
        for chunk in response.iter_content(chunk_size=65536):
            body.extend(chunk)
            if len(body) > max_bytes:
                raise ValueError("official_source_too_large")
        return bytes(body)


class _ArticleMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = {}

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        attrs = dict(attrs)
        key = attrs.get("property") or attrs.get("name")
        if key in ("og:title", "article:published_time"):
            self.values.setdefault(key, set()).add(attrs.get("content", ""))


def official_patch_from_html(body, *, patch, retrieved_at):
    if not isinstance(patch, str) or not re.fullmatch(r"[0-9]+\.[0-9]+", patch):
        raise ValueError("official_patch_invalid")
    if not isinstance(body, bytes) or len(body) > 1_048_576:
        raise ValueError("official_source_invalid")
    parser = _ArticleMetadata()
    try:
        parser.feed(body.decode("utf-8"))
        titles = parser.values.get("og:title", set())
        dates = parser.values.get("article:published_time", set())
        if len(titles) != 1 or len(dates) != 1:
            return None
        title = next(iter(titles))
        if not re.search(r"\bpatch\s+" + re.escape(patch) + r"\s+notes\b", title, re.I):
            return None
        published = datetime.fromisoformat(next(iter(dates)).replace("Z", "+00:00"))
        if published.tzinfo is None or published.utcoffset() is None:
            return None
        return OfficialPatchEvidence(
            patch_version=patch, update_id="riot-patch-" + patch.replace(".", "-"),
            published_at=published, retrieved_at=retrieved_at, expires_at=None,
            source_digest=hashlib.sha256(body).hexdigest(),
        )
    except (ValueError, UnicodeError):
        return None


class GoldenMatchStaticData:
    """Choose static definitions from each actual match's patch before enriching.

    Multi-patch summaries keep per-row identities. The single-snapshot Evidence
    contract cannot represent them yet, so callers must omit that bundle field.
    """
    def __init__(self, *, language, cache_dir, max_versions=5, versions=None,
                 service_factory=DataDragonService, before_request=None):
        if type(max_versions) is not int or not 1 <= max_versions <= 5:
            raise ValueError("static_version_budget_invalid")
        self.language, self.cache_dir = language, cache_dir
        self._max_versions, self._factory = max_versions, service_factory
        self._versions = versions
        self.services = {}
        self._current = None
        self._before_request = before_request

    @property
    def version(self):
        return next(iter(self.services)) if len(self.services) == 1 else None

    def enrich_match_row(self, row):
        self._current = None
        if self._versions is None:
            if self._before_request is not None:
                self._before_request()
            body = read_official_bytes("https://ddragon.leagueoflegends.com/api/versions.json")
            if body is None:
                raise ValueError("static_version_catalog_unavailable")
            self._versions = json.loads(body)
        version = select_static_version(row.get("game_version"), self._versions)
        if version not in self.services:
            if len(self.services) >= self._max_versions:
                raise ValueError("static_version_budget_exceeded")
            self.services[version] = self._factory(language=self.language, cache_dir=self.cache_dir, version=version,
                                                   before_request=self._before_request)
        self._current = self.services[version]
        enriched = self._current.enrich_match_row(row)
        enriched["data_dragon_version"] = version
        return enriched

    def enrich_item_purchases(self, purchases):
        if self._current is None:
            raise ValueError("static_match_not_selected")
        return self._current.enrich_item_purchases(purchases)
