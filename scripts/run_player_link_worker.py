from __future__ import annotations

import argparse
import os
import signal
import sys
from collections.abc import Callable, Mapping, Sequence
from threading import Event

from dotenv import load_dotenv

from app.players.composition import (
    PlayerLinkWorkerCompositionError,
    PlayerLinkWorkerProcess,
    build_player_link_worker_process,
    load_player_link_worker_settings,
)
from app.players.link_worker import PlayerLinkWorker, PlayerLinkWorkerError


def run_until_stopped(worker: PlayerLinkWorker) -> None:
    if not isinstance(worker, PlayerLinkWorker):
        raise TypeError("worker must be a PlayerLinkWorker")
    stop_event = Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_stop)
    worker.run_forever(stop_event)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the RiftCoach PostgreSQL player-link worker.",
    )
    parser.add_argument(
        "--worker-id",
        required=True,
        help="Bounded deployment-unique player-link worker identifier.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Validate complete composition and exit before polling.",
    )
    mode.add_argument(
        "--once",
        action="store_true",
        help="Run exactly one player-link claim iteration, then exit.",
    )
    return parser


ProcessFactory = Callable[..., PlayerLinkWorkerProcess]


def main(
    argv: Sequence[str] | None = None,
    *,
    environment: Mapping[str, str] | None = None,
    process_factory: ProcessFactory = build_player_link_worker_process,
) -> int:
    args = build_parser().parse_args(argv)
    if environment is None:
        load_dotenv()
        source: Mapping[str, str] = dict(os.environ)
    else:
        source = environment

    try:
        settings = load_player_link_worker_settings(source)
        with process_factory(settings, worker_id=args.worker_id) as process:
            if args.check:
                return 0
            if args.once:
                process.worker.run_once()
                return 0
            run_until_stopped(process.worker)
            return 0
    except PlayerLinkWorkerCompositionError as error:
        print(error.code, file=sys.stderr)
        return 2
    except PlayerLinkWorkerError as error:
        print(error.code, file=sys.stderr)
        return 1
    except Exception:
        print("player_link_worker_failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
