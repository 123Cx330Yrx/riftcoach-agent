"""Fresh product-runtime inputs and reproducible, network-free commitments.

The Dataset contains acceptance criteria, never a model prompt or expected
answer. Only the separate synthetic inputs enter the product compiler.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from uuid import UUID

from app.agent.memory_context import MemoryAwareContextBuilder
from app.evaluation.domain_e2e import (
    ContractSnapshot, DomainCaseRequirements, DomainEvaluationCase,
    DomainEvaluationDataset,
)
from app.lol.match_analyzer import aggregate_recent_matches
from app.lol.report_renderer import render_deterministic_report
from app.memory.context_models import (
    MemoryContextBinding, MemoryContextRecord, MemoryContextSnapshot, MemoryContextRecordKind,
)
from app.players.models import RelationshipRole
from app.product.recent_review import RecentReviewProductRequest, RecentReviewRuntimeRequestCompiler
from app.runtime.coach_context import CoachContextBuilder
from app.runtime.coach_contract import COACH_CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from app.skills.execution import SkillExecutionBoundary


ASSET_PATH = Path("examples/evaluation/coach_product_rq246_v1")
DATASET_ID = "coach-product-rq246-v1"
FIXED_TIME = datetime(2026, 9, 6, tzinfo=timezone.utc)


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(json_bytes(value)).hexdigest()


def composition(root: Path) -> RuntimeCompositionRoot:
    assets = root / "examples/runtime_profiles/flash_v2"
    return RuntimeCompositionRoot.from_directories(
        skills_root=assets / "skills", prompt_programs_root=assets / "prompt_programs",
        coach_contract=COACH_CONTRACT,
    )


class FrozenMemory:
    """Synthetic owner-scoped repository; manifest hashes contain no message body."""

    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.manifest_hashes = []

    def load(self, binding):
        if binding != self.snapshot.binding:
            raise ValueError("acceptance_memory_binding_drift")
        return self.snapshot

    def write(self, manifest):
        value = digest(manifest.model_dump(mode="json"))
        self.manifest_hashes.append(value)
        return value


def context_builder(case):
    memory = case["memory"]
    if memory is None:
        return CoachContextBuilder(), None, None
    binding = MemoryContextBinding(
        run_id=case["case_id"], owner_id="synthetic-coach246-owner",
        conversation_id=UUID(int=24601), relationship_id=UUID(int=24602),
        player_subject_id=UUID(int=24603), relationship_role=RelationshipRole.SELF,
    )
    record = MemoryContextRecord(
        kind=MemoryContextRecordKind.MESSAGE, record_id=UUID(int=24604), version=1, content=memory,
        content_sha256=hashlib.sha256(memory.encode()).hexdigest(),
        priority=650, stable_order="message:0001", relationship_role=RelationshipRole.SELF,
    )
    repository = FrozenMemory(MemoryContextSnapshot(binding=binding, records=(record,)))
    builder = MemoryAwareContextBuilder(
        delegate=CoachContextBuilder(), repository=repository, manifest_store=repository,
        clock=lambda: FIXED_TIME,
    )
    return builder, binding, repository


def summary_from_inputs(inputs):
    rows = []
    for index, value in enumerate(inputs["matches"]):
        rows.append({
            **value, "match_id": f"SYNTHETIC_COACH246_{index + 1}",
            "champion_id": 900246, "champion_name": "合成测试英雄",
            "champion_name_en": "Synthetic246", "role": "MIDDLE",
            "game_duration_seconds": 1800, "timeline_status": "available",
            "included_in_aggregate": True,
            "kda": round((value["kills"] + value["assists"]) / max(1, value["deaths"]), 2),
            "kill_participation": 0.52, "damage_share": 0.24, "gold_share": 0.22,
            "death_times": ([f"{5 + i * 4:02d}:20" for i in range(value["deaths_before_15"])]
                            + [f"{17 + i * 2:02d}:10" for i in range(value["deaths"] - value["deaths_before_15"])]),
            "items": [], "item_names": [], "item_purchases": [],
        })
    game_name, tag_line = inputs["player"].split("#")
    return {
        "schema_version": "1.0",
        "metadata": {"generated_at_utc": FIXED_TIME.isoformat(), "source": inputs["source"],
                     "matches_requested": 5, "matches_received": 5, "matches_analyzed": 5},
        "player": {"riot_id": inputs["player"], "game_name": game_name, "tag_line": tag_line,
                   "puuid_prefix": "synthetic246"},
        "request": {"count": 5, "queue": 420, "region": "asia"},
        "recent_summary": aggregate_recent_matches(rows), "matches": rows,
        "failed_matches": [], "excluded_matches": [],
    }


def compile_case(root, inputs, case):
    compiler = RecentReviewRuntimeRequestCompiler(root.skill_catalog, coach_contract=COACH_CONTRACT)
    builder, binding, memory = context_builder(case)
    summary = summary_from_inputs(inputs)
    request = compiler.compile(
        RecentReviewProductRequest(riot_id=inputs["player"], routing_region="asia", count=5, focus=case["focus"]),
        player_summary=summary, deterministic_report=(
            "> 独立验收：以下比赛、英雄和账号均为合成数据；本次未调用 Riot API 或 Data Dragon，"
            "不能把模板里的数据渠道说明当成本次真实联网来源。\n\n" + render_deterministic_report(summary)),
        run_id=case["case_id"], memory_context_binding=binding,
    )
    return request, builder, memory


@dataclass(frozen=True)
class AcceptanceAssets:
    inputs: dict
    manifest: dict
    dataset: DomainEvaluationDataset

    @property
    def sha256(self):
        return digest(self.manifest)


def build_assets(project_root: Path) -> AcceptanceAssets:
    """Rebuild all commitments. Does not read credentials or construct a Provider."""
    inputs = json.loads((project_root / ASSET_PATH / "inputs.json").read_text(encoding="utf-8"))
    if (inputs["fixture_id"] != "coach-product-rq246-inputs-v1"
            or len(inputs["matches"]) != 5 or len(inputs["cases"]) != 4):
        raise ValueError("acceptance_input_identity_mismatch")
    root = composition(project_root)
    contexts = []
    for case in inputs["cases"]:
        request, builder, memory = compile_case(root, inputs, case)
        execution = SkillExecutionBoundary(root.skill_catalog).validate(request.execution_request)
        context = builder.build(execution, max_context_tokens=request.policy.max_context_tokens,
                                **({"memory_context_binding": request.memory_context_binding} if memory else {}))
        contexts.append({
            "case_id": case["case_id"], "request_sha256": digest(request.model_dump(mode="json")),
            "context_sha256": digest(asdict(context)), "estimated_context_units": context.estimated_tokens,
            "memory_manifest_sha256s": memory.manifest_hashes if memory else [],
            "marker_sha256s": [hashlib.sha256(marker.encode()).hexdigest() for marker in case["forbidden_output_markers"]],
        })
    corpus = {
        path.relative_to(project_root).as_posix(): hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()
        for path in sorted((project_root / "data/rag_docs").rglob("*")) if path.is_file()
    }
    if not corpus:
        raise ValueError("acceptance_corpus_empty")
    program = root.prompt_program_resolver.resolve("recent-form-review", "0.3.0")
    context_snapshot = {"contexts": contexts, "corpus": corpus,
                        "coach_contract": COACH_CONTRACT.snapshot().model_dump(mode="json"),
                        "program_sha256": program.manifest.program_sha256}
    contract = ContractSnapshot(
        skill_name="recent-form-review", skill_version="0.3.0", context_contract="context-builder-v1@1.0.0",
        evaluation_contract="coach_evaluation@1.1.0", prompt_context_snapshot_id="coach246-context-v1",
        prompt_context_snapshot_sha256=digest(context_snapshot),
    )
    requirements = DomainCaseRequirements(
        minimum_normalized_responses=3, expected_agent_status="completed", expected_agent_stop_reason="final_response",
        required_tool_names=("knowledge.search",), minimum_successful_tool_executions=1,
        minimum_evidence_sources=1, require_fact_check=True, require_citation_check=True,
        require_injection_check=True, require_validated_evaluation=True, minimum_evaluation_score=85,
        allowed_terminal_statuses=("published",), maximum_provider_calls=9, maximum_total_tokens=612864,
    )
    dataset = DomainEvaluationDataset(
        schema_version="1.2", dataset_id=DATASET_ID, dataset_version="1.0.0", role="held_out",
        calibration_excluded=True, created_at="2026-09-06", case_count=4, contract_snapshot=contract,
        contamination_notes=(), lifecycle_policy="Single fresh product observation; never tune on outcomes or overwrite receipts.",
        cases=tuple(DomainEvaluationCase(
            case_id=case["case_id"], category="memory_injection" if case["memory"] else case["focus"],
            expect_task_success=True, expected_primary_failure=None, requirements=requirements, contamination_sources=(),
        ) for case in inputs["cases"]),
    )
    manifest = {"schema_version": "1.0", "asset_id": DATASET_ID,
                "inputs_sha256": digest(inputs), "context_snapshot": context_snapshot,
                "dataset": dataset.model_dump(mode="json"),
                "budget": {"cases": 4, "maximum_calls": 36, "maximum_total_tokens": 2451456,
                           "per_case": COACH_CONTRACT.descriptor(), "protocol_calls_separate": 3}}
    return AcceptanceAssets(inputs, manifest, dataset)


def admit_assets(project_root: Path) -> AcceptanceAssets:
    rebuilt = build_assets(project_root)
    frozen = json.loads((project_root / ASSET_PATH / "manifest.json").read_text(encoding="utf-8"))
    if json_bytes(rebuilt.manifest) != json_bytes(frozen):
        raise ValueError("acceptance_asset_drift")
    return rebuilt
