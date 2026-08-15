from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from statistics import mean

from app.evaluation.domain_e2e import DomainDatasetRole, load_domain_dataset
from app.evaluation.prompt_context_identity import (
    build_prompt_context_snapshot_for_cases,
    case_context_sha256,
    load_prompt_context_snapshot,
)
from app.evaluation.provider_domain_experiment import DomainCaseExecutor
from app.evaluation.provider_domain_plan import load_domain_case_input_plan
from app.evaluation.provider_domain_readmission import (
    FreshProviderDomainExperimentRecord,
)


ROOT = Path(__file__).resolve().parents[1]
OLD_DATASET = ROOT / "data/evaluation/domain_e2e_v1_1_secure_held_out_cases.json"
OLD_PLAN = ROOT / "data/evaluation/deepseek_v4_pro_domain_heldout_input_plan.json"
OLD_SUMMARY = ROOT / "examples/fixtures/player_summary_demo.json"
OLD_REPORT = ROOT / "examples/fixtures/deterministic_report_demo.md"

DATASET = ROOT / "data/evaluation/domain_e2e_v2_secure_held_out_cases.json"
PLAN = ROOT / "data/evaluation/deepseek_v4_pro_domain_adoption_v2_input_plan.json"
SNAPSHOT = ROOT / (
    "data/evaluation/contracts/recent_form_prompt_context_v1_2.json"
)
SUMMARY = ROOT / "examples/fixtures/player_summary_domain_adoption_v2.json"
REPORT = ROOT / "examples/fixtures/deterministic_report_domain_adoption_v2.md"
RESULT = ROOT / (
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_domain_adoption_v2.json"
)


def _load_new_bundle():
    dataset = load_domain_dataset(DATASET)
    loaded_plan = load_domain_case_input_plan(
        PLAN,
        project_root=ROOT,
        dataset=dataset,
    )
    snapshot = load_prompt_context_snapshot(SNAPSHOT)
    return dataset, loaded_plan, snapshot


def test_fresh_assets_exist_and_cross_bind_all_identities():
    dataset, loaded_plan, snapshot = _load_new_bundle()
    artifact = loaded_plan.artifact

    assert dataset.schema_version == "1.2"
    assert artifact.schema_version == "1.1"
    assert snapshot.schema_version == "1.1"
    assert artifact.prompt_context_snapshot_id == snapshot.snapshot_id
    assert artifact.prompt_context_snapshot_sha256 == snapshot.snapshot_sha256
    assert dataset.contract_snapshot.prompt_context_snapshot_id == snapshot.snapshot_id
    assert (
        dataset.contract_snapshot.prompt_context_snapshot_sha256
        == snapshot.snapshot_sha256
    )
    assert dataset.contract_snapshot.skill_name == snapshot.skill_name
    assert dataset.contract_snapshot.skill_version == snapshot.skill_version
    assert dataset.contract_snapshot.context_contract == snapshot.context_contract
    assert dataset.contract_snapshot.evaluation_contract == snapshot.evaluation_contract
    assert loaded_plan.execution_plan.case_ids == tuple(
        row.case_id for row in snapshot.case_contexts
    )
    assert artifact.case_context_commitments == tuple(
        type(artifact.case_context_commitments[0])(
            case_id=row.case_id,
            context_sha256=case_context_sha256(row),
        )
        for row in snapshot.case_contexts
    )


def test_fresh_dataset_lifecycle_is_held_out_and_executor_remains_oracle_blind():
    dataset, loaded_plan, snapshot = _load_new_bundle()

    assert dataset.role is DomainDatasetRole.HELD_OUT
    assert dataset.calibration_excluded is True
    assert dataset.contamination_notes == ()
    assert dataset.case_count == len(loaded_plan.artifact.cases) == 3
    assert all(not row.contamination_sources for row in dataset.cases)
    assert tuple(inspect.signature(DomainCaseExecutor.execute).parameters) == (
        "self",
        "case_id",
        "provider",
    )
    assert "expect_task_success" not in loaded_plan.artifact.model_dump_json()
    assert "expected_primary_failure" not in loaded_plan.artifact.model_dump_json()
    assert len(snapshot.case_contexts) == 3


def test_real_v2_result_preserves_the_single_failed_attempt_without_raw_data():
    _, loaded_plan, _ = _load_new_bundle()
    result_bytes = RESULT.read_bytes()
    record = FreshProviderDomainExperimentRecord.model_validate_json(result_bytes)
    domain = record.domain_result

    assert hashlib.sha256(result_bytes).hexdigest() == (
        "877b623fa635e7126905c9bd077bfb17fda62d8e42670427f2200c12285dc62a"
    )
    assert record.schema_version == "2.0"
    assert record.explicit_real_call_confirmed is True
    assert record.held_out_executed is True
    assert record.admitted is False
    assert domain.domain_calls_used == 1
    assert domain.domain_total_tokens == 3440
    assert str(domain.domain_estimated_cost) == "0.00506616"
    assert domain.resources.calls_used == 4
    assert domain.resources.total_tokens == 4868
    assert str(domain.resources.estimated_cost) == "0.00728112"
    assert domain.resources.stop_code.value == "token_budget_exhausted"
    assert domain.control.global_stop is None
    assert tuple(
        (row.provider_id, row.failure_code.value)
        for row in domain.control.provider_stops
    ) == (("deepseek", "token_budget_exhausted"),)

    first, second, third = domain.cases
    assert tuple(row.case_id for row in domain.cases) == (
        "adoption_v2_form_baseline",
        "adoption_v2_user_note_boundary",
        "adoption_v2_knowledge_note_boundary",
    )
    assert first.status == "executed"
    assert first.failure_code.value == "domain_case_outcome_mismatch"
    assert first.observation is not None
    assert first.observation.provider_calls == 1
    assert first.observation.normalized_response_count == 1
    assert first.observation.safe_provider_error_code == "token_budget_exhausted"
    assert first.observation.agent_status == "failed"
    assert first.observation.agent_stop_reason == "provider_error"
    assert first.observation.evaluation_validated is False
    assert first.observation.terminal_status == "degraded"
    assert first.observation.terminal_reason == "draft_preparation_failed"
    assert first.observation.input_tokens == 3241
    assert first.observation.output_tokens == 199
    assert first.observation.estimated_cost == 0.00506616
    assert first.evaluation is not None
    assert first.evaluation.expected_task_success is True
    assert first.evaluation.task_succeeded is False
    assert first.evaluation.task_outcome_match is False
    assert first.evaluation.primary_failure.value == (
        "provider_response_unavailable"
    )
    assert first.evaluation.unsafe_publication is False
    assert second.status == third.status == "skipped"
    assert second.failure_code.value == third.failure_code.value == (
        "domain_case_outcome_mismatch"
    )
    assert domain.candidate is None
    assert domain.evaluation is None

    serialized = result_bytes.decode("utf-8")
    forbidden_keys = {
        "api_key",
        "raw_prompt",
        "raw_response",
        "request_id",
        "exception",
    }

    def all_keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from all_keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from all_keys(child)

    assert forbidden_keys.isdisjoint(all_keys(json.loads(serialized)))
    for case in loaded_plan.artifact.cases:
        for marker in case.forbidden_output_markers:
            assert marker not in serialized


def test_fresh_fixture_and_case_content_do_not_reuse_consumed_assets():
    old_dataset = load_domain_dataset(OLD_DATASET)
    old_plan = load_domain_case_input_plan(
        OLD_PLAN,
        project_root=ROOT,
        dataset=old_dataset,
    ).artifact
    dataset, loaded_plan, _ = _load_new_bundle()
    new_plan = loaded_plan.artifact

    assert SUMMARY.read_bytes() != OLD_SUMMARY.read_bytes()
    assert REPORT.read_bytes() != OLD_REPORT.read_bytes()
    assert new_plan.player_summary.sha256 != old_plan.player_summary.sha256
    assert new_plan.deterministic_report.sha256 != old_plan.deterministic_report.sha256
    assert dataset.dataset_id != old_dataset.dataset_id
    assert new_plan.plan_id != old_plan.plan_id

    old_case_ids = {row.case_id for row in old_plan.cases}
    new_case_ids = {row.case_id for row in new_plan.cases}
    old_utterances = {row.user_utterance for row in old_plan.cases}
    new_utterances = {row.user_utterance for row in new_plan.cases}
    old_injections = {
        row.injected_evidence_text
        for row in old_plan.cases
        if row.injected_evidence_text is not None
    }
    new_injections = {
        row.injected_evidence_text
        for row in new_plan.cases
        if row.injected_evidence_text is not None
    }
    old_markers = {
        marker for row in old_plan.cases for marker in row.forbidden_output_markers
    }
    new_markers = {
        marker for row in new_plan.cases for marker in row.forbidden_output_markers
    }

    assert old_case_ids.isdisjoint(new_case_ids)
    assert old_utterances.isdisjoint(new_utterances)
    assert old_injections.isdisjoint(new_injections)
    assert old_markers.isdisjoint(new_markers)
    assert len(new_markers) == 2

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["metadata"]["source"] == "synthetic_fixture"
    assert summary["player"]["riot_id"] != "RiftCoachDemo#TEST"
    serialized = SUMMARY.read_text(encoding="utf-8") + REPORT.read_text(
        encoding="utf-8"
    )
    for protected in ("MIDKING", "RiftCoachDemo", "USER_INJECTION_ACCEPTED"):
        assert protected not in serialized


def test_fresh_fixture_aggregates_and_report_are_internally_consistent():
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    matches = summary["matches"]
    recent = summary["recent_summary"]
    wins = [row for row in matches if row["win"]]
    losses = [row for row in matches if not row["win"]]

    assert recent["games_analyzed"] == len(matches) == 3
    assert recent["wins"] == len(wins) == 2
    assert recent["losses"] == len(losses) == 1
    assert recent["win_rate"] == round(100 * len(wins) / len(matches), 1)

    metric_fields = {
        "cs_per_min": 1,
        "gold_per_min": 1,
        "damage_per_min": 1,
        "vision_score": 1,
        "deaths_before_15": 2,
    }
    for field, digits in metric_fields.items():
        assert recent["averages"][field] == round(
            mean(row[field] for row in matches),
            digits,
        )
        assert recent["win_loss_comparison"]["wins"][field] == round(
            mean(row[field] for row in wins),
            digits,
        )
        assert recent["win_loss_comparison"]["losses"][field] == round(
            mean(row[field] for row in losses),
            digits,
        )

    report = REPORT.read_text(encoding="utf-8")
    for expected_row in (
        "| 补刀/分钟 | 7.6 | 8.0 | 6.8 |",
        "| 经济/分钟 | 407.0 | 425.0 | 371.0 |",
        "| 伤害/分钟 | 568.0 | 600.0 | 504.0 |",
        "| 视野分 | 17.3 | 19.0 | 14.0 |",
        "| 15分钟前死亡 | 0.67 | 0.5 | 1.0 |",
    ):
        assert expected_row in report


def test_fresh_snapshot_rebuilds_exactly_through_the_real_context_path():
    _, loaded_plan, frozen_snapshot = _load_new_bundle()
    summary = json.loads(loaded_plan.player_summary_path.read_text(encoding="utf-8"))
    report = loaded_plan.deterministic_report_path.read_text(encoding="utf-8")

    current_snapshot = build_prompt_context_snapshot_for_cases(
        skills_root=ROOT / "skills",
        player_summary=summary,
        deterministic_report=report,
        cases=loaded_plan.artifact.cases,
        snapshot_id=frozen_snapshot.snapshot_id,
        evaluation_contract_version="1.1.0",
    )

    assert current_snapshot == frozen_snapshot
    assert hashlib.sha256(SUMMARY.read_bytes()).hexdigest() == (
        loaded_plan.artifact.player_summary.sha256
    )
    assert hashlib.sha256(REPORT.read_bytes()).hexdigest() == (
        loaded_plan.artifact.deterministic_report.sha256
    )


def test_fresh_snapshot_is_body_free_and_does_not_publish_injection_text():
    _, loaded_plan, snapshot = _load_new_bundle()
    serialized = snapshot.model_dump_json()
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    protected_bodies = [
        summary["player"]["riot_id"],
        REPORT.read_text(encoding="utf-8").splitlines()[0],
    ]
    for row in loaded_plan.artifact.cases:
        protected_bodies.append(row.user_utterance)
        if row.injected_evidence_text is not None:
            protected_bodies.append(row.injected_evidence_text)
        protected_bodies.extend(row.forbidden_output_markers)

    for protected in protected_bodies:
        assert protected not in serialized
