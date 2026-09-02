"""One explicitly authorized real-call runner for the GLM-5.3 candidate.

The versioned diagnostic in :mod:`candidate_recovery_diagnostic_v2` is kept
provider-neutral and deliberately has no SDK or credential dependency.  This
module is the narrow composition seam around it: it loads one frozen,
held-out context, constructs the existing explicit Zhipu neutral stream
adapter, and permits exactly one primary request.  The candidate activation
gate remains disabled, so a candidate-shaped response is recorded and never
followed by a recovery request.

This is evaluation code, not product Runtime code.  It does not register a
Provider, change the default model, enable ``capabilities.streaming``, invoke
the AgentLoop/ToolRuntime, or write a product trace.  Only the body-free v2
receipt is persisted.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from openai import OpenAI

from app.agent.context import ContextBuilderV1
from app.evaluation.domain_e2e import (
    DomainDatasetRole,
    DomainEvaluationDataset,
    validate_domain_dataset_usage,
)
from app.evaluation.prompt_context_identity import (
    build_prompt_context_snapshot_for_cases,
    case_context_sha256,
)
from app.evaluation.provider_domain_experiment import DomainCaseExecutionPlan
from app.evaluation.provider_domain_plan import (
    DomainCaseInputPlanArtifact,
    LoadedDomainCaseInputPlan,
)
from app.evaluation.provider_domain_production import ProductionDomainCaseExecutor
from app.providers.config import load_zhipu_settings
from app.providers.errors import ProviderError
from app.providers.models import ChatMessage, ChatRequest, MessageRole, ToolChoiceMode
from app.providers.response_completion_policy import (
    GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1,
    ResponseRequestContext,
)
from app.providers.response_recovery_contract import (
    GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1,
)
from app.providers.stream_adapter_contract import ProviderStreamEvent, StreamAdapterError
from app.providers.zhipu import ZhipuProvider

from .candidate_recovery_diagnostic_v2 import (
    CandidateRecoveryDiagnostic,
    CandidateRecoveryDiagnosticReceipt,
    CandidateRecoveryRunSpec,
    WrittenDiagnosticReceipt,
    write_candidate_recovery_receipt,
)
from .candidate_stream_contract import (
    CANDIDATE_MODEL,
    CANDIDATE_POLICY_ID,
    CANDIDATE_POLICY_VERSION,
    CANDIDATE_PROVIDER_ID,
    CANDIDATE_RUNTIME_PROFILE_ID,
    CANDIDATE_RUNTIME_PROFILE_VERSION,
    CandidateBoundaryContractError,
    CandidateRuntimeBinding,
    CandidateStreamSession,
    CandidateStreamTransport,
    CandidateTransportError,
    CandidateZhipuStreamTransport,
    PRIMARY_CANDIDATE_BINDING,
)


PROVIDER_ID = CANDIDATE_PROVIDER_ID
MODEL = CANDIDATE_MODEL
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
CASE_ID = "flash_gate_baseline_01"
PLAN_RELATIVE_PATH = "data/evaluation/glm53_flash_domain_adoption_v1_input_plan.json"
DATASET_RELATIVE_PATH = "data/evaluation/glm53_flash_domain_adoption_v1_cases.json"
PLAYER_SUMMARY_RELATIVE_PATH = "examples/fixtures/player_summary_glm53_flash_domain_v1.json"
DETERMINISTIC_REPORT_RELATIVE_PATH = "examples/fixtures/deterministic_report_glm53_flash_domain_v1.md"
DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "zhipu_glm53_flash_candidate_recovery_diagnostic_v2_rq207_v1.json"
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")


class CandidateRealCallError(RuntimeError):
    """Safe control-plane error for setup failures before the provider call."""

    def __init__(self, code: str) -> None:
        if not isinstance(code, str) or not _SAFE_CODE.fullmatch(code):
            raise ValueError("real-call error code must be a safe code")
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class FrozenCandidateContext:
    """One validated held-out context; message bodies never leave this object."""

    messages: tuple[ChatMessage, ...] = field(repr=False)
    # The v2 receipt's input_plan_sha is a Git identity. Keep the canonical
    # file-content digest separately for frozen-input verification.
    input_plan_sha: str
    input_plan_content_sha256: str
    prompt_context_snapshot_sha256: str
    case_id: str = CASE_ID

    def __post_init__(self) -> None:
        if not self.messages or not all(
            isinstance(message, ChatMessage) for message in self.messages
        ):
            raise CandidateRealCallError("context_messages_invalid")
        for message in self.messages:
            if message.role not in {MessageRole.SYSTEM, MessageRole.USER}:
                raise CandidateRealCallError("context_role_invalid")
            if message.content is None or not message.content.strip():
                raise CandidateRealCallError("context_content_invalid")
            if message.tool_calls or message.reasoning_content is not None:
                raise CandidateRealCallError("context_body_shape_invalid")
        if not isinstance(self.input_plan_sha, str) or not _GIT_SHA.fullmatch(
            self.input_plan_sha
        ):
            raise CandidateRealCallError("input_plan_sha_invalid")
        for name, value in (
            ("input_plan_content_sha256", self.input_plan_content_sha256),
            ("prompt_context_snapshot_sha256", self.prompt_context_snapshot_sha256),
        ):
            if not isinstance(value, str) or not _SHA256.fullmatch(value):
                raise CandidateRealCallError(f"{name}_invalid")
        if not isinstance(self.case_id, str) or not re.fullmatch(
            r"^[a-z][a-z0-9_.-]{0,95}$", self.case_id
        ):
            raise CandidateRealCallError("case_id_invalid")


@dataclass(frozen=True, slots=True)
class CandidateRecoveryRealCallReport:
    """Safe result of one real primary attempt and its immutable receipt."""

    receipt: CandidateRecoveryDiagnosticReceipt = field(repr=False)
    written: WrittenDiagnosticReceipt = field(repr=False)
    case_id: str = CASE_ID
    external_calls: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.receipt, CandidateRecoveryDiagnosticReceipt):
            raise TypeError("receipt must be CandidateRecoveryDiagnosticReceipt")
        if not isinstance(self.written, WrittenDiagnosticReceipt):
            raise TypeError("written must be WrittenDiagnosticReceipt")
        if self.case_id != CASE_ID:
            raise CandidateRealCallError("case_id_invalid")
        if self.external_calls != 1:
            raise CandidateRealCallError("real_call_count_invalid")


def run_candidate_recovery_real_call(
    *,
    repository_root: str | Path,
    implementation_sha: str,
    diagnostic_code_sha: str,
    output: str | Path = DEFAULT_OUTPUT,
    env_file: str | Path | None = None,
    confirm_real_call: bool = False,
    client_factory: Callable[..., Any] = OpenAI,
    environment_loader: Callable[[Path | None], Mapping[str, str]] | None = None,
    context_loader: Callable[[Path], FrozenCandidateContext] | None = None,
) -> CandidateRecoveryRealCallReport:
    """Execute exactly one bounded, candidate-only real primary request.

    ``confirm_real_call`` is intentionally a keyword gate.  No client is
    constructed and no credential is read until it is ``True``.  The current
    v2 diagnostic's disabled activation gate prevents a second request even
    when the primary response has the exact candidate ``length`` shape.
    """

    if confirm_real_call is not True:
        raise CandidateRealCallError("real_call_confirmation_required")
    root = Path(repository_root).resolve()
    _validate_git_sha(implementation_sha, "implementation_sha")
    _validate_git_sha(diagnostic_code_sha, "diagnostic_code_sha")
    output_path = _resolve_output_path(root, output)
    if output_path.exists() or output_path.is_symlink():
        raise FileExistsError("candidate diagnostic evidence is immutable")

    context = (context_loader or _load_frozen_context)(root)
    if not isinstance(context, FrozenCandidateContext):
        raise CandidateRealCallError("context_loader_invalid")
    if context.case_id != CASE_ID:
        raise CandidateRealCallError("case_id_mismatch")
    profile = GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1
    policy = GLM53_FLASH_FRESH_RECOVERY_CANDIDATE_V1
    request_context = ResponseRequestContext(
        phase="agent_initial",
        has_response_contract=False,
        has_tools=False,
        has_tool_side_effects=False,
        remaining_timeout_s=profile.agent_timeout_s,
        remaining_token_budget=profile.max_output_tokens,
    )
    run = CandidateRecoveryRunSpec.new(
        implementation_sha=implementation_sha,
        diagnostic_code_sha=diagnostic_code_sha,
        input_plan_sha=context.input_plan_sha,
        context=request_context,
    )
    request = _candidate_request(context.messages)

    load_environment = environment_loader or _load_environment
    try:
        settings = load_zhipu_settings(
            load_environment(Path(env_file) if env_file is not None else None)
        )
    except Exception:
        raise CandidateRealCallError("provider_configuration_invalid") from None
    if (
        settings.model.strip().lower() != MODEL
        or settings.base_url.rstrip("/") != BASE_URL.rstrip("/")
    ):
        raise CandidateRealCallError("candidate_endpoint_mismatch")

    try:
        client = client_factory(
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
    except Exception:
        raise CandidateRealCallError("provider_client_init_failed") from None

    call_count = 0

    def opener(
        *,
        binding: CandidateRuntimeBinding,
        request: ChatRequest,
        max_output_tokens: int,
        timeout_s: float,
        transport_timeout_s: float,
        max_retries: int,
    ) -> CandidateStreamSession:
        nonlocal call_count
        if binding != PRIMARY_CANDIDATE_BINDING:
            raise CandidateTransportError("candidate_attempt_mismatch", "identity")
        if max_retries != 0:
            raise CandidateTransportError("sdk_retries_invalid", "budget")
        if max_output_tokens != profile.max_output_tokens:
            raise CandidateTransportError("candidate_output_cap_mismatch", "budget")
        if timeout_s != profile.agent_timeout_s or transport_timeout_s != profile.transport_timeout_s:
            raise CandidateTransportError("candidate_timeout_mismatch", "budget")
        call_count += 1
        if call_count != 1:
            raise CandidateTransportError("real_call_budget_exceeded", "budget")
        # The real candidate seam opts into the owned/cancellable adapter
        # session. Usage is requested explicitly so a normal terminal frame
        # can be followed by the provider's one Usage-only tail. The legacy
        # lazy generator remains untouched for product/offline callers.
        return adapter.stream_session(request, include_usage_tail=True)

    transport: CandidateStreamTransport = CandidateZhipuStreamTransport(
        opener,
        session_opener=opener,
        runtime_profile=profile,
        policy=policy,
    )
    diagnostic = CandidateRecoveryDiagnostic(run, require_hard_deadline=True)
    try:
        receipt = diagnostic.run_once(request, transport)
    except (GeneratorExit, KeyboardInterrupt, SystemExit):
        # The v2 runner stores a safe interrupted receipt before propagating a
        # control exception.  Preserve it when possible, then let the caller
        # stop rather than converting cancellation into success.
        receipt = diagnostic.last_receipt
        if receipt is None:
            raise
        written = write_candidate_recovery_receipt(output_path, receipt)
        raise
    if call_count != 1:
        raise CandidateRealCallError("real_call_count_invalid")
    written = write_candidate_recovery_receipt(output_path, receipt)
    return CandidateRecoveryRealCallReport(
        receipt=receipt,
        written=written,
        case_id=context.case_id,
        external_calls=call_count,
    )


def _candidate_request(messages: tuple[ChatMessage, ...]) -> ChatRequest:
    return ChatRequest(
        messages=messages,
        tools=(),
        tool_choice=ToolChoiceMode.NONE,
        temperature=GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1.temperature,
        top_p=GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1.top_p,
        max_tokens=GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1.max_output_tokens,
        timeout_s=GLM53_FLASH_FRESH_RECOVERY_RUNTIME_CANDIDATE_V1.agent_timeout_s,
        metadata={
            "provider_id": CANDIDATE_PROVIDER_ID,
            "model": CANDIDATE_MODEL,
            "runtime_profile_id": CANDIDATE_RUNTIME_PROFILE_ID,
            "runtime_profile_version": CANDIDATE_RUNTIME_PROFILE_VERSION,
            "policy_id": CANDIDATE_POLICY_ID,
            "policy_version": CANDIDATE_POLICY_VERSION,
        },
    )


def _safe_provider_events(
    events: Iterable[ProviderStreamEvent],
) -> Iterable[ProviderStreamEvent]:
    """Map provider/adapter failures to body-free candidate transport codes.

    The returned generator owns the adapter iterator.  Keeping that ownership
    explicit is important for a consumer that stops after the first event (or
    for the v2 runner's cancellation path): closing only this outer generator
    must also close the provider iterator and release the vendor stream.
    """

    iterator: Iterator[ProviderStreamEvent] | None = None
    try:
        iterator = iter(events)
        for event in iterator:
            yield event
    except (GeneratorExit, KeyboardInterrupt, SystemExit):
        raise
    except CandidateBoundaryContractError:
        raise
    except ProviderError as error:
        code = error.code if _SAFE_CODE.fullmatch(error.code) else "provider_error"
        raise CandidateTransportError(code, "transport") from None
    except StreamAdapterError as error:
        code = error.code if _SAFE_CODE.fullmatch(error.code) else "stream_adapter_error"
        raise CandidateTransportError(code, "protocol") from None
    except Exception:
        raise CandidateTransportError("stream_read_failed", "read") from None
    finally:
        # Preserve an already active read/control error.  Cleanup errors are
        # deliberately reduced to one safe boundary code and never chained
        # back to an SDK/provider exception or its response body.
        active_error = sys.exc_info()[1]
        close_failed = False
        pending_control: BaseException | None = None
        seen: set[int] = set()
        for resource in (iterator, events):
            if resource is None or id(resource) in seen:
                continue
            seen.add(id(resource))
            try:
                close_method = getattr(resource, "close", None)
            except (GeneratorExit, KeyboardInterrupt, SystemExit) as error:
                close_failed = True
                if active_error is None and pending_control is None:
                    pending_control = error
                continue
            except Exception:
                close_failed = True
                continue
            if callable(close_method):
                try:
                    close_method()
                except (GeneratorExit, KeyboardInterrupt, SystemExit) as error:
                    close_failed = True
                    if active_error is None and pending_control is None:
                        pending_control = error
                except Exception:
                    close_failed = True
                continue

            # The real adapter currently returns a generator, but retaining
            # context-manager cleanup here keeps this boundary safe for an
            # injected iterable with a distinct iterator.
            try:
                exit_method = getattr(resource, "__exit__", None)
            except (GeneratorExit, KeyboardInterrupt, SystemExit) as error:
                close_failed = True
                if active_error is None and pending_control is None:
                    pending_control = error
                continue
            except Exception:
                close_failed = True
                continue
            if callable(exit_method):
                try:
                    exit_method(None, None, None)
                except (GeneratorExit, KeyboardInterrupt, SystemExit) as error:
                    close_failed = True
                    if active_error is None and pending_control is None:
                        pending_control = error
                except Exception:
                    close_failed = True

        if active_error is None:
            if pending_control is not None:
                raise pending_control
            if close_failed:
                raise CandidateTransportError("stream_close_failed", "close") from None


def _load_environment(path: Path | None) -> Mapping[str, str]:
    """Read a dotenv file without mutating process-wide environment state."""

    values: dict[str, str] = {}
    if path is not None:
        if not path.is_file():
            raise CandidateRealCallError("env_file_missing")
        for key, value in dotenv_values(path).items():
            if isinstance(key, str) and isinstance(value, str):
                values[key] = value
    # Process environment has normal override semantics, but the mapping is
    # discarded after settings construction and never enters the receipt.
    values.update({key: value for key, value in os.environ.items()})
    return values


def _load_frozen_context(root: Path) -> FrozenCandidateContext:
    """Load committed held-out bytes while tolerating a CRLF checkout only."""

    plan_raw = _committed_bytes(root, PLAN_RELATIVE_PATH)
    dataset_raw = _committed_bytes(root, DATASET_RELATIVE_PATH)
    summary_raw = _committed_bytes(root, PLAYER_SUMMARY_RELATIVE_PATH)
    report_raw = _committed_bytes(root, DETERMINISTIC_REPORT_RELATIVE_PATH)
    try:
        artifact = DomainCaseInputPlanArtifact.model_validate_json(plan_raw)
        dataset = DomainEvaluationDataset.model_validate_json(dataset_raw)
        player_summary = json.loads(summary_raw)
        deterministic_report = report_raw.decode("utf-8")
    except Exception:
        raise CandidateRealCallError("frozen_input_parse_failed") from None
    try:
        validate_domain_dataset_usage(
            dataset,
            DomainDatasetRole.HELD_OUT,
            confirm_rules_frozen=True,
        )
        if (artifact.dataset_id, artifact.dataset_version) != (
            dataset.dataset_id,
            dataset.dataset_version,
        ) or tuple(row.case_id for row in artifact.cases) != tuple(
            row.case_id for row in dataset.cases
        ):
            raise ValueError
        if artifact.sdk_max_retries != 0 or artifact.max_revisions != 0:
            raise ValueError
        snapshot = build_prompt_context_snapshot_for_cases(
            skills_root=root / "skills",
            player_summary=player_summary,
            deterministic_report=deterministic_report,
            cases=artifact.cases,
            snapshot_id=artifact.prompt_context_snapshot_id,
            evaluation_contract_version="1.1.0",
        )
        if snapshot.snapshot_sha256 != artifact.prompt_context_snapshot_sha256:
            raise ValueError
        expected_case = next(
            row.context_sha256
            for row in artifact.case_context_commitments
            if row.case_id == CASE_ID
        )
        actual_case = case_context_sha256(
            next(row for row in snapshot.case_contexts if row.case_id == CASE_ID)
        )
        if actual_case != expected_case:
            raise ValueError
    except Exception:
        raise CandidateRealCallError("frozen_context_identity_mismatch") from None

    with tempfile.TemporaryDirectory(prefix="riftcoach-candidate-context-") as temp:
        temp_root = Path(temp)
        summary_path = temp_root / "player_summary.json"
        report_path = temp_root / "deterministic_report.md"
        summary_path.write_bytes(summary_raw)
        report_path.write_bytes(report_raw)
        loaded_plan = LoadedDomainCaseInputPlan(
            artifact=artifact,
            execution_plan=DomainCaseExecutionPlan(
                plan_id=artifact.plan_id,
                plan_version=artifact.plan_version,
                plan_sha256=hashlib.sha256(plan_raw).hexdigest(),
                case_ids=tuple(row.case_id for row in artifact.cases),
            ),
            player_summary_path=summary_path,
            deterministic_report_path=report_path,
        )
        try:
            case = artifact.case(CASE_ID)
            executor = ProductionDomainCaseExecutor(
                project_root=root,
                input_plan=loaded_plan,
                runs_root=temp_root / "runs",
                runtime_profile=None,
            )
            execution = executor._build_execution(case)  # noqa: SLF001
            bundle = ContextBuilderV1().build(execution)
        except Exception:
            raise CandidateRealCallError("frozen_context_build_failed") from None
    return FrozenCandidateContext(
        messages=tuple(bundle.messages),
        input_plan_sha=_head_git_sha(root),
        input_plan_content_sha256=hashlib.sha256(plan_raw).hexdigest(),
        prompt_context_snapshot_sha256=artifact.prompt_context_snapshot_sha256
        or ("0" * 64),
        case_id=CASE_ID,
    )


def _committed_bytes(root: Path, relative_path: str) -> bytes:
    path = (root / relative_path).resolve()
    if not path.is_file():
        raise CandidateRealCallError("frozen_input_missing")
    try:
        committed = subprocess.run(
            ["git", "show", f"HEAD:{relative_path}"],
            cwd=root,
            check=True,
            capture_output=True,
            timeout=10,
        ).stdout
    except Exception:
        raise CandidateRealCallError("frozen_input_commit_unavailable") from None
    current = path.read_bytes()
    if current == committed:
        return committed
    if current.replace(b"\r\n", b"\n") == committed:
        return committed
    raise CandidateRealCallError("frozen_input_changed")


def _resolve_output_path(root: Path, value: str | Path) -> Path:
    path = (Path(value) if Path(value).is_absolute() else root / value).resolve()
    allowed = (root / "data/evaluation/results/provider_capabilities").resolve()
    if not path.is_relative_to(allowed) or path.suffix.lower() != ".json":
        raise CandidateRealCallError("output_path_invalid")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _validate_git_sha(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not _GIT_SHA.fullmatch(value):
        raise CandidateRealCallError(f"{field_name}_invalid")


def _head_git_sha(root: Path) -> str:
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
        raise CandidateRealCallError("frozen_input_commit_unavailable") from None
    _validate_git_sha(value, "input_plan_sha")
    return value


__all__ = [
    "BASE_URL",
    "CASE_ID",
    "CandidateRealCallError",
    "CandidateRecoveryRealCallReport",
    "DEFAULT_OUTPUT",
    "FrozenCandidateContext",
    "MODEL",
    "PROVIDER_ID",
    "run_candidate_recovery_real_call",
]
