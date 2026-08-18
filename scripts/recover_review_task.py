"""Conservative, explicit recovery command for an owner-less review task."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from uuid import UUID

from dotenv import load_dotenv

from app.persistence.config import load_database_settings
from app.persistence.database import build_engine, build_session_factory
from app.persistence.task_repository import PostgresTaskRepository
from app.tasks.reconciliation import ManualReviewTaskRecovery


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Conditionally mark one confirmed-dead review worker as failed.",
    )
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--worker-id", required=True)
    parser.add_argument(
        "--confirm-worker-id",
        required=True,
        help="Must exactly equal --worker-id; this is the explicit operator confirmation.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.worker_id != args.confirm_worker_id:
        print("worker_confirmation_mismatch", file=sys.stderr)
        return 2
    try:
        task_id = UUID(args.task_id)
        load_dotenv()
        settings = load_database_settings()
        engine = build_engine(settings)
        repository = PostgresTaskRepository(build_session_factory(engine))
        result = ManualReviewTaskRecovery(repository).recover(
            task_id=task_id,
            worker_id=args.worker_id,
            confirmation_worker_id=args.confirm_worker_id,
        )
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False))
        return 0 if result.status.value == "recovered" else 3
    except (ValueError, TypeError):
        print("task_recovery_input_invalid", file=sys.stderr)
        return 2
    except Exception:
        # Never expose DATABASE_URL, SQL, paths, or driver details.
        print("task_recovery_unavailable", file=sys.stderr)
        return 3
    finally:
        if "engine" in locals():
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
