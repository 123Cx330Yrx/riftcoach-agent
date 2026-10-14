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
# Audited pair only, not a general major+10 rule. See the RQ-258 source audit.
AUDITED_PATCH_ARTICLES = {
    "16.17": ("26.17", "https://www.leagueoflegends.com/en-gb/news/game-updates/league-of-legends-patch-26-17-notes/"),
}


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
        self.json_ld = []
        self._script = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._script = []
        if tag != "meta":
            return
        key = attrs.get("property") or attrs.get("name")
        if key in ("og:title", "article:published_time"):
            self.values.setdefault(key, set()).add(attrs.get("content", ""))

    def handle_data(self, data):
        if self._script is not None:
            self._script.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            self.json_ld.append("".join(self._script))
            self._script = None


def official_patch_from_html(body, *, patch, retrieved_at, source_patch=None):
    if not isinstance(patch, str) or not re.fullmatch(r"[0-9]+\.[0-9]+", patch):
        raise ValueError("official_patch_invalid")
    if not isinstance(body, bytes) or len(body) > 1_048_576:
        raise ValueError("official_source_invalid")
    source_patch = source_patch or patch
    if source_patch != patch and AUDITED_PATCH_ARTICLES.get(patch, (None,))[0] != source_patch:
        raise ValueError("official_patch_mapping_not_audited")
    parser = _ArticleMetadata()
    try:
        parser.feed(body.decode("utf-8"))
        titles = parser.values.get("og:title", set())
        dates = set(parser.values.get("article:published_time", set()))
        expected_title = r"\bpatch\s+" + re.escape(source_patch) + r"\s+notes\b"
        for script in parser.json_ld:
            document = json.loads(script)
            rows = document.get("@graph", [document]) if isinstance(document, dict) else document
            if not isinstance(rows, list):
                return None
            for article in rows:
                if not isinstance(article, dict) or article.get("@type") not in ("TechArticle", "NewsArticle", "Article"):
                    continue
                headline = article.get("headline")
                if not isinstance(headline, str) or not re.search(expected_title, headline, re.I):
                    return None
                if article.get("version", source_patch) != source_patch:
                    return None
                date = article.get("datePublished")
                if not isinstance(date, str):
                    return None
                dates.add(date)
        if len(titles) != 1 or len(dates) != 1:
            return None
        title = next(iter(titles))
        if not re.search(expected_title, title, re.I):
            return None
        published = datetime.fromisoformat(next(iter(dates)).replace("Z", "+00:00"))
        if published.tzinfo is None or published.utcoffset() is None:
            return None
        return OfficialPatchEvidence(
            patch_version=patch, update_id="riot-patch-" + source_patch.replace(".", "-"),
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
