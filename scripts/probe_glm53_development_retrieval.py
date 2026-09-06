"""One development review: autonomous GLM queries, no held-out or publication claim."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evaluation.glm53_bounded_revision_budget import (
    BoundedRevisionBudgetedProvider, BoundedRevisionBudgetState,
)
from app.agent.context import CANDIDATE_CONTEXT_SAFETY_POLICY_V1
from app.evaluation.prompt_context_identity import case_context_sha256
from app.evaluation.glm53_flash_candidate_profile import GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
from app.evaluation.provider_domain_experiment import DomainCaseExecutionPlan
from app.evaluation.provider_domain_plan import (
    DomainCaseContextCommitment, DomainCaseInput, DomainCaseInputPlanArtifact,
    DomainFixtureCommitment, LoadedDomainCaseInputPlan,
)
from app.evaluation.provider_domain_production import ProductionDomainCaseExecutor
from app.evaluation.glm53_guided_candidate import (
    GUIDANCE_ID, GUIDANCE_SHA256, build_guided_context_snapshot, require_guided_candidate,
)
from app.skills.review_executor import SkillReviewExecutionError
from app.rag.coaching_query import (
    COACHING_QUERY_GUIDANCE_V1, _TOPICS, _contains_alias, _normalize, _topic,
)
from app.rag.retriever import tokenize

CASE_ID = "development_autonomous_recent_review_01"
UTTERANCE = "请复盘我最近两局的状态，区分数据事实和可能原因，结合教练资料给出下一局可记录的调整建议。"
POLICY = GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
DEVELOPMENT_SCENARIOS = {
    "recent_review": (CASE_ID, UTTERANCE, "overall"),
    "survival_adjustment": (
        "development_autonomous_survival_adjustment_01",
        "请帮我复盘最近几局总是早早阵亡的情况，结合教练资料给我一个下一局可记录的生存调整。",
        "survival",
    ),
    "economy_adjustment": (
        "development_autonomous_economy_adjustment_01",
        "请帮我复盘最近补刀经济落后的情况，结合教练资料分析下一局可记录的经济调整。",
        "economy",
    ),
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def development_plan(root: Path, *, guided: bool = False, scenario: str = "recent_review") -> LoadedDomainCaseInputPlan:
    if scenario not in DEVELOPMENT_SCENARIOS:
        raise ValueError("unknown development scenario")
    case_id, utterance, focus = DEVELOPMENT_SCENARIOS[scenario]
    summary = root / "examples/fixtures/player_summary_demo.json"
    report = root / "examples/fixtures/deterministic_report_demo.md"
    artifact = DomainCaseInputPlanArtifact(
        plan_id="glm53-autonomous-retrieval-development", plan_version="1.0.0",
        dataset_id="demo-development-not-heldout", dataset_version="1.0.0",
        skill_name="recent-form-review", skill_version="0.2.0",
        player_summary=DomainFixtureCommitment(relative_path=summary.relative_to(root).as_posix(), sha256=digest(summary.read_bytes())),
        deterministic_report=DomainFixtureCommitment(relative_path=report.relative_to(root).as_posix(), sha256=digest(report.read_bytes())),
        sdk_max_retries=0, max_revisions=1, request_policy_id=POLICY.policy_id,
        request_policy_version=POLICY.version, quality_hardening=True, retrieval_hardening=True,
        case_count=1, cases=(DomainCaseInput(
            case_id=case_id, run_id=case_id, user_utterance=utterance,
            focus=focus, knowledge_mode="standard",
        ),),
    )
    if guided:
        provisional = LoadedDomainCaseInputPlan(
            artifact=artifact, player_summary_path=summary, deterministic_report_path=report,
            execution_plan=DomainCaseExecutionPlan(
                plan_id=artifact.plan_id, plan_version=artifact.plan_version,
                plan_sha256=digest(artifact.model_dump_json().encode()), case_ids=(case_id,),
            ),
        )
        snapshot = build_guided_context_snapshot_for_plan(provisional, root)
        artifact = DomainCaseInputPlanArtifact.model_validate({**artifact.model_dump(mode="json"),
            "schema_version": "1.1",
            "prompt_context_snapshot_id": snapshot.snapshot_id,
            "prompt_context_snapshot_sha256": snapshot.snapshot_sha256,
            "case_context_commitments": tuple(
                DomainCaseContextCommitment(case_id=row.case_id, context_sha256=case_context_sha256(row))
                for row in snapshot.case_contexts
            ),
        })
    return LoadedDomainCaseInputPlan(
        artifact=artifact, player_summary_path=summary, deterministic_report_path=report,
        execution_plan=DomainCaseExecutionPlan(
            plan_id=artifact.plan_id, plan_version=artifact.plan_version,
            plan_sha256=digest(artifact.model_dump_json().encode()), case_ids=(case_id,),
        ),
    )


def build_guided_context_snapshot_for_plan(plan: LoadedDomainCaseInputPlan, root: Path):
    """Build a provisional identity before sealing the schema 1.1 plan."""
    from app.evaluation.prompt_context_identity import build_prompt_context_snapshot_for_cases
    import json
    return build_prompt_context_snapshot_for_cases(
        skills_root=root / "skills",
        player_summary=json.loads(plan.player_summary_path.read_text(encoding="utf-8")),
        deterministic_report=plan.deterministic_report_path.read_text(encoding="utf-8"),
        cases=plan.artifact.cases,
        snapshot_id="glm53-guided-development-context-v1",
        evaluation_contract_version="1.1.0",
        policy_addendum="\n\n".join((CANDIDATE_CONTEXT_SAFETY_POLICY_V1, COACHING_QUERY_GUIDANCE_V1)),
    )


class QueryObserver:
    """Read-only projection; never repairs or replaces a model-selected query."""
    def __init__(self, provider, emit=lambda _event: None):
        self.provider_name, self.model_name = provider.provider_name, provider.model_name
        self.capabilities = provider.capabilities
        self.provider = provider
        self.emit = emit
        self.queries = []

    def chat(self, request):
        response = self.provider.chat(replace(request, timeout_s=min(request.timeout_s, 45.0)))
        for call in response.tool_calls:
            if call.name != "knowledge.search":
                continue
            query = call.arguments.get("query")
            if not isinstance(query, str):
                self.queries.append({"shape": "invalid_query_type"})
                continue
            normalized = _normalize(query)
            recognized = tuple(topic for topic, aliases, _terms in _TOPICS
                               if any(_contains_alias(normalized, alias) for alias in aliases))
            filters = call.arguments.get("filters", {})
            self.queries.append({
                "shape": "string", "topic": _topic(query)[0],
                "recognized_topics": recognized, "character_count": len(query),
                "term_count": len(set(tokenize(query))),
                "filter_names": sorted(key for key in filters if key in {"as_of", "position", "version"})
                    if isinstance(filters, dict) else [],
            })
        self.emit({"event": "provider_response", "query_count": len(self.queries)})
        return response


def observe(provider, *, root: Path, runs_root: Path, real: bool = False, emit=lambda _event: None,
            retrieval_guidance: str | None = None, scenario: str = "recent_review"):
    plan = development_plan(root, guided=retrieval_guidance is not None, scenario=scenario)
    if retrieval_guidance is not None:
        require_guided_candidate(project_root=root, input_plan=plan)
    state = BoundedRevisionBudgetState()
    case_id = plan.execution_plan.case_ids[0]
    state.register_case(case_id)
    budgeted = BoundedRevisionBudgetedProvider(
        provider=provider, state=state, case_id=case_id,
        case_max_tokens=205_000, domain_max_tokens=205_000,
    )
    observer = QueryObserver(budgeted, emit)
    executor = ProductionDomainCaseExecutor(
        project_root=root, input_plan=plan, runs_root=runs_root,
        request_policy=POLICY, quality_hardening=True, retrieval_hardening=True,
        retrieval_guidance=retrieval_guidance, max_revisions=1,
    )
    execution_error = None
    try:
        result = executor.execute(case_id=case_id, provider=observer)
    except SkillReviewExecutionError:
        # Retain bounded diagnostics even if terminal output projection fails.
        # Never persist exception text, prompts, drafts or model reasoning.
        result = None
        execution_error = "terminal_output_validation_failed"
    guidance_id = GUIDANCE_ID if retrieval_guidance is not None else None
    guidance_sha256 = GUIDANCE_SHA256 if retrieval_guidance is not None else None
    return {
        "schema_version": "1.0", "scope": "development_not_admission",
        "evidence_origin": "real_provider" if real else "offline_fake",
        "network_used": real and state.calls_used > 0,
        "candidate_registered": False, "production_admitted": False,
        "plan_sha256": plan.execution_plan.plan_sha256,
        "summary_sha256": plan.artifact.player_summary.sha256,
        "report_sha256": plan.artifact.deterministic_report.sha256,
        "request_policy_id": POLICY.policy_id, "max_calls": 9, "max_tokens": 205_000,
        "request_timeout_s": 45, "resources": state.snapshot(),
        "retrieval_guidance_id": guidance_id, "retrieval_guidance_sha256": guidance_sha256,
        "queries": observer.queries,
        "observation": result.model_dump(mode="json") if result is not None else None,
        "execution_error": execution_error,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-real-call", action="store_true")
    parser.add_argument("--implementation-sha", required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--retrieval-guidance", action="store_true")
    parser.add_argument("--scenario", choices=tuple(DEVELOPMENT_SCENARIOS), default="recent_review")
    args = parser.parse_args(argv)
    if not args.confirm_real_call:
        parser.error("real development observation requires --confirm-real-call")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=10).strip()
    if head != args.implementation_sha:
        raise ValueError("implementation must match HEAD")
    changed = subprocess.check_output(["git", "diff", "HEAD", "--name-only", "--", "app", "skills", "data/rag_docs", "examples"], cwd=ROOT, text=True, timeout=10)
    if changed.strip():
        raise ValueError("runtime and development inputs must match committed code")
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "data/evaluation/results/development"):
        raise ValueError("output must stay inside development results")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Reserve before credentials or I/O. Interrupted runs retain a truthful pending record.
    with output.open("x", encoding="utf-8") as stream:
        identity = {"implementation_sha": head, "probe_sha256": digest(Path(__file__).read_bytes()),
                    "probe_public_ci_verified": False, "scope": "development_not_admission"}
        stream.write(json.dumps({**identity, "status": "pending"}) + "\n")
        stream.flush()
        from dotenv import dotenv_values
        from app.providers.config import load_zhipu_settings
        from app.evaluation.glm53_low_profile_domain_gate import create_low_profile_provider
        settings = load_zhipu_settings(dotenv_values(args.env_file))
        provider = create_low_profile_provider(settings)
        with tempfile.TemporaryDirectory(prefix="riftcoach-dev-query-") as temporary:
            result = observe(provider, root=ROOT, runs_root=Path(temporary), real=True,
                             retrieval_guidance=(COACHING_QUERY_GUIDANCE_V1 if args.retrieval_guidance else None),
                             scenario=args.scenario,
                             emit=lambda row: print(json.dumps(row), flush=True))
        result.update(identity)
        result["status"] = "execution_failed" if result["execution_error"] else "completed"
        stream.seek(0)
        stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
        stream.truncate()
    observation = result["observation"]
    print(json.dumps({"status": result["status"], "calls": result["resources"]["calls_used"],
                      "sources": len(observation["evidence_source_ids"]) if observation else None,
                      "terminal": observation["terminal_status"] if observation else None}), flush=True)
    return 1 if result["execution_error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
