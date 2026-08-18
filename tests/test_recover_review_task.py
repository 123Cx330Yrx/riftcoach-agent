from __future__ import annotations

from uuid import UUID

from scripts.recover_review_task import main


def test_recovery_cli_requires_exact_worker_confirmation_without_touching_database():
    assert (
        main(
            [
                "--task-id",
                str(UUID("11111111-1111-4111-8111-111111111111")),
                "--worker-id",
                "worker-1",
                "--confirm-worker-id",
                "worker-2",
            ]
        )
        == 2
    )
