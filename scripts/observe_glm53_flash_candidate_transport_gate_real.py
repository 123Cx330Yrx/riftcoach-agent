"""Run one bounded, body-free real GLM-5.3 transport-gate observation.

The parent process owns the hard wall-clock boundary.  The child loads the
explicitly supplied dotenv file only after ``--confirm-real-call`` has been
checked, opens one Zhipu candidate stream through the existing neutral
adapter, and wraps the official TLS transport in the evaluation-only gate.
No retry, recovery request, second request, response body, or credential is
ever written to stdout or the receipt.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import httpx

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.evaluation.candidate_provider_close_wakeup_observation import (  # noqa: E402
    CandidateCloseWakeObservation,
    CandidateCloseWakeObservationError,
    observe_candidate_session,
)
from app.evaluation.candidate_recovery_diagnostic_real import (  # noqa: E402
    BASE_URL,
    MODEL,
    _candidate_request,
    _load_environment,
    _load_frozen_context,
)
from app.evaluation.candidate_transport_gate import GateTransport  # noqa: E402
from app.evaluation.candidate_transport_gate_real import (  # noqa: E402
    CandidateRealTransportGateError,
    REAL_TRANSPORT_GATE_PHASES,
    build_real_transport_gate_receipt,
    default_transport_metrics,
    safe_child_observation,
    write_real_transport_gate_receipt,
)
from app.providers.config import load_zhipu_settings  # noqa: E402
from app.providers.response_recovery_contract import (  # noqa: E402
    GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1,
)
from app.providers.zhipu import ZhipuProvider  # noqa: E402
from openai import OpenAI  # noqa: E402


DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_candidate_transport_gate_real_rq215_v1.json"
)
DEFAULT_PHASE = "before_first_event"
DEFAULT_DEADLINE_S = 30.0
DEFAULT_INITIAL_READ_TIMEOUT_S = 0.5
DEFAULT_CANCEL_TIMEOUT_S = 2.0
DEFAULT_READER_GRACE_S = 1.0


def _safe_code(code: str, fallback: str = "child_probe_failed") -> str:
    if isinstance(code, str) and code and all(
        character.islower() or character.isdigit() or character in "_.-"
        for character in code
    ) and code[0].islower():
        return code[:96]
    return fallback


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
        raise CandidateRealTransportGateError("head_sha_unavailable", "identity") from None
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise CandidateRealTransportGateError("head_sha_invalid", "identity")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one bounded, candidate-only GLM-5.3 real HTTPS transport-gate "
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
    parser.add_argument("--observer-code-sha")
    parser.add_argument("--input-plan-sha")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--phase",
        choices=sorted(REAL_TRANSPORT_GATE_PHASES),
        default=DEFAULT_PHASE,
    )
    parser.add_argument(
        "--process-deadline-s",
        type=float,
        default=DEFAULT_DEADLINE_S,
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
    parser.add_argument("--metadata-path", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    return parser


def _write_metadata(path: Path, value: dict[str, object]) -> None:
    """Atomically write only the allow-listed child control projection."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(temporary, flags | getattr(os, "O_BINARY", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if fd != -1:
            os.close(fd)
    os.replace(temporary, path)


def _child_main(args: argparse.Namespace) -> int:
    """Run one explicit adapter session and persist safe child metadata."""

    if args.confirm_real_call is not True:
        if args.metadata_path:
            _write_metadata(
                args.metadata_path,
                {
                    "observation": safe_child_observation("confirmation_required"),
                    "transport": default_transport_metrics(),
                    "provider_call_count": 0,
                },
            )
        return 2

    gate: GateTransport | None = None
    client: OpenAI | None = None
    http_client: httpx.Client | None = None
    calls = 0
    observation: CandidateCloseWakeObservation | dict[str, object] | None = None
    transport_metrics: dict[str, object] = default_transport_metrics()
    error_code: str | None = None
    try:
        root = args.repository_root.resolve()
        context = _load_frozen_context(root)
        environment = _load_environment(args.env_file)
        settings = load_zhipu_settings(environment)
        if settings.model.strip().lower() != MODEL:
            raise CandidateRealTransportGateError("candidate_model_mismatch", "identity")
        if settings.base_url.rstrip("/") != BASE_URL.rstrip("/"):
            raise CandidateRealTransportGateError("candidate_endpoint_mismatch", "identity")
        if not settings.api_key.strip():
            raise CandidateRealTransportGateError("candidate_key_missing", "configuration")
        profile = GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1

        # ``HTTPTransport(retries=0)`` and OpenAI ``max_retries=0`` make the
        # one-request budget explicit at both retry layers.  Keep HTTPX's
        # An explicit transport bypasses HTTPX's automatic environment-proxy
        # selection, so carry the existing HTTPS/ALL proxy setting into the
        # wrapped transport without printing or persisting its value.  The
        # gate still counts and bounds the provider request itself.
        proxy = environment.get("HTTPS_PROXY") or environment.get("https_proxy")
        proxy = proxy or environment.get("ALL_PROXY") or environment.get("all_proxy")
        inner_transport = httpx.HTTPTransport(proxy=proxy or None, retries=0)
        gate = GateTransport(inner_transport, phase=args.phase)
        http_client = httpx.Client(
            transport=gate,
            timeout=profile.transport_timeout_s,
            follow_redirects=False,
            trust_env=False,
        )
        client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            http_client=http_client,
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

        def session_factory(
            supplied_request: Any = None,
            *,
            include_usage_tail: bool = False,
        ):
            nonlocal calls
            if calls != 0 or supplied_request is not request:
                raise CandidateRealTransportGateError("real_call_budget_exceeded", "budget")
            if include_usage_tail is not True:
                raise CandidateRealTransportGateError("usage_tail_required", "request")
            calls = 1
            return adapter.stream_session(supplied_request, include_usage_tail=True)

        observation = observe_candidate_session(
            session_factory,
            request=request,
            initial_read_timeout_s=args.initial_read_timeout_s,
            cancel_timeout_s=args.cancel_timeout_s,
            reader_grace_s=args.reader_grace_s,
        )
    except CandidateRealTransportGateError as error:
        error_code = error.code
        observation = safe_child_observation(error_code)
    except CandidateCloseWakeObservationError as error:
        error_code = error.code
        observation = safe_child_observation(error_code)
    except Exception:
        # Do not retain SDK/provider exception text or response material.
        error_code = "child_probe_failed"
        observation = safe_child_observation(error_code)
    finally:
        if gate is not None:
            transport_metrics = gate.metrics.as_dict()
        # Closing the client after the observer has projected its state makes
        # the transport lifecycle visible while retaining no response data.
        for resource in (client, http_client):
            if resource is None:
                continue
            try:
                resource.close()
            except Exception:
                if error_code is None:
                    error_code = "client_close_failed"
        if gate is not None:
            transport_metrics = gate.metrics.as_dict()
        if observation is None:
            observation = safe_child_observation(error_code or "child_probe_failed")
        if args.metadata_path:
            _write_metadata(
                args.metadata_path,
                {
                    "observation": (
                        observation.as_dict()
                        if isinstance(observation, CandidateCloseWakeObservation)
                        else observation
                    ),
                    "transport": transport_metrics,
                    "provider_call_count": calls,
                },
            )
    return 0 if error_code is None else 2


def _load_metadata(path: Path) -> tuple[dict[str, object], dict[str, object], int]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return safe_child_observation("child_metadata_invalid"), default_transport_metrics(), 0
    if not isinstance(payload, dict):
        return safe_child_observation("child_metadata_invalid"), default_transport_metrics(), 0
    observation = payload.get("observation")
    transport = payload.get("transport")
    calls = payload.get("provider_call_count")
    if not isinstance(observation, dict) or not isinstance(transport, dict):
        return safe_child_observation("child_metadata_invalid"), default_transport_metrics(), 0
    if isinstance(calls, bool) or not isinstance(calls, int) or calls not in {0, 1}:
        return safe_child_observation("child_metadata_invalid"), default_transport_metrics(), 0
    return observation, transport, calls


def _terminate(process: subprocess.Popen[bytes]) -> bool:
    try:
        process.terminate()
    except Exception:
        pass
    try:
        process.wait(timeout=1.0)
        return True
    except Exception:
        try:
            process.kill()
        except Exception:
            pass
        try:
            process.wait(timeout=1.0)
        except Exception:
            return False
        return True


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.child:
        return _child_main(args)
    if args.confirm_real_call is not True:
        print("candidate-real-transport-gate-error=real_call_confirmation_required", file=sys.stderr)
        return 2
    if not 0 < args.process_deadline_s <= DEFAULT_DEADLINE_S:
        print("candidate-real-transport-gate-error=deadline_invalid", file=sys.stderr)
        return 2
    root = args.repository_root.resolve()
    try:
        implementation_sha = args.implementation_sha or _head_sha(root)
        observer_code_sha = args.observer_code_sha or implementation_sha
        input_plan_sha = args.input_plan_sha or implementation_sha
        output = args.output if args.output.is_absolute() else root / args.output
        results_root = root / "data/evaluation/results/provider_capabilities"
        if output.exists() or output.is_symlink():
            raise FileExistsError("real transport-gate evidence is immutable")
        temp_root = Path(tempfile.mkdtemp(prefix="rq215-transport-gate-"))
        metadata_path = temp_root / "child-metadata.json"
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--child",
            "--confirm-real-call",
            "--repository-root",
            str(root),
            "--implementation-sha",
            implementation_sha,
            "--observer-code-sha",
            observer_code_sha,
            "--input-plan-sha",
            input_plan_sha,
            "--phase",
            args.phase,
            "--process-deadline-s",
            str(args.process_deadline_s),
            "--initial-read-timeout-s",
            str(args.initial_read_timeout_s),
            "--cancel-timeout-s",
            str(args.cancel_timeout_s),
            "--reader-grace-s",
            str(args.reader_grace_s),
            "--metadata-path",
            str(metadata_path),
        ]
        if args.env_file is not None:
            command.extend(["--env-file", str(args.env_file.resolve())])
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(root),
            creationflags=(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0),
            start_new_session=(os.name != "nt"),
        )
        timed_out = False
        try:
            process.wait(timeout=args.process_deadline_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate(process)
        observation_raw, transport_raw, calls = _load_metadata(metadata_path)
        if timed_out:
            observation_raw = safe_child_observation("child_timeout", terminated=True)
        receipt = build_real_transport_gate_receipt(
            implementation_sha=implementation_sha,
            observer_code_sha=observer_code_sha,
            input_plan_sha=input_plan_sha,
            gate_phase=args.phase,
            process_deadline_ms=int(round(args.process_deadline_s * 1000)),
            observation=observation_raw,
            metrics=transport_raw,
            provider_call_count=calls,
        )
        written = write_real_transport_gate_receipt(
            output,
            receipt,
            results_root=results_root,
        )
    except (CandidateRealTransportGateError, CandidateCloseWakeObservationError) as error:
        print(f"candidate-real-transport-gate-error={error.code}", file=sys.stderr)
        return 2
    except FileExistsError:
        print("candidate-real-transport-gate-error=evidence_exists", file=sys.stderr)
        return 2
    finally:
        if "temp_root" in locals():
            shutil.rmtree(temp_root, ignore_errors=True)
    print(
        "provider=zhipu model=glm-5.3-flash phase=%s state=%s calls=%d "
        "transport_requests=%s gate_entered=%s reader_woke=%s conclusion=%s output=%s"
        % (
            receipt.gate_phase,
            receipt.observation["observation_state"],
            receipt.provider_call_count,
            receipt.transport["transport_request_count"],
            receipt.transport["gate_entered"],
            receipt.observation["reader_woke"],
            receipt.conclusion,
            written,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
