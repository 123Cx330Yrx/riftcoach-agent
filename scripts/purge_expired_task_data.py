"""Purge task data by the 6A retention contract.

The command is deliberately explicit about its roots and never loads a model
or external API key.  SQL rows are hidden in a short repository transaction;
run directories are then cleaned with the same safe compensating cleaner used
by the DELETE endpoint.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.persistence.config import DatabaseSettings
from app.persistence.database import build_engine, build_session_factory
from app.persistence.task_repository import PostgresTaskRepository
from app.tasks.deletion import FileRunDataCleaner
from app.tasks.retention import RetentionKind, RetentionPolicy, RetentionService


@dataclass(frozen=True, slots=True)
class PurgeReport:
    terminal_rows_hidden: int
    run_directories_cleaned: int
    cleanup_pending: int
    filesystem_entries_removed: int


def purge_expired_task_data(
    *,
    runs_root: str | Path,
    repository: PostgresTaskRepository | None = None,
    cache_root: str | Path | None = None,
    logs_root: str | Path | None = None,
    now: datetime | None = None,
    policy: RetentionPolicy | None = None,
) -> PurgeReport:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    retention = RetentionService(policy=policy or RetentionPolicy(), clock=lambda: current)
    cleaner = FileRunDataCleaner(runs_root, clock=lambda: current)

    terminal_rows_hidden = 0
    # Retry previously recorded cleanup work first.  These runs are already
    # hidden from SQL/API queries, so retrying cannot re-expose them.
    run_directories_cleaned = cleaner.retry_pending()
    cleanup_pending = 0
    if repository is not None:
        run_ids = repository.delete_expired_terminal(
            before=current - retention.policy.ttl_for(RetentionKind.TERMINAL_RUN)
        )
        terminal_rows_hidden = len(run_ids)
        for run_id in run_ids:
            if cleaner.cleanup(run_id):
                run_directories_cleaned += 1
            else:
                cleanup_pending += 1
    if cleaner.compensation_root.is_dir():
        cleanup_pending += len(tuple(cleaner.compensation_root.glob("*.json")))

    filesystem_entries_removed = 0
    for root, kind in (
        (cache_root, RetentionKind.RIOT_CACHE),
        (logs_root, RetentionKind.OPERATIONS_LOG),
    ):
        if root is None:
            continue
        filesystem_entries_removed += _purge_filesystem_root(
            Path(root),
            retention=retention,
            kind=kind,
            now=current,
        )

    return PurgeReport(
        terminal_rows_hidden=terminal_rows_hidden,
        run_directories_cleaned=run_directories_cleaned,
        cleanup_pending=cleanup_pending,
        filesystem_entries_removed=filesystem_entries_removed,
    )


def _purge_filesystem_root(
    root: Path,
    *,
    retention: RetentionService,
    kind: RetentionKind,
    now: datetime,
) -> int:
    if not root.is_dir():
        return 0
    removed = 0
    for entry in sorted(root.iterdir()):
        try:
            modified = datetime.fromtimestamp(
                entry.stat().st_mtime,
                tz=timezone.utc,
            )
            if not retention.is_expired(kind=kind, created_at=modified, now=now):
                continue
            if entry.is_symlink() or entry.is_file():
                entry.unlink()
            elif entry.is_dir():
                import shutil

                shutil.rmtree(entry)
            removed += 1
        except OSError:
            # A later run can retry; the command never prints the path or
            # exception body because paths may contain user-controlled data.
            continue
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge expired RiftCoach task data")
    parser.add_argument("--runs-root", default="data/runs")
    parser.add_argument("--cache-root", default="data/cache")
    parser.add_argument("--logs-root", default="data/logs")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    args = parser.parse_args()

    repository = None
    engine = None
    if args.database_url:
        engine = build_engine(DatabaseSettings(url=args.database_url))
        repository = PostgresTaskRepository(build_session_factory(engine))
    try:
        report = purge_expired_task_data(
            runs_root=args.runs_root,
            repository=repository,
            cache_root=args.cache_root,
            logs_root=args.logs_root,
        )
        print(
            "purge_completed "
            f"terminal_rows_hidden={report.terminal_rows_hidden} "
            f"run_directories_cleaned={report.run_directories_cleaned} "
            f"cleanup_pending={report.cleanup_pending} "
            f"filesystem_entries_removed={report.filesystem_entries_removed}"
        )
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
