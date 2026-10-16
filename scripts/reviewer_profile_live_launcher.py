"""Controlled live entry point for the reviewer Responses transport.

This module deliberately has a small surface.  It performs the local, human
supplied preflight that the offline batch controller cannot perform, then calls
the existing :func:`reviewer_responses_process.run_once` exactly once.  The API
key is read interactively and is passed only through ``run_once``'s private
stdin protocol; it is never an argument, environment variable, or evidence
file.  A successful transport result is still not a semantic qualification.

The preflight is intentionally assertion based for CI and network state.  It
does not contact a CI service or a provider (there is no network probe here),
so the operator must supply the exact green-CI identity and the approved local
route/profile.  Mismatches fail closed before a run directory is created.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import getpass
import json
import re
from pathlib import Path
import subprocess
import sys
from typing import Callable, Mapping

from scripts import reviewer_responses_process
from scripts.reviewer_responses_transport import Profile


ROOT = Path(__file__).resolve().parents[1]
CI_RUN_RE = re.compile(r"[0-9]{1,32}\Z")
HEX40_RE = re.compile(r"[0-9a-f]{40}\Z")
NETWORK_PROFILE = "direct-no-proxy"
MODEL_PROFILE = "responses:gpt-6.1-sol:high:32768:no-retry"
MAX_TIMEOUT_S = 300


class LiveLaunchError(ValueError):
    """Fixed public failure code; never contains private input or OS text."""

    def __init__(self, code: str):
        if not isinstance(code, str) or not re.fullmatch(r"[a-z][a-z0-9_]{2,80}", code):
            code = "live_launch_failed"
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class LivePreflight:
    """Operator supplied, non-secret gate for one live request.

    ``operator`` is a create-only output directory.  It is not allowed under
    ``data/runs`` because the existing research-run namespace is frozen.  The
    CI and network fields are local assertions: this launcher does not call a
    remote service to verify them.
    """

    group: str
    operator: Path
    primary: str
    independent: str
    expected_head: str
    ci_run: str
    ci_head: str
    ci_status: str
    network_profile: str | None = None
    network_ready: bool | None = None
    model_profile: str | None = None
    # These are executable/source identities, not paths inferred from a
    # project name.  A live caller must bind both explicitly.
    python_path: Path | str | None = None
    codex_executable: Path | str | None = None
    ci_proof: Path | str | None = None


def _fixed_path(
    value: Path | str,
    *,
    code: str,
    allow_symlink: bool = False,
) -> Path:
    try:
        path = Path(value)
        if not path.is_absolute():
            raise LiveLaunchError(code)
        resolved = path.resolve()
        if not allow_symlink and resolved != path:
            raise LiveLaunchError(code)
        return resolved if allow_symlink else path
    except LiveLaunchError:
        raise
    except (OSError, TypeError, ValueError):
        raise LiveLaunchError(code) from None


def _git_head() -> str:
    """Read the local checkout identity without contacting a remote."""
    try:
        value = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except Exception:
        raise LiveLaunchError("head_unavailable") from None
    if not HEX40_RE.fullmatch(value):
        raise LiveLaunchError("head_unavailable")
    return value


def _git_is_clean() -> bool:
    """Return whether the checkout has no tracked or untracked changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        raise LiveLaunchError("clean_head_unavailable") from None
    return result.stdout == ""


def _identity_file(
    value: Path | str | None,
    *,
    code: str,
    allow_symlink: bool = False,
) -> Path:
    """Validate an absolute identity file and return its resolved target.

    The Linux runner commonly exposes ``sys.executable`` through a symlink
    (for example ``/usr/local/bin/python``).  That is still the same
    executable identity once resolved, while CI receipts and operator files
    must remain direct paths so a redirected evidence tree cannot be accepted.
    """
    if value is None:
        raise LiveLaunchError(code)
    path = _fixed_path(value, code=code, allow_symlink=allow_symlink)
    try:
        resolved = path.resolve()
        if (not allow_symlink and resolved != path) or not resolved.is_file():
            raise LiveLaunchError(code)
    except LiveLaunchError:
        raise
    except OSError:
        raise LiveLaunchError(code) from None
    return resolved


def _check_ci_proof(path: Path, *, expected_head: str, expected_run: str) -> None:
    """Read a local, immutable CI receipt; never query a remote service."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise LiveLaunchError("ci_proof_invalid") from None
    if not isinstance(value, dict):
        raise LiveLaunchError("ci_proof_binding")
    head = value.get("head", value.get("headSha"))
    run = value.get("run", value.get("ci_run"))
    if head != expected_head or str(run) != expected_run:
        raise LiveLaunchError("ci_proof_binding")
    if value.get("status") != "completed" or value.get("conclusion") != "success":
        raise LiveLaunchError("ci_not_green")


def _validate_no_existing_artifacts(operator: Path) -> None:
    """Reject runs, claims and partially-created batches before key input."""
    if operator.is_relative_to(ROOT / "data" / "runs"):
        raise LiveLaunchError("frozen_run_namespace")
    # ``run_once`` uses mkdir(exist_ok=False).  Checking first gives a stable
    # public code and, more importantly, prevents reusing a stale claim.
    if operator.exists():
        raise LiveLaunchError("existing_run_or_incomplete_batch")
    # A pre-existing path at this point can only be a redirected parent.  Walk
    # the nearest existing ancestor and reject symlink/junction components so a
    # run cannot be redirected into an old claims/checkpoints tree later.
    current = operator.parent
    while not current.exists():
        current = current.parent
    try:
        if current.resolve() != current:
            raise LiveLaunchError("operator_redirected")
    except OSError:
        raise LiveLaunchError("operator_unavailable") from None


def validate_preflight(
    preflight: LivePreflight,
    *,
    current_head: str | None = None,
    git_clean: bool | None = None,
) -> LivePreflight:
    """Validate all non-secret launch gates and return a normalized copy.

    No socket, provider, CI, filesystem write, or key read occurs here.
    ``current_head`` exists for offline tests; production callers leave it
    unset so the checkout's exact local HEAD is read.
    """
    if not isinstance(preflight, LivePreflight):
        raise LiveLaunchError("preflight_required")
    try:
        profile = Profile(group=preflight.group)
    except Exception:
        raise LiveLaunchError("group_invalid") from None
    del profile  # construction is the canonical supported-group check
    operator = _fixed_path(preflight.operator, code="operator_path_invalid")
    if not isinstance(preflight.primary, str) or not preflight.primary.strip():
        raise LiveLaunchError("primary_required")
    if not isinstance(preflight.independent, str) or not preflight.independent.strip():
        raise LiveLaunchError("independent_required")
    if preflight.primary == preflight.independent:
        raise LiveLaunchError("review_principals_must_differ")
    if not isinstance(preflight.expected_head, str) or not HEX40_RE.fullmatch(preflight.expected_head):
        raise LiveLaunchError("head_binding_invalid")
    actual = current_head if current_head is not None else _git_head()
    if actual != preflight.expected_head:
        raise LiveLaunchError("head_mismatch")
    clean = git_clean if git_clean is not None else _git_is_clean()
    if clean is not True:
        raise LiveLaunchError("dirty_checkout")
    if not isinstance(preflight.ci_run, str) or not CI_RUN_RE.fullmatch(preflight.ci_run):
        raise LiveLaunchError("ci_run_invalid")
    if preflight.ci_head != preflight.expected_head:
        raise LiveLaunchError("ci_head_mismatch")
    if preflight.ci_status != "success":
        raise LiveLaunchError("ci_not_green")
    if preflight.network_profile != NETWORK_PROFILE or preflight.network_ready is not True:
        raise LiveLaunchError("network_preflight_failed")
    if preflight.model_profile != MODEL_PROFILE:
        raise LiveLaunchError("model_profile_mismatch")
    python_path = _identity_file(
        preflight.python_path,
        code="python_path_required",
        allow_symlink=True,
    )
    try:
        if python_path != Path(sys.executable).resolve():
            raise LiveLaunchError("python_path_mismatch")
    except OSError:
        raise LiveLaunchError("python_path_mismatch") from None
    _identity_file(preflight.codex_executable, code="codex_executable_required")
    ci_proof = _identity_file(preflight.ci_proof, code="ci_proof_required")
    _check_ci_proof(ci_proof, expected_head=preflight.expected_head, expected_run=preflight.ci_run)
    _validate_no_existing_artifacts(operator)
    return LivePreflight(
        group=preflight.group,
        operator=operator,
        primary=preflight.primary.strip(),
        independent=preflight.independent.strip(),
        expected_head=preflight.expected_head,
        ci_run=preflight.ci_run,
        ci_head=preflight.ci_head,
        ci_status=preflight.ci_status,
        network_profile=preflight.network_profile,
        network_ready=True,
        model_profile=preflight.model_profile,
        python_path=python_path,
        codex_executable=_identity_file(preflight.codex_executable, code="codex_executable_required"),
        ci_proof=ci_proof,
    )


def _read_business(path: Path) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise LiveLaunchError("business_unreadable") from None
    if not isinstance(value, dict):
        raise LiveLaunchError("business_invalid")
    return value


def run_live_once(
    business: Mapping[str, object],
    preflight: LivePreflight,
    *,
    api_key: str | None = None,
    read_key: Callable[[str], str] = getpass.getpass,
    sender: Callable[..., dict] = reviewer_responses_process.run_once,
    current_head: str | None = None,
    git_clean: bool | None = None,
) -> dict:
    """Run one controlled call after all local gates pass.

    ``api_key`` is provided for embedding/tests only.  The command-line entry
    point leaves it ``None`` and obtains it with ``getpass``.  In either case
    it is passed as a normal ``run_once`` keyword, which serializes it solely
    over the worker's stdin pipe; the launcher never stores or prints it.
    """
    checked = validate_preflight(preflight, current_head=current_head, git_clean=git_clean)
    if not isinstance(business, dict):
        raise LiveLaunchError("business_invalid")
    if api_key is None:
        try:
            api_key = read_key("Third-party API key (hidden): ")
        except (KeyboardInterrupt, EOFError):
            raise LiveLaunchError("api_key_cancelled") from None
        except Exception:
            raise LiveLaunchError("api_key_read_failed") from None
    if not isinstance(api_key, str) or not api_key:
        raise LiveLaunchError("api_key_required")
    try:
        result = sender(
            business,
            profile=Profile(group=checked.group),
            api_key=api_key,
            directory=checked.operator,
            timeout_s=MAX_TIMEOUT_S,
        )
    except (KeyboardInterrupt, LiveLaunchError):
        raise LiveLaunchError("live_call_cancelled") from None
    except Exception:
        # Do not expose exception text: providers and SDKs may echo credentials.
        raise LiveLaunchError("live_call_failed") from None
    finally:
        # Drop the local binding as soon as the worker has consumed stdin.
        api_key = None
    if not isinstance(result, dict):
        raise LiveLaunchError("live_receipt_invalid")
    # Existing run_once deliberately leaves qualification/publication closed;
    # reject a sender that tries to bypass that boundary.
    if result.get("qualified") is not False or result.get("publication_allowed", False) is not False:
        raise LiveLaunchError("qualification_boundary_violation")
    # ``run_once`` predates this launcher and omits the publication field from
    # its receipt.  Normalize the public return only; no evidence file is
    # rewritten and the value is always the closed boundary.
    result = dict(result, publication_allowed=False, batch_bound=False)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Controlled single reviewer Responses call")
    parser.add_argument("--business", required=True, type=Path)
    parser.add_argument("--operator", required=True, type=Path)
    parser.add_argument("--group", required=True)
    parser.add_argument("--primary", required=True)
    parser.add_argument("--independent", required=True)
    parser.add_argument("--head", required=True, dest="expected_head")
    parser.add_argument("--ci-run", required=True)
    parser.add_argument("--ci-head", required=True)
    parser.add_argument("--ci-status", required=True)
    parser.add_argument("--network-profile", required=True)
    parser.add_argument("--network-ready", required=True, action="store_true")
    parser.add_argument("--model-profile", required=True)
    parser.add_argument("--python", required=True, dest="python_path", type=Path)
    parser.add_argument("--codex", required=True, dest="codex_executable", type=Path)
    parser.add_argument("--ci-proof", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        preflight = LivePreflight(
            group=args.group,
            operator=args.operator,
            primary=args.primary,
            independent=args.independent,
            expected_head=args.expected_head,
            ci_run=args.ci_run,
            ci_head=args.ci_head,
            ci_status=args.ci_status,
            network_profile=args.network_profile,
            network_ready=args.network_ready,
            model_profile=args.model_profile,
            python_path=args.python_path,
            codex_executable=args.codex_executable,
            ci_proof=args.ci_proof,
        )
        result = run_live_once(_read_business(args.business), preflight)
    except LiveLaunchError as error:
        print(error.code, file=sys.stderr)
        return 2
    # Only fixed public fields are printed; no request body or provider text.
    print(json.dumps({
        "ok": result.get("ok") is True,
        "code": result.get("code"),
        "batch_bound": False,
        "qualified": False,
        "publication_allowed": False,
    },
                     ensure_ascii=True, sort_keys=True))
    return 0 if result.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())

