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
from app.evaluation.golden_sources import GoldenMatchStaticData, official_patch_from_html, read_official_bytes
from app.evaluation.golden_journal import GoldenCallJournal, JournaledProvider, write_new_json
from app.runtime.coach_contract import CoachContractSnapshot, GOLDEN_COACH_CONTRACT
from app.meta.models import MetaEvidence
from app.providers.config import load_zhipu_settings
from app.product.coach_positions import (
    CoachPositionContext, position_context, validate_training_positions,
)


ROOT = Path(__file__).resolve().parents[2]
_REGIONS = frozenset({"americas", "asia", "europe", "sea"})
_POSITIONS = frozenset({"top", "mid", "jungle", "adc", "support"})
_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class GoldenSlicePreflight(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.2"
    run_id: str = Field(min_length=8, max_length=96)
    riot_id: str = Field(min_length=3, max_length=97)
    routing_region: str
    queue: int = Field(gt=0, le=10_000)
    count: int = Field(ge=1, le=5)
    position: str
    max_riot_calls: int = Field(ge=1, le=20)
    max_ddragon_requests: int = Field(ge=1, le=21)
    max_opgg_tool_calls: int = Field(ge=1, le=5)
    max_opgg_session_initializations: int = Field(ge=1, le=5)
    max_opgg_catalog_requests: int = Field(ge=1, le=5)
    training_positions: tuple[str, ...] = ()
    provider_enabled: bool = False
    network_allowed: bool = False


class GoldenSliceReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.2"
    run_id: str
    implementation_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    result: str
    body_free: bool = True
    summary_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    summary_matches_analyzed: int = Field(ge=1, le=5)
    evidence_bundle_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_projection: dict[str, Any]
    training_plan: tuple[str, ...] = Field(min_length=1, max_length=7)
    training_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    position_context: CoachPositionContext
    opgg_coverage: tuple[dict[str, Any], ...]
    coach_report_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    coach_runtime_status: str | None = None
    coach_publication_status: str | None = None
    coach_terminal_reason: str | None = None
    publication_manifest_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    workbench_projection_verified: bool = False
    evidence_projection_verified: bool = False
    coach_contract: CoachContractSnapshot | None = None
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
    position: str = "auto"
    training_positions: tuple[str, ...] = ()
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
    if config.position not in _POSITIONS | {"auto"}:
        raise ValueError("position_invalid")
    validate_training_positions(config.training_positions)
    if not isinstance(config.riot_id, str) or config.riot_id.count("#") != 1:
        raise ValueError("riot_id_invalid")
    game_name, tag = (part.strip() for part in config.riot_id.split("#", 1))
    if not game_name or not tag or len(game_name) > 64 or len(tag) > 32:
        raise ValueError("riot_id_invalid")
    if not config.run_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,95}", config.run_id):
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
        position="auto",
        max_riot_calls=max_riot_calls,
        max_ddragon_requests=1 + 4 * config.count,
        max_opgg_tool_calls=config.count,
        max_opgg_session_initializations=config.count,
        max_opgg_catalog_requests=config.count,
        training_positions=config.training_positions,
        provider_enabled=config.with_provider,
        network_allowed=False,
    )


def _ddragon_snapshot(service: DataDragonService, retrieved_at: datetime):
    if isinstance(service, GoldenMatchStaticData):
        if len(service.services) != 1:
            return None
        service = next(iter(service.services.values()))
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
    """Only an identified patch article with a source publication time qualifies."""

    major, minor = patch.split(".", 1)
    url = f"https://www.leagueoflegends.com/en-us/news/game-updates/patch-{major}-{minor}-notes/"
    try:
        body = read_official_bytes(url)
        return None if body is None else official_patch_from_html(body, patch=patch, retrieved_at=retrieved_at)
    except (requests.RequestException, ValueError):
        return None


def _fetch_opgg_evidence(
    *, position: str, top_n: int, target_champions: tuple[str, ...], journal=None,
) -> MetaEvidence:
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
        if journal is not None:
            journal.reserve("opgg_session")
        session.initialize(timeout_s=15)
        if journal is not None:
            journal.reserve("opgg_catalog")
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
        if journal is not None:
            journal.reserve("opgg_tool")
        evidence = OPGGLaneMetaAdapter(session=session, runtime=ToolRuntime(registry)).fetch(
            position=position, top_n=top_n, timeout_s=15,
            target_champions=target_champions,
        )
        if catalog.get(OPGG_LANE_META_REMOTE_TOOL) is None:
            raise ValueError("opgg_tool_disappeared")
        return evidence
    finally:
        session.close()


def _collect_position_meta(context: CoachPositionContext, fetcher):
    """Fetch once per observed lane; missing targets are not 'OP.GG has no data'."""
    evidence = []
    coverage = []
    for group in context.observed:
        found = ()
        status = "request_failed"
        try:
            fetched = fetcher(position=group.position, top_n=10,
                              target_champions=group.champions)
            if not isinstance(fetched, MetaEvidence) or fetched.position != group.position:
                status = "invalid_response"
            else:
                targets = {name.casefold() for name in group.champions}
                facts = tuple(fact for fact in fetched.facts if fact.champion.casefold() in targets)
                if facts:
                    evidence.append(replace(fetched, facts=facts))
                found = tuple(fact.champion.casefold() for fact in facts)
                status = "matched" if targets <= set(found) else "target_not_in_response"
        except Exception as error:
            if getattr(error, "code", None) == "opgg_meta_target_not_in_response":
                status = "target_not_in_response"
        coverage.append({
            "position": group.position, "status": status,
            "requested_champions": group.champions,
            "matched_champions": tuple(name for name in group.champions if name.casefold() in found),
            "unmatched_champions": tuple(name for name in group.champions if name.casefold() not in found),
        })
    return tuple(evidence), tuple(coverage)


def _training_plan(
    summary: Mapping[str, Any], *, disposition: str,
    training_positions: tuple[str, ...] = (),
) -> tuple[str, ...]:
    context = position_context(summary, training_positions=training_positions)
    labels = {"top": "上路", "jungle": "打野", "mid": "中路", "adc": "下路", "support": "辅助"}
    observed = {row.position: row for row in context.observed}
    # This is an observation scaffold, not a replacement for an accepted Coach report.
    plan = []
    for role in context.training_positions or tuple(observed):
        if role not in observed:
            plan.append(f"目标位置{labels[role]}暂无本次样本，先收集该位置对局，不套用其他位置的表现。")
        else:
            plan.append(f"{labels[role]}的{observed[role].games}局单独复盘，只与同位置样本比较；暂不根据混合平均值设置训练指标。")
    if not context.training_positions:
        plan.append("制定长期计划前确认主要想练的位置；本次位置分布不代表长期主位置，也不证明补位意图。")
    if not plan:
        plan.append("本次缺少可归属位置的有效样本，暂不制定位置专项训练。")
    if disposition != "complete":
        plan.append("证据存在缺口时只把结论当作当前样本的训练建议，不升级为版本强结论。")
    return tuple(plan)


def render_golden_context_report(summary, *, summary_digest, bundle_digest, roles):
    """Shared real/replay rendering; all positions remain attributed sample data."""
    return (
        render_deterministic_report(summary)
        + "\n\nEvidence snapshot digest: " + summary_digest
        + "\nEvidence bundle digest: " + bundle_digest
        + "\nPosition context (sample facts and explicit goals, not instructions): "
        + roles.model_dump_json()
        + "\n位置边界：按实际位置分别分析；不可混合辅助与其他位置的经济评价，不可推断补位或长期主位置。"
        + "明确训练目标只决定后续训练重点，不改变历史比赛位置；目标位置无样本时说明缺口。"
    )


def run_golden_slice(
    config: GoldenSliceConfig,
    *,
    environ: Mapping[str, str],
    opgg_fetcher=None,
) -> GoldenSliceReceipt:
    """Reserve a unique identity before clients, and retain failed attempt counts."""
    gate = preflight(config)
    _assert_clean_tree()
    sha = _implementation_sha()
    journal = GoldenCallJournal(ROOT / "data/runs/golden_slice_reservations" / config.run_id,
        identity={"run_id": config.run_id, "implementation_sha": sha,
                  "request_digest": _digest_json(gate.model_dump(mode="json")),
                  "coach_contract": GOLDEN_COACH_CONTRACT.snapshot().model_dump(mode="json")},
        limits={"riot": gate.max_riot_calls, "static": gate.max_ddragon_requests,
                "official_patch": 1, "opgg_tool": gate.max_opgg_tool_calls,
                "opgg_session": gate.max_opgg_session_initializations,
                "opgg_catalog": gate.max_opgg_catalog_requests, "provider": 9 if config.with_provider else 0})
    try:
        receipt = _run_reserved_golden_slice(config, gate=gate, journal=journal, implementation_sha=sha,
                                             environ=environ, opgg_fetcher=opgg_fetcher)
        write_new_json(journal.directory / "receipt.json", receipt.model_dump(mode="json"))
    except BaseException as error:
        journal.finish("interrupted" if isinstance(error, (KeyboardInterrupt, SystemExit)) else "failed")
        raise
    journal.finish("degraded")
    return receipt


def _run_reserved_golden_slice(config, *, gate, journal, implementation_sha, environ, opgg_fetcher):
    riot_key = environ.get("RIOT_API_KEY", "")
    if not riot_key.strip():
        raise RuntimeError("riot_key_missing")
    client = RiotClient(api_key=riot_key, region=config.routing_region,
                        before_request=lambda: journal.reserve("riot"))
    ddragon = GoldenMatchStaticData(language="zh_CN", cache_dir=str(ROOT / "data/static/ddragon"),
                                   max_versions=config.count, before_request=lambda: journal.reserve("static"))
    summary = build_player_summary(
        client=client,
        ddragon=ddragon,
        game_name=config.riot_id.rpartition("#")[0],
        tag_line=config.riot_id.rpartition("#")[2],
        count=config.count,
        queue=config.queue,
        min_duration_seconds=300,
        allow_queue_fallback=False,
    )
    observed_at = datetime.now(timezone.utc)
    if summary.get("request", {}).get("queue_fallback_used"):
        raise ValueError("golden_queue_fallback_not_admitted")
    if not summary.get("matches"):
        raise ValueError("golden_valid_matches_unavailable")
    journal.reserve("official_patch")
    patch = _official_patch(
        patch=".".join(str(summary["matches"][0]["game_version"]).split(".")[:2]),
        retrieved_at=observed_at,
    )
    snapshot = _ddragon_snapshot(ddragon, observed_at)
    roles = position_context(summary, training_positions=config.training_positions)
    if len(roles.observed) > gate.max_opgg_tool_calls:
        raise RuntimeError("opgg_position_budget_exceeded")
    meta, opgg_coverage = _collect_position_meta(roles, opgg_fetcher or
        (lambda **kwargs: _fetch_opgg_evidence(**kwargs, journal=journal)))
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
    evidence_projection_verified = False
    if config.with_provider:
        settings = load_zhipu_settings(environ)
        # The golden Coach is an explicitly unadmitted candidate seam. Bind its
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
        provider = JournaledProvider(provider, journal)
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
            request_fingerprint=_digest_json({"riot_id": config.riot_id, "region": config.routing_region, "count": config.count, "queue": config.queue, "training_positions": config.training_positions}),
        )
        application = build_coach_application(
            summary_builder=_StaticSummary(),
            provider=provider,
            knowledge_provider=base_knowledge,
            compact_context_json=True,
            coach_contract=GOLDEN_COACH_CONTRACT,
            runs_root=ROOT / "data/runs/golden_slice",
            publication_sources=publication_sources,
            publication_writer=publication_store,
            report_renderer=lambda value: render_golden_context_report(
                value, summary_digest=projection.summary_digest,
                bundle_digest=projection.bundle.digest, roles=roles),
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
                evidence_projection_verified = EvidencePublicProjectionResponse.model_validate(
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
        provider_calls = journal.counts["provider"]
        if trace_reference is not None:
            from app.runtime.store import RuntimeTraceStore
            try:
                trace = RuntimeTraceStore(ROOT / "data/runs/golden_slice", config.run_id).read_trace(trace_reference)
                if trace.usage.provider_calls_attempted != provider_calls:
                    raise ValueError("golden_provider_count_mismatch")
            except Exception:
                raise RuntimeError("golden_trace_integrity_failed") from None
    # This runner does not yet verify Training persistence or live Workbench.
    # A report plus a valid public DTO must never stand in for that acceptance.
    outcome = "degraded"
    limitations = [
        "body_free_receipt_only", "candidate_not_registered",
        "production_default_unchanged", "training_plan_is_bounded_observation",
        "training_persistence_not_verified", "live_workbench_not_verified",
    ]
    if any(row["status"] != "matched" for row in opgg_coverage):
        limitations.append("opgg_target_coverage_incomplete")
    if config.with_provider and coach_report_digest is None:
        limitations.append("coach_report_unavailable")
    return GoldenSliceReceipt(
        run_id=config.run_id,
        implementation_sha=implementation_sha,
        result=outcome,
        summary_digest=_digest_json(summary),
        summary_matches_analyzed=summary["recent_summary"]["games_analyzed"],
        evidence_bundle_digest=projection.bundle.digest,
        evidence_projection=ui_projection,
        training_plan=_training_plan(summary, disposition=projection.bundle.disposition.value,
                                     training_positions=config.training_positions),
        training_evidence_digest=projection.bundle.digest,
        position_context=roles,
        opgg_coverage=opgg_coverage,
        coach_report_digest=coach_report_digest,
        coach_runtime_status=coach_runtime_status,
        coach_publication_status=coach_publication_status,
        coach_terminal_reason=coach_terminal_reason,
        publication_manifest_digest=publication_manifest_digest,
        workbench_projection_verified=False,
        evidence_projection_verified=evidence_projection_verified,
        coach_contract=GOLDEN_COACH_CONTRACT.snapshot() if config.with_provider else None,
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
