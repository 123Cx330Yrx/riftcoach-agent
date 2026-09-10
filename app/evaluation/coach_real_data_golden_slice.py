"""Bounded real-data Coach golden-slice orchestration.

The module keeps acquisition outside the evidence kernel and writes only a
body-free receipt.  A run freezes one player request, source budget and run
identity before network I/O; the same materialized Summary is then consumed by
Evidence and the Coach application seam.  Production registration/defaults are
intentionally impossible here.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from dataclasses import replace
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import requests
from pydantic import BaseModel, ConfigDict, Field

from app.api.evidence_models import EvidencePublicProjectionResponse
from app.evidence.adapters import data_dragon_snapshot_from_identity
from app.evidence.fusion import OfficialPatchEvidence
from app.evidence.summary_bridge import summary_to_evidence
from app.evidence.publication import EvidencePublicationContext, EvidencePublicationSources
from app.evidence.publication_store import FileEvidencePublicationStore
from app.lol.data_dragon import DataDragonService
from app.lol.player_summary import build_player_summary
from app.lol.riot_client import RiotClient
from app.lol.report_renderer import render_deterministic_report
from app.meta.models import MetaEvidence
from app.providers.config import load_zhipu_settings


ROOT = Path(__file__).resolve().parents[2]
_REGIONS = frozenset({"americas", "asia", "europe", "sea"})
_POSITIONS = frozenset({"top", "mid", "jungle", "adc", "support"})
_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class GoldenSlicePreflight(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    run_id: str = Field(min_length=8, max_length=96)
    riot_id: str = Field(min_length=3, max_length=97)
    routing_region: str
    queue: int = Field(gt=0, le=10_000)
    count: int = Field(ge=1, le=5)
    position: str
    max_riot_calls: int = Field(ge=1, le=20)
    max_ddragon_requests: int = Field(ge=1, le=5)
    max_opgg_tool_calls: int = Field(ge=1, le=1)
    provider_enabled: bool = False
    network_allowed: bool = False


class GoldenSliceReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    run_id: str
    implementation_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    result: str
    body_free: bool = True
    summary_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    summary_matches_analyzed: int = Field(ge=1, le=5)
    evidence_bundle_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_projection: dict[str, Any]
    training_plan: tuple[str, ...] = Field(min_length=1, max_length=5)
    training_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    coach_report_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    coach_runtime_status: str | None = None
    coach_publication_status: str | None = None
    coach_terminal_reason: str | None = None
    publication_manifest_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    workbench_projection_verified: bool = False
    source_counts: dict[str, int]
    provider_calls: int = Field(ge=0, le=9)
    limitations: tuple[str, ...]
    candidate_registered: bool = False
    production_admitted: bool = False


@dataclass(frozen=True)
class GoldenSliceConfig:
    riot_id: str
    routing_region: str
    queue: int = 420
    count: int = 5
    position: str = "mid"
    run_id: str = ""
    with_provider: bool = False


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_json(value: object) -> str:
    return _digest_bytes(
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    )


def _implementation_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True, timeout=10
    )
    sha = result.stdout.strip()
    if not _SHA.fullmatch(sha):
        raise RuntimeError("implementation_sha_invalid")
    return sha


def _assert_clean_tree() -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.stdout.strip():
        raise RuntimeError("real_golden_slice_requires_clean_committed_tree")


def preflight(config: GoldenSliceConfig) -> GoldenSlicePreflight:
    """Validate all bounds without reading secrets or touching the network."""

    if config.routing_region not in _REGIONS:
        raise ValueError("routing_region_invalid")
    if config.position not in _POSITIONS:
        raise ValueError("position_invalid")
    if not isinstance(config.riot_id, str) or config.riot_id.count("#") != 1:
        raise ValueError("riot_id_invalid")
    game_name, tag = (part.strip() for part in config.riot_id.split("#", 1))
    if not game_name or not tag or len(game_name) > 64 or len(tag) > 32:
        raise ValueError("riot_id_invalid")
    if not config.run_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,95}", config.run_id):
        raise ValueError("run_id_invalid")
    if not 1 <= config.count <= 5:
        raise ValueError("count_invalid")
    if config.queue != 420:
        raise ValueError("queue_not_admitted")
    # Account + IDs + detail + timeline for five matches; no fallback is
    # permitted after the identity is frozen.
    max_riot_calls = 2 + config.count * 2
    return GoldenSlicePreflight(
        run_id=config.run_id,
        riot_id=f"{game_name}#{tag}",
        routing_region=config.routing_region,
        queue=config.queue,
        count=config.count,
        position=config.position,
        max_riot_calls=max_riot_calls,
        max_ddragon_requests=5,
        max_opgg_tool_calls=1,
        provider_enabled=config.with_provider,
        network_allowed=False,
    )


def _ddragon_snapshot(service: DataDragonService, retrieved_at: datetime):
    payload = {
        "version": service.version,
        "language": service.language,
        "champions": service.champions,
        "items": service.items,
        "summoner_spells": service.summoner_spells,
        "runes": service.runes,
    }
    return data_dragon_snapshot_from_identity(
        version=service.version,
        language=service.language,
        catalog_digest=_digest_json(payload),
        retrieved_at=retrieved_at,
    )


def _official_patch(*, patch: str, retrieved_at: datetime) -> OfficialPatchEvidence | None:
    """Read one Riot-hosted patch/version identity and retain only its digest."""

    major, minor = patch.split(".", 1)
    url = f"https://www.leagueoflegends.com/en-us/news/game-updates/patch-{major}-{minor}-notes/"
    try:
        response = requests.get(url, timeout=20, headers={"Accept": "text/html"})
        if response.status_code == 404:
            # The patch-note page may not be published in the current locale
            # yet.  Riot's official version feed is still a separate,
            # immutable update identity and is sufficient for a bounded patch
            # fact (without pretending to have note text).
            url = "https://ddragon.leagueoflegends.com/api/versions.json"
            response = requests.get(url, timeout=20, headers={"Accept": "application/json"})
        response.raise_for_status()
        body = response.content
    except requests.RequestException:
        return None
    return OfficialPatchEvidence(
        patch_version=f"{major}.{minor}",
        update_id=f"riot-version-{major}-{minor}",
        published_at=retrieved_at,
        retrieved_at=retrieved_at,
        expires_at=None,
        source_digest=_digest_bytes(body),
    )


def _fetch_opgg_evidence(*, position: str, top_n: int) -> MetaEvidence:
    """Fetch exactly one typed OP.GG lane-meta snapshot."""

    from app.mcp.client import McpClientSession
    from app.mcp.models import McpImplementation
    from app.mcp.transport import StreamableHttpMcpTransport
    from app.meta.opgg import (
        OPGG_LANE_META_LOCAL_TOOL,
        OPGG_LANE_META_REMOTE_TOOL,
        OPGGLaneMetaAdapter,
    )
    from app.tools.models import CachePolicy, RetryPolicy, ToolPolicy
    from app.tools.registry import ToolRegistry
    from app.tools.runtime import ToolRuntime

    transport = StreamableHttpMcpTransport("https://mcp-api.op.gg/mcp")
    session = McpClientSession(
        transport,
        client_info=McpImplementation(name="riftcoach", version="0.1.0"),
        supported_protocol_versions=frozenset({"2025-06-18"}),
        allowed_tools=frozenset({OPGG_LANE_META_REMOTE_TOOL}),
    )
    try:
        session.initialize(timeout_s=15)
        catalog = session.discover(timeout_s=15)
        registry = ToolRegistry()
        registry.register(
            session.to_tool_definition(
                OPGG_LANE_META_REMOTE_TOOL,
                local_name=OPGG_LANE_META_LOCAL_TOOL,
                description="Fetch one bounded OP.GG lane-meta snapshot.",
                policy=ToolPolicy(timeout_s=15, retry=RetryPolicy(max_attempts=1), cache=CachePolicy(ttl_s=0)),
            )
        )
        evidence = OPGGLaneMetaAdapter(session=session, runtime=ToolRuntime(registry)).fetch(
            position=position, top_n=top_n, timeout_s=15
        )
        if catalog.get(OPGG_LANE_META_REMOTE_TOOL) is None:
            raise ValueError("opgg_tool_disappeared")
        return evidence
    finally:
        session.close()


def _training_plan(summary: Mapping[str, Any], *, disposition: str) -> tuple[str, ...]:
    recent = summary["recent_summary"]
    averages = recent["averages"]
    plan: list[str] = []
    if averages.get("deaths_before_15", 0) >= 1:
        plan.append("前15分钟先练安全换血与回城节奏：每局记录第一次阵亡前的视野和兵线状态。")
    if averages.get("cs_per_min", 0) < 7.0:
        plan.append("把补刀作为第一训练指标：前10分钟目标稳定达到每分钟7刀以上。")
    if averages.get("vision_score", 0) < 20:
        plan.append("每次推线后补一个河道/入口眼，并在下一次回城前复盘眼位价值。")
    if not plan:
        plan.append("保持当前基本盘，下一周把胜负局差异最大的指标做成单一训练目标。")
    if disposition != "complete":
        plan.append("证据存在缺口时只把结论当作当前样本的训练建议，不升级为版本强结论。")
    return tuple(plan[:5])


def run_golden_slice(
    config: GoldenSliceConfig,
    *,
    environ: Mapping[str, str],
    opgg_fetcher=None,
) -> GoldenSliceReceipt:
    """Execute one bounded real observation; never writes raw source bodies."""

    gate = preflight(config)
    _assert_clean_tree()
    started = datetime.now(timezone.utc)
    riot_key = environ.get("RIOT_API_KEY", "")
    if not riot_key.strip():
        raise RuntimeError("riot_key_missing")
    client = RiotClient(api_key=riot_key, region=config.routing_region)
    ddragon = DataDragonService(language="zh_CN", cache_dir=str(ROOT / "data/static/ddragon"))
    summary = build_player_summary(
        client=client,
        ddragon=ddragon,
        game_name=config.riot_id.rpartition("#")[0],
        tag_line=config.riot_id.rpartition("#")[2],
        count=config.count,
        queue=config.queue,
        min_duration_seconds=300,
    )
    observed_at = datetime.now(timezone.utc)
    patch = _official_patch(
        patch=".".join(str(summary["matches"][0]["game_version"]).split(".")[:2]),
        retrieved_at=observed_at,
    )
    snapshot = _ddragon_snapshot(ddragon, observed_at)
    meta: tuple[MetaEvidence, ...] = ()
    opgg_error = None
    position = config.position
    if not position:
        position = "mid"
    if opgg_fetcher is None:
        opgg_fetcher = _fetch_opgg_evidence
    try:
        fetched = opgg_fetcher(position=position, top_n=10)
        # Keep compatibility with the older validation helper, which returns
        # (initialized, catalog, descriptor, evidence), while the golden
        # slice helper returns the typed evidence directly.
        opgg = fetched[-1] if isinstance(fetched, tuple) else fetched
    except Exception as error:
        opgg_error = getattr(error, "code", "opgg_fetch_failed")
        opgg = None
    if isinstance(opgg, MetaEvidence):
        meta = (opgg,)
    # All source snapshots must be no later than the frozen fusion clock.  We
    # deliberately take that clock after the last external source returns.
    checked_now = datetime.now(timezone.utc)
    projection = summary_to_evidence(
        summary,
        routing_region=config.routing_region,
        now=checked_now,
        observed_at=observed_at,
        data_dragon=snapshot,
        official_patch=patch,
        meta_evidence=meta,
    )
    ui_projection = EvidencePublicProjectionResponse.model_validate(
        projection.bundle.to_public_projection()
    ).model_dump(mode="json")
    coach_report_digest = None
    provider_calls = 0
    coach_runtime_status = None
    coach_publication_status = None
    coach_terminal_reason = None
    publication_manifest_digest = None
    workbench_projection_verified = False
    if config.with_provider:
        settings = load_zhipu_settings(environ)
        # Coach 1.2.0 is an explicitly unadmitted candidate seam.  Bind its
        # candidate-only high-thinking profile directly; the normal provider
        # resolver's product runtime profile is intentionally not attached.
        from openai import OpenAI
        from app.providers.zhipu import ZhipuProvider
        from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE

        provider = ZhipuProvider.from_candidate_profile(
            client=OpenAI(
                api_key=settings.api_key,
                base_url=settings.base_url,
                timeout=settings.default_timeout_s,
                max_retries=0,
            ),
            model=settings.model,
            profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE,
        )
        # The provider execution seam is intentionally optional here; a
        # provider failure must not erase the valid evidence/training slice.
        from app.product.coach_composition import build_coach_application

        class _StaticSummary:
            def build(self, **_: Any) -> dict:
                return json.loads(json.dumps(summary))

            def build_by_puuid(self, **_: Any) -> dict:
                return json.loads(json.dumps(summary))

        from app.rag.hybrid import LocalHybridKnowledgeProvider

        base_knowledge = LocalHybridKnowledgeProvider.from_directory(ROOT / "data/rag_docs")

        class _CappedKnowledge:
            provider_name = "golden-slice-capped-local-hybrid"

            def search(self, query):
                result = base_knowledge.search(query)
                # Keep attribution/citation metadata while bounding parent
                # prose carried into the one real Coach context.
                hits = tuple(
                    replace(
                        hit,
                        content=hit.content[:1200],
                        matched_content=(hit.matched_content or "")[:800] or None,
                    )
                    for hit in result.hits[:3]
                )
                return replace(result, hits=hits)

        publication_sources = EvidencePublicationSources(
            now=checked_now,
            observed_at=observed_at,
            data_dragon=snapshot,
            official_patch=patch,
            meta_evidence=meta,
        )
        publication_store = FileEvidencePublicationStore(ROOT / "data/runs/golden_slice")
        from uuid import NAMESPACE_URL, uuid5
        publication_context = EvidencePublicationContext(
            owner_id="golden-slice",
            task_id=uuid5(NAMESPACE_URL, "riftcoach:" + config.run_id),
            run_id=config.run_id,
            request_fingerprint=_digest_json({"riot_id": config.riot_id, "region": config.routing_region, "count": config.count, "queue": config.queue}),
        )
        application = build_coach_application(
            summary_builder=_StaticSummary(),
            provider=provider,
            knowledge_provider=_CappedKnowledge(),
            runs_root=ROOT / "data/runs/golden_slice",
            publication_sources=publication_sources,
            publication_writer=publication_store,
            report_renderer=lambda value: (
                render_deterministic_report(value)
                + "\n\nEvidence snapshot digest: " + projection.summary_digest
                + "\nEvidence bundle digest: " + projection.bundle.digest
            ),
        )
        from app.product.recent_review import RecentReviewProductRequest

        try:
            result = application.review(RecentReviewProductRequest(
                riot_id=config.riot_id, routing_region=config.routing_region,
                count=config.count, queue=config.queue, focus="overall",
            ), run_id=config.run_id, publication_context=publication_context)
            report = getattr(result.output, "report", None)
            if isinstance(report, str) and report.strip():
                coach_report_digest = _digest_bytes(report.encode("utf-8"))
            coach_runtime_status = result.runtime_status.value
            coach_publication_status = result.publication_status.value if result.publication_status else None
            coach_terminal_reason = result.terminal_reason
            trace_reference = result.trace_reference
            if result.evidence_projection is not None:
                workbench_projection_verified = EvidencePublicProjectionResponse.model_validate(
                    result.evidence_projection.bundle.to_public_projection()
                ).bundle_digest == projection.bundle.digest
                manifest_path = ROOT / "data/runs/golden_slice" / config.run_id / FileEvidencePublicationStore.filename
                if manifest_path.is_file():
                    publication_manifest_digest = _digest_bytes(manifest_path.read_bytes())
        except Exception as error:
            # A provider/runtime failure is still a valid bounded observation;
            # return a degraded receipt instead of turning it into a false
            # success or losing its safe terminal category.
            code = getattr(error, "code", None)
            coach_terminal_reason = code if isinstance(code, str) else "coach_execution_failed"
            trace_reference = None
        provider_calls = 0
        if trace_reference is not None:
            trace_path = ROOT / "data/runs/golden_slice" / config.run_id / trace_reference.run_id / trace_reference.relative_path
            try:
                trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
                usage = trace_payload.get("usage", {})
                provider_calls = int(usage.get("provider_calls_attempted", 0))
            except (OSError, ValueError, TypeError):
                provider_calls = 1
    outcome = "passed" if projection.bundle.disposition.value == "complete" and coach_report_digest else "degraded"
    limitations = [
        "body_free_receipt_only", "candidate_not_registered",
        "production_default_unchanged", "training_plan_is_bounded_observation",
    ]
    if opgg_error:
        limitations.append(opgg_error)
    if config.with_provider and coach_report_digest is None:
        limitations.append("coach_report_unavailable")
    return GoldenSliceReceipt(
        run_id=config.run_id,
        implementation_sha=_implementation_sha(),
        result=outcome,
        summary_digest=_digest_json(summary),
        summary_matches_analyzed=summary["recent_summary"]["games_analyzed"],
        evidence_bundle_digest=projection.bundle.digest,
        evidence_projection=ui_projection,
        training_plan=_training_plan(summary, disposition=projection.bundle.disposition.value),
        training_evidence_digest=projection.bundle.digest,
        coach_report_digest=coach_report_digest,
        coach_runtime_status=coach_runtime_status,
        coach_publication_status=coach_publication_status,
        coach_terminal_reason=coach_terminal_reason,
        publication_manifest_digest=publication_manifest_digest,
        workbench_projection_verified=workbench_projection_verified,
        source_counts={
            "riot_official": len(projection.bundle.riot_matches),
            "data_dragon": int(projection.bundle.data_dragon is not None),
            "riot_patch": int(projection.bundle.official_patch is not None),
            "opgg": len(projection.bundle.meta_evidence),
        },
        provider_calls=provider_calls,
        limitations=tuple(limitations),
    )


__all__ = [
    "GoldenSliceConfig",
    "GoldenSlicePreflight",
    "GoldenSliceReceipt",
    "preflight",
    "run_golden_slice",
]
