from __future__ import annotations

import io
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.persistence.database import Base
from app.persistence.memory_records import MemoryCandidateRecord


ROOT = Path(__file__).resolve().parents[1]


def _config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


def test_memory_candidate_metadata_contract() -> None:
    assert MemoryCandidateRecord.__table__.metadata is Base.metadata
    assert "memory_candidates" in Base.metadata.tables
    constraints = {item.name for item in MemoryCandidateRecord.__table__.constraints}
    indexes = {item.name for item in MemoryCandidateRecord.__table__.indexes}
    assert {
        "pk_memory_candidates",
        "uq_memory_candidates_owner_id_idempotency_key",
        "uq_memory_candidates_identity",
        "fk_memory_candidates_conversation_identity",
        "fk_memory_candidates_source_message",
        "fk_memory_candidates_source_task",
        "ck_memory_candidates_schema_version_allowed",
        "ck_memory_candidates_relationship_role_allowed",
        "ck_memory_candidates_target_scope_allowed",
        "ck_memory_candidates_candidate_kind_allowed",
        "ck_memory_candidates_operation_allowed",
        "ck_memory_candidates_provenance_kind_allowed",
        "ck_memory_candidates_status_allowed",
        "ck_memory_candidates_status_shape",
        "ck_memory_candidates_timestamp_order",
        "ck_memory_candidates_observed_candidate_shape",
        "ck_memory_candidates_inference_requires_confirmation",
        "ck_memory_candidates_training_plan_requires_confirmation",
    } <= constraints
    assert {
        "ix_memory_candidates_owner_pending",
        "ix_memory_candidates_conversation_history",
        "ix_memory_candidates_expiry",
    } <= indexes
    assert all(len(str(name)) <= 63 for name in constraints | indexes)


def test_memory_candidate_revision_is_short_and_offline_sql_has_trigger(monkeypatch) -> None:
    head = ScriptDirectory.from_config(_config()).get_current_head()
    assert head == "0007_training_plan_progress"
    assert len(head) <= 32

    output = io.StringIO()
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://riftcoach:offline@localhost:5432/riftcoach",
    )
    config = Config(str(ROOT / "alembic.ini"), output_buffer=output)
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option(
        "sqlalchemy.url",
        "postgresql+psycopg://riftcoach:offline@localhost:5432/riftcoach",
    )
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE memory_candidates" in sql
    assert "CREATE FUNCTION riftcoach_guard_memory_candidate_update" in sql
    assert "CREATE TRIGGER trg_memory_candidates_guard_update" in sql
    assert "fk_memory_candidates_source_task" in sql
    assert "ck_memory_candidates_status_shape" in sql
