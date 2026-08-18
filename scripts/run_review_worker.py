from __future__ import annotations

import argparse
import signal
import sys
from collections.abc import Sequence
from threading import Event

from app.workers.review_worker import ReviewWorker


def run_until_stopped(worker: ReviewWorker) -> None:
    if not isinstance(worker, ReviewWorker):
        raise TypeError("worker must be a ReviewWorker")
    stop_event = Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_stop)
    worker.run_forever(stop_event)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the RiftCoach PostgreSQL review-task worker.",
    )
    parser.add_argument(
        "--worker-id",
        required=True,
        help="Bounded deployment-unique worker identifier.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    # 6A-3 deliberately has only a Fake Executor contract. Claiming production
    # rows without the 6A-4 Application/Artifact executor would destroy work,
    # so the executable entry point remains fail-closed until that composition
    # is implemented.
    print("review_worker_executor_not_configured", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
