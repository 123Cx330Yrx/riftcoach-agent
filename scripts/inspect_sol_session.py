"""Inspect or reconcile original receipts, without credentials or provider calls."""
import argparse
import json
from pathlib import Path

from app.evaluation.sol_natural_session import CandidateSession, SessionBlocked, SessionPaused


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'reconcile'))
    parser.add_argument('--session', required=True, type=Path)
    parser.add_argument('--guard-sha', required=True)
    parser.add_argument('--checkpoint-sha', required=True)
    args = parser.parse_args()
    # Guard is independently pinned by the caller before any paths are used.
    from app.evaluation.sol_natural_session import digest
    raw = (args.session/'guard.json').read_bytes()
    if digest(raw) != args.guard_sha:
        raise ValueError('session_guard_changed')
    guard = json.loads(raw)
    def emit(value):
        print(json.dumps(value, ensure_ascii=True), flush=True)
    try:
        with CandidateSession(args.session, binding=guard['binding'],
                transport_root=guard['transport_root'], journal_root=guard['journal_root'],
                guard_sha=args.guard_sha, checkpoint_sha=args.checkpoint_sha,
                read_only=args.action == 'status', reconcile=args.action == 'reconcile',
                checkpoint_sink=emit) as session:
            emit(session.status() if args.action == 'status' else session.reconcile_completed())
    except (SessionBlocked, SessionPaused) as error:
        emit(dict(ok=False, code=str(error), provider_requests=0))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
