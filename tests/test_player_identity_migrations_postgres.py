from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from app.persistence.database import Base
from app.persistence.player_records import (
    OwnerPlayerRelationshipRecord,
    PlayerAliasRecord,
    PlayerLinkTaskRecord,
    PlayerSubjectRecord,
)


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_ENV = "RIFTCOACH_TEST_DATABASE_URL"


@pytest.fixture()
def postgres_migration_database(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    url = os.getenv(TEST_DATABASE_ENV)
    if not url:
        pytest.skip(
            f"{TEST_DATABASE_ENV} is not configured; real PostgreSQL migration evidence runs in CI"
        )
    if not url.startswith("postgresql+psycopg://"):
        pytest.fail(f"{TEST_DATABASE_ENV} must use postgresql+psycopg")

    monkeypatch.setenv("DATABASE_URL", url)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))

    command.downgrade(config, "base")
    try:
        yield url
    finally:
        command.downgrade(config, "base")


def test_player_identity_metadata_defines_expected_tables_and_constraints() -> None:
    assert PlayerSubjectRecord.__table__.metadata is Base.metadata
    assert PlayerAliasRecord.__table__.metadata is Base.metadata
    assert OwnerPlayerRelationshipRecord.__table__.metadata is Base.metadata
    assert PlayerLinkTaskRecord.__table__.metadata is Base.metadata

    assert {
        "player_subjects",
        "player_aliases",
        "owner_player_relationships",
        "player_link_tasks",
    } <= set(Base.metadata.tables)

    subject_constraints = {
        constraint.name for constraint in PlayerSubjectRecord.__table__.constraints
    }
    alias_constraints = {
        constraint.name for constraint in PlayerAliasRecord.__table__.constraints
    }
    relationship_constraints = {
        constraint.name
        for constraint in OwnerPlayerRelationshipRecord.__table__.constraints
    }
    link_constraints = {
        constraint.name for constraint in PlayerLinkTaskRecord.__table__.constraints
    }
    alias_indexes = {index.name for index in PlayerAliasRecord.__table__.indexes}
    relationship_indexes = {
        index.name for index in OwnerPlayerRelationshipRecord.__table__.indexes
    }
    link_indexes = {index.name for index in PlayerLinkTaskRecord.__table__.indexes}

    assert {
        "pk_player_subjects",
        "uq_player_subjects_game_puuid",
        "ck_player_subjects_game_allowed",
        "ck_player_subjects_current_routing_region_allowed",
        "ck_player_subjects_timestamp_order",
    } <= subject_constraints
    assert {
        "pk_player_aliases",
        "uq_player_aliases_subject_region_riot_id_hash",
        "ck_player_aliases_routing_region_allowed",
        "ck_player_aliases_normalized_riot_id_hash_format",
        "ck_player_aliases_timestamp_order",
    } <= alias_constraints
    assert {
        "pk_owner_player_relationships",
        "uq_owner_player_relationships_owner_id_player_subject_id",
        "uq_owner_player_relationships_identity",
        "ck_owner_player_relationships_relationship_role_allowed",
        "ck_owner_player_relationships_verification_status_allowed",
        "ck_owner_player_relationships_status_allowed",
        "ck_owner_player_relationships_role_verification_allowed",
        "ck_owner_player_relationships_hidden_status_shape",
        "ck_owner_player_relationships_timestamp_order",
    } <= relationship_constraints
    assert {
        "pk_player_link_tasks",
        "uq_player_link_tasks_owner_id_idempotency_key",
        "ck_player_link_tasks_task_kind_allowed",
        "ck_player_link_tasks_schema_version_allowed",
        "ck_player_link_tasks_routing_region_allowed",
        "ck_player_link_tasks_relationship_role_allowed",
        "ck_player_link_tasks_request_fingerprint_format",
        "ck_player_link_tasks_alias_hash_format",
        "ck_player_link_tasks_terminal_reason_format",
        "ck_player_link_tasks_riot_id_components_bounded",
        "ck_player_link_tasks_lifecycle_shape",
        "ck_player_link_tasks_timestamp_order",
    } <= link_constraints
    assert {
        "ix_player_aliases_player_subject_id",
    } <= alias_indexes
    assert {
        "ix_owner_player_relationships_player_subject_id",
    } <= relationship_indexes
    assert {
        "ix_player_link_tasks_claim",
        "ix_player_link_tasks_owner_history",
        "ix_player_link_tasks_player_subject_id",
        "ix_player_link_tasks_relationship_id",
    } <= link_indexes

    assert PlayerLinkTaskRecord.__table__.c.game_name.type.length == 64
    assert PlayerLinkTaskRecord.__table__.c.tag_line.type.length == 32
    assert PlayerLinkTaskRecord.__table__.c.confirmed_game_name.type.length == 64
    assert PlayerLinkTaskRecord.__table__.c.confirmed_tag_line.type.length == 32
    assert PlayerLinkTaskRecord.__table__.c.created_at.type.timezone is True
    assert PlayerLinkTaskRecord.__table__.c.updated_at.type.timezone is True
    assert PlayerLinkTaskRecord.__table__.c.claimed_at.type.timezone is True
    assert PlayerLinkTaskRecord.__table__.c.finished_at.type.timezone is True


def test_player_identity_migration_creates_postgresql_schema(
    postgres_migration_database: str,
) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.upgrade(config, "head")

    engine = sa.create_engine(postgres_migration_database)
    try:
        inspector = sa.inspect(engine)
        assert {
            "review_tasks",
            "player_subjects",
            "player_aliases",
            "owner_player_relationships",
            "player_link_tasks",
        } <= set(inspector.get_table_names())

        subject_columns = {
            column["name"]: column
            for column in inspector.get_columns("player_subjects")
        }
        alias_unique_names = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("player_aliases")
        }
        relationship_unique_names = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints(
                "owner_player_relationships"
            )
        }
        relationship_check_names = {
            constraint["name"]
            for constraint in inspector.get_check_constraints(
                "owner_player_relationships"
            )
        }
        link_columns = {
            column["name"]: column
            for column in inspector.get_columns("player_link_tasks")
        }
        link_check_names = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("player_link_tasks")
        }
        link_index_names = {
            index["name"] for index in inspector.get_indexes("player_link_tasks")
        }
        fk_names = {
            foreign_key["name"]
            for foreign_key in inspector.get_foreign_keys("player_link_tasks")
        }

        assert subject_columns["created_at"]["type"].timezone is True
        assert subject_columns["updated_at"]["type"].timezone is True
        assert subject_columns["last_resolved_at"]["type"].timezone is True
        assert relationship_unique_names >= {
            "uq_owner_player_relationships_owner_id_player_subject_id",
            "uq_owner_player_relationships_identity",
        }
        assert alias_unique_names >= {
            "uq_player_aliases_subject_region_riot_id_hash"
        }
        assert relationship_check_names >= {
            "ck_owner_player_relationships_role_verification_allowed"
        }
        assert link_columns["game_name"]["type"].length == 64
        assert link_columns["tag_line"]["type"].length == 32
        assert link_columns["confirmed_game_name"]["type"].length == 64
        assert link_columns["confirmed_tag_line"]["type"].length == 32
        assert link_columns["created_at"]["type"].timezone is True
        assert link_columns["updated_at"]["type"].timezone is True
        assert link_columns["claimed_at"]["type"].timezone is True
        assert link_columns["finished_at"]["type"].timezone is True
        assert {
            "ck_player_link_tasks_lifecycle_shape",
            "ck_player_link_tasks_terminal_reason_format",
        } <= link_check_names
        assert {
            "ix_player_link_tasks_claim",
            "ix_player_link_tasks_owner_history",
            "ix_player_link_tasks_player_subject_id",
            "ix_player_link_tasks_relationship_id",
        } <= link_index_names
        assert {
            "fk_player_link_tasks_player_subject_id_player_subjects",
            "fk_player_link_tasks_relationship_identity",
        } <= fk_names
        relationship_fk = next(
            foreign_key
            for foreign_key in inspector.get_foreign_keys("player_link_tasks")
            if foreign_key["name"]
            == "fk_player_link_tasks_relationship_identity"
        )
        assert relationship_fk["constrained_columns"] == [
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
        ]
        assert relationship_fk["referred_columns"] == [
            "owner_id",
            "relationship_id",
            "player_subject_id",
            "relationship_role",
        ]
    finally:
        engine.dispose()


def test_player_identity_migration_downgrades_to_review_task_foundation(
    postgres_migration_database: str,
) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))

    command.upgrade(config, "head")
    command.downgrade(config, "0001_review_tasks")

    engine = sa.create_engine(postgres_migration_database)
    try:
        table_names = set(sa.inspect(engine).get_table_names())
        assert "review_tasks" in table_names
        assert "player_subjects" not in table_names
        assert "player_aliases" not in table_names
        assert "owner_player_relationships" not in table_names
        assert "player_link_tasks" not in table_names
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_migration_database)
    try:
        table_names = set(sa.inspect(engine).get_table_names())
        assert "review_tasks" in table_names
        assert "player_link_tasks" in table_names
    finally:
        engine.dispose()


def test_player_identity_migration_enforces_link_lifecycle_shapes(
    postgres_migration_database: str,
) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_migration_database)

    subject_id = uuid.uuid4()
    relationship_id = uuid.uuid4()
    link_task_id = uuid.uuid4()
    base_values = {
        "link_task_id": link_task_id,
        "task_kind": "player_link",
        "schema_version": "1.0",
        "owner_id": "owner-test",
        "idempotency_key": "idem-player-link",
        "request_fingerprint": "a" * 64,
        "game_name": "DemoPlayer",
        "tag_line": "NA1",
        "routing_region": "americas",
        "relationship_role": "self",
        "alias_hash": "b" * 64,
    }

    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO player_subjects (
                        player_subject_id, game, puuid, current_routing_region,
                        created_at, updated_at, last_resolved_at
                    ) VALUES (
                        :player_subject_id, 'lol', :puuid, 'americas', now(), now(), now()
                    )
                    """
                ),
                {
                    "player_subject_id": subject_id,
                    "puuid": "PUUID-DEMO-1234567890",
                },
            )
            connection.execute(
                sa.text(
                    """
                    INSERT INTO owner_player_relationships (
                        relationship_id, owner_id, player_subject_id,
                        relationship_role, verification_status, status,
                        created_at, updated_at
                    ) VALUES (
                        :relationship_id, 'owner-test', :player_subject_id,
                        'self', 'unverified_claim', 'active', now(), now()
                    )
                    """
                ),
                {
                    "relationship_id": relationship_id,
                    "player_subject_id": subject_id,
                },
            )
            connection.execute(
                sa.text(
                    """
                    INSERT INTO player_link_tasks (
                        link_task_id, task_kind, schema_version, owner_id, idempotency_key,
                        request_fingerprint, game_name, tag_line, routing_region,
                        relationship_role, alias_hash
                    ) VALUES (
                        :link_task_id, :task_kind, :schema_version, :owner_id, :idempotency_key,
                        :request_fingerprint, :game_name, :tag_line, :routing_region,
                        :relationship_role, :alias_hash
                    )
                    """
                ),
                base_values,
            )

            connection.execute(
                sa.text(
                    """
                    UPDATE player_link_tasks
                    SET status = 'succeeded',
                        worker_id = 'worker-1',
                        claimed_at = now(),
                        finished_at = now(),
                        confirmed_game_name = 'DemoPlayer',
                        confirmed_tag_line = 'NA1',
                        player_subject_id = :player_subject_id,
                        relationship_id = :relationship_id
                    WHERE link_task_id = :link_task_id
                    """
                ),
                {
                    "link_task_id": link_task_id,
                    "player_subject_id": subject_id,
                    "relationship_id": relationship_id,
                },
            )

            invalid_failed_link_task_id = uuid.uuid4()
            connection.execute(
                sa.text(
                    """
                    INSERT INTO player_link_tasks (
                        link_task_id, task_kind, schema_version, owner_id, idempotency_key,
                        request_fingerprint, game_name, tag_line, routing_region,
                        relationship_role, alias_hash
                    ) VALUES (
                        :link_task_id, :task_kind, :schema_version, :owner_id, :idempotency_key,
                        :request_fingerprint, :game_name, :tag_line, :routing_region,
                        :relationship_role, :alias_hash
                    )
                    """
                ),
                {
                    **base_values,
                    "link_task_id": invalid_failed_link_task_id,
                    "idempotency_key": "idem-player-link-failed",
                },
            )

        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        """
                        UPDATE player_link_tasks
                        SET status = 'failed',
                            worker_id = 'worker-1',
                            claimed_at = now(),
                            finished_at = now(),
                            terminal_reason = 'relationship_role_conflict',
                            player_subject_id = :player_subject_id
                        WHERE link_task_id = :link_task_id
                        """
                    ),
                    {
                        "link_task_id": invalid_failed_link_task_id,
                        "player_subject_id": subject_id,
                    },
                )

        cross_role_link_task_id = uuid.uuid4()
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        """
                        INSERT INTO player_link_tasks (
                            link_task_id, task_kind, schema_version, owner_id,
                            idempotency_key, request_fingerprint, game_name,
                            tag_line, routing_region, relationship_role, alias_hash
                        ) VALUES (
                            :link_task_id, 'player_link', '1.0', 'owner-test',
                            'idem-cross-role', :request_fingerprint, 'DemoPlayer',
                            'NA1', 'americas', 'observed', :alias_hash
                        )
                        """
                    ),
                    {
                        "link_task_id": cross_role_link_task_id,
                        "request_fingerprint": "c" * 64,
                        "alias_hash": "d" * 64,
                    },
                )
                connection.execute(
                    sa.text(
                        """
                        UPDATE player_link_tasks
                        SET status = 'succeeded', worker_id = 'worker-2',
                            claimed_at = now(), finished_at = now(),
                            confirmed_game_name = 'DemoPlayer',
                            confirmed_tag_line = 'NA1',
                            player_subject_id = :player_subject_id,
                            relationship_id = :relationship_id
                        WHERE link_task_id = :link_task_id
                        """
                    ),
                    {
                        "link_task_id": cross_role_link_task_id,
                        "player_subject_id": subject_id,
                        "relationship_id": relationship_id,
                    },
                )
    finally:
        engine.dispose()
