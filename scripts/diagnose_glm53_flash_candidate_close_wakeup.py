"""Run one explicitly authorized, body-free GLM-5.3 close/wakeup probe.

The default mode is a parent process.  It starts a short-lived child and
persists exactly one immutable receipt.  The child mode is intentionally
private to this script; it loads credentials only after the explicit
``--confirm-real-call`` gate has been checked.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.evaluation.candidate_provider_close_wakeup_observation import (  # noqa: E402
    CANDIDATE_CLOSE_WAKE_PROTOCOL_ID,
    CandidateCloseWakeObservation,
    CandidateCloseWakeObservationError,
    child_observation_line,
    observe_candidate_session,
    run_parent_close_wakeup_observation,
)
from app.evaluation.candidate_recovery_diagnostic_real import (  # noqa: E402
    BASE_URL,
    MODEL,
    _candidate_request,
    _load_environment,
    _load_frozen_context,
)
from app.providers.config import load_zhipu_settings  # noqa: E402
from app.providers.response_recovery_contract import (  # noqa: E402
    GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1,
)
from app.providers.zhipu import ZhipuProvider  # noqa: E402
from openai import OpenAI  # noqa: E402


DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_candidate_close_wakeup_observation_rq211_v1.json"
)
DEFAULT_PROCESS_DEADLINE_S = 30.0
DEFAULT_INITIAL_READ_TIMEOUT_S = 0.5
DEFAULT_CANCEL_TIMEOUT_S = 2.0
DEFAULT_READER_GRACE_S = 0.5


def _head_sha(root: Path) -> str:
    try:
        value = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except Exception:
        raise CandidateCloseWakeObservationError("head_sha_unavailable", "identity") from None
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise CandidateCloseWakeObservationError("head_sha_invalid", "identity")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one bounded, candidate-only GLM-5.3 provider close/wakeup "
            "observation; no retry or recovery call is permitted."
        )
    )
    parser.add_argument(
        "--confirm-real-call",
        action="store_true",
        help="Acknowledge one billable external candidate request.",
    )
    parser.add_argument("--repository-root", type=Path, default=_ROOT)
    parser.add_argument("--implementation-sha")
    parser.add_argument("--diagnostic-code-sha")
    parser.add_argument("--input-plan-sha")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--process-deadline-s",
        type=float,
        default=DEFAULT_PROCESS_DEADLINE_S,
    )
    parser.add_argument(
        "--initial-read-timeout-s",
        type=float,
        default=DEFAULT_INITIAL_READ_TIMEOUT_S,
    )
    parser.add_argument(
        "--cancel-timeout-s",
        type=float,
        default=DEFAULT_CANCEL_TIMEOUT_S,
    )
    parser.add_argument(
        "--reader-grace-s",
        type=float,
        default=DEFAULT_READER_GRACE_S,
    )
    parser.add_argument(
        "--child",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser


def _safe_child_error(code: str) -> CandidateCloseWakeObservation:
    return CandidateCloseWakeObservation(
        observation_state="child_error",
        call_count=0,
        session_opened=False,
        pending_reader_observed=False,
        cancel_status="not_attempted",
        cancel_returned=False,
        reader_woke=False,
        event_categories=(),
        initial_read_elapsed_ms=0,
        cancel_elapsed_ms=None,
        reader_grace_ms=0,
        reader_wake_elapsed_ms=None,
        close_report=None,
        error_code=code,
        child_exit_code=0,
        child_terminated=False,
    )


def _child_main(args: argparse.Namespace) -> int:
    """Open exactly one explicit adapter session and print safe JSON lines."""

    # This check is deliberately first: no dotenv, key, or client construction
    # happens before the explicit acknowledgement reaches the child.
    if args.confirm_real_call is not True:
        print(child_observation_line(_safe_child_error("confirmation_required")), flush=True)
        return 2
    root = args.repository_root.resolve()
    try:
        context = _load_frozen_context(root)
        settings = load_zhipu_settings(_load_environment(args.env_file))
        if settings.model.strip().lower() != MODEL:
            raise CandidateCloseWakeObservationError("candidate_model_mismatch", "identity")
        if settings.base_url.rstrip("/") != BASE_URL.rstrip("/"):
            raise CandidateCloseWakeObservationError("candidate_endpoint_mismatch", "identity")
        profile = GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1
        if profile.max_attempts != 2 or profile.max_additional_calls != 1:
            raise CandidateCloseWakeObservationError("candidate_profile_mismatch", "identity")
        # The probe itself is primary-only: it never invokes the candidate's
        # fresh-recovery slot and always sets the SDK retry budget to zero.
        client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=profile.transport_timeout_s,
            max_retries=0,
        )
        provider = ZhipuProvider(
            client=client,
            model=settings.model,
            profile=settings.thinking_profile,
        )
        adapter = provider.stream_adapter(tool_stream=False)
        request = _candidate_request(context.messages)
        calls = 0

        def session_factory(
            supplied_request=None,
            *,
            include_usage_tail: bool = False,
        ):
            nonlocal calls
            if calls != 0 or supplied_request is not request:
                raise CandidateCloseWakeObservationError("real_call_budget_exceeded", "budget")
            if include_usage_tail is not True:
                raise CandidateCloseWakeObservationError("usage_tail_required", "request")
            calls = 1
            # Flush a marker before the potentially blocking SDK open.  The
            # parent may use it only to say whether a call was attempted.
            print(
                json.dumps(
                    {"kind": "probe_started", "call_count": 1, "session_opened": False},
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                flush=True,
            )
            session = adapter.stream_session(
                supplied_request,
                include_usage_tail=True,
            )
            print(
                json.dumps(
                    {"kind": "probe_started", "call_count": 1, "session_opened": True},
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                flush=True,
            )
            return session

        observation = observe_candidate_session(
            session_factory,
            request=request,
            initial_read_timeout_s=args.initial_read_timeout_s,
            cancel_timeout_s=args.cancel_timeout_s,
            reader_grace_s=args.reader_grace_s,
        )
        if calls != 1:
            observation = _safe_child_error("real_call_count_invalid")
        print(child_observation_line(observation), flush=True)
        return 0
    except CandidateCloseWakeObservationError as error:
        print(child_observation_line(_safe_child_error(error.code)), flush=True)
        return 2
    except (GeneratorExit, KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        # Never copy SDK/provider exception text to stdout or stderr receipt
        # material.  The parent records only this bounded machine code.
        print(child_observation_line(_safe_child_error("child_probe_failed")), flush=True)
        return 2


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.child:
        return _child_main(args)
    if args.confirm_real_call is not True:
        print("candidate-close-wakeup-error=real_call_confirmation_required", file=sys.stderr)
        return 2
    root = args.repository_root.resolve()
    try:
        head = _head_sha(root)
        implementation_sha = args.implementation_sha or head
        diagnostic_code_sha = args.diagnostic_code_sha or head
        input_plan_sha = args.input_plan_sha or head
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--child",
            "--confirm-real-call",
            "--repository-root",
            str(root),
            "--implementation-sha",
            implementation_sha,
            "--diagnostic-code-sha",
            diagnostic_code_sha,
            "--input-plan-sha",
            input_plan_sha,
            "--process-deadline-s",
            str(args.process_deadline_s),
            "--initial-read-timeout-s",
            str(args.initial_read_timeout_s),
            "--cancel-timeout-s",
            str(args.cancel_timeout_s),
            "--reader-grace-s",
            str(args.reader_grace_s),
        ]
        if args.env_file is not None:
            command.extend(["--env-file", str(args.env_file.resolve())])
        result = run_parent_close_wakeup_observation(
            command,
            args.output if args.output.is_absolute() else root / args.output,
            implementation_sha=implementation_sha,
            diagnostic_code_sha=diagnostic_code_sha,
            input_plan_sha=input_plan_sha,
            confirm_real_call=True,
            process_deadline_s=args.process_deadline_s,
            cwd=root,
        )
    except CandidateCloseWakeObservationError as error:
        print(f"candidate-close-wakeup-error={error.code}", file=sys.stderr)
        return 2
    except FileExistsError:
        print("candidate-close-wakeup-error=evidence_exists", file=sys.stderr)
        return 2
    observation = result.observation
    print(
        "provider=zhipu model=glm-5.3-flash protocol=%s state=%s calls=%d "
        "cancel=%s cancel_returned=%s reader_woke=%s child_terminated=%s output=%s"
        % (
            CANDIDATE_CLOSE_WAKE_PROTOCOL_ID,
            observation.observation_state,
            observation.call_count,
            observation.cancel_status,
            observation.cancel_returned,
            observation.reader_woke,
            observation.child_terminated,
            result.output_path,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
