from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest

from app.providers.capabilities import ProviderCapabilities
from app.providers.errors import ProviderAuthenticationError
from app.providers.models import ChatRequest, ChatResponse, TokenUsage, ToolCall
from scripts.run_deepseek_domain_heldout import (
    DeepSeekDomainCliOptions,
    run_cli,
)


SOURCE_ROOT = Path(__file__).resolve().parents[1]
DATASET_REL = Path("data/evaluation/domain_e2e_v2_secure_held_out_cases.json")
SNAPSHOT_REL = Path(
    "data/evaluation/contracts/recent_form_prompt_context_v1_2.json"
)
PLAN_REL = Path(
    "data/evaluation/deepseek_v4_pro_domain_adoption_v2_input_plan.json"
)
PROTOCOL_REL = Path(
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_adapter_protocol.json"
)
REJECTED_REL = Path(
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_domain_heldout.json"
)
OUTPUT_REL = Path(
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_domain_adoption_v2.json"
)


def _copy_inputs(root: Path) -> None:
    for relative in (
        DATASET_REL,
        SNAPSHOT_REL,
        PLAN_REL,
        PROTOCOL_REL,
        REJECTED_REL,
        Path("examples/fixtures/player_summary_domain_adoption_v2.json"),
        Path("examples/fixtures/deterministic_report_domain_adoption_v2.md"),
    ):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((SOURCE_ROOT / relative).read_bytes())
    for directory in (Path("skills"), Path("data/rag_docs")):
        for source in (SOURCE_ROOT / directory).rglob("*"):
            if not source.is_file():
                continue
            relative = source.relative_to(SOURCE_ROOT)
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())


def _options() -> DeepSeekDomainCliOptions:
    return DeepSeekDomainCliOptions(
        confirm_real_call=True,
        confirm_public_ci_success=True,
        public_ci_sha="0" * 40,
        dataset=DATASET_REL,
        snapshot=SNAPSHOT_REL,
        input_plan=PLAN_REL,
        protocol_result=PROTOCOL_REL,
        rejected_domain_result=REJECTED_REL,
        output=OUTPUT_REL,
        runs_root=Path("data/evaluation/runs/test_domain"),
    )


def test_preflight_failure_never_loads_environment_or_provider(tmp_path):
    calls: list[str] = []

    def fail_preflight(**kwargs):
        calls.append("preflight")
        raise RuntimeError("controlled preflight failure")

    with pytest.raises(RuntimeError, match="preflight"):
        run_cli(
            _options(),
            repository_root=tmp_path,
            preflight_runner=fail_preflight,
            environment_loader=lambda root: calls.append("environment"),
            provider_factory=lambda settings: calls.append("provider"),
        )

    assert calls == ["preflight"]
    assert not (tmp_path / OUTPUT_REL).exists()


def test_existing_output_fails_before_preflight_or_environment(tmp_path):
    output = tmp_path / OUTPUT_REL
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("reserved", encoding="utf-8")
    calls: list[str] = []

    with pytest.raises(FileExistsError, match="immutable"):
        run_cli(
            _options(),
            repository_root=tmp_path,
            preflight_runner=lambda **kwargs: calls.append("preflight"),
            environment_loader=lambda root: calls.append("environment"),
            provider_factory=lambda settings: calls.append("provider"),
        )

    assert calls == []


def test_output_is_reserved_before_environment_and_provider_creation(tmp_path):
    _copy_inputs(tmp_path)
    calls: list[str] = []

    def environment(root):
        calls.append("environment")
        assert (tmp_path / OUTPUT_REL).exists()
        return {"DEEPSEEK_API_KEY": "test-only-secret"}

    def provider_factory(settings):
        calls.append("provider")
        raise RuntimeError("controlled provider construction stop")

    with pytest.raises(RuntimeError, match="construction"):
        run_cli(
            _options(),
            repository_root=tmp_path,
            environment_loader=environment,
            provider_factory=provider_factory,
            code_sha_reader=lambda root: calls.append("preflight") or "0" * 40,
        )

    assert calls == ["preflight", "environment", "provider"]
    assert (tmp_path / OUTPUT_REL).read_bytes() == b""


def test_protocol_byte_drift_fails_before_environment_or_reservation(tmp_path):
    _copy_inputs(tmp_path)
    protocol_path = tmp_path / PROTOCOL_REL
    protocol_path.write_bytes(protocol_path.read_bytes() + b"\n")
    calls: list[str] = []

    with pytest.raises(ValueError, match="historical protocol bytes"):
        run_cli(
            _options(),
            repository_root=tmp_path,
            environment_loader=lambda root: calls.append("environment"),
            provider_factory=lambda settings: calls.append("provider"),
            code_sha_reader=lambda root: "0" * 40,
        )

    assert calls == []
    assert not (tmp_path / OUTPUT_REL).exists()


@dataclass
class OfflineDeepSeekProvider:
    provider_name: str = "deepseek"
    model_name: str = "deepseek-v4-pro"
    capabilities: ProviderCapabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )
    requests: list[ChatRequest] = field(default_factory=list)

    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        if request.response_contract is not None:
            return self._text(
                json.dumps(
                    {
                        "score": 95,
                        "verdict": "pass",
                        "issues": [],
                        "passed_checks": ["facts", "citations", "security"],
                        "summary": "offline production assembly pass",
                    },
                    ensure_ascii=False,
                )
            )
        if any(message.role.value == "tool" for message in request.messages):
            return self._text("# RiftCoach 复盘\n\n谨慎训练建议 [K1]。")
        return ChatResponse(
            content=None,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="tool_calls",
            tool_calls=(
                ToolCall(
                    id=f"offline-tool-{len(self.requests)}",
                    name="knowledge.search",
                    arguments={"query": "早期死亡", "top_k": 2},
                ),
            ),
            usage=TokenUsage(input_tokens=10, output_tokens=5),
        )

    def _text(self, content: str) -> ChatResponse:
        return ChatResponse(
            content=content,
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="stop",
            usage=TokenUsage(input_tokens=10, output_tokens=10),
        )


@dataclass
class AuthenticationFailingProvider(OfflineDeepSeekProvider):
    def chat(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        raise ProviderAuthenticationError(
            provider=self.provider_name,
            code="authentication_failed",
        )


def test_offline_provider_proves_complete_cli_assembly_without_a_real_key(tmp_path):
    _copy_inputs(tmp_path)
    provider = OfflineDeepSeekProvider()
    record = run_cli(
        _options(),
        repository_root=tmp_path,
        environment_loader=lambda root: {
            "DEEPSEEK_API_KEY": "test-only-secret",
        },
        provider_factory=lambda settings: provider,
        code_sha_reader=lambda root: "0" * 40,
    )

    assert record.admitted is True
    assert record.domain_result.domain_calls_used == 9
    assert record.held_out_executed is True
    assert len(provider.requests) == 9
    serialized = (tmp_path / OUTPUT_REL).read_text(encoding="utf-8")
    assert "test-only-secret" not in serialized
    assert "SEASTAR_GOLD_742" not in serialized
    assert "LANTERN_MOSS_913" not in serialized


def test_prepare_only_never_loads_environment_provider_or_creates_output(tmp_path):
    _copy_inputs(tmp_path)
    calls: list[str] = []
    options = replace(
        _options(),
        confirm_real_call=False,
        prepare_only=True,
    )

    admission = run_cli(
        options,
        repository_root=tmp_path,
        environment_loader=lambda root: calls.append("environment"),
        provider_factory=lambda settings: calls.append("provider"),
        code_sha_reader=lambda root: calls.append("code_sha") or "0" * 40,
    )

    assert admission.external_provider_calls == 0
    assert admission.held_out_executed is False
    assert admission.provider_construction_authorized is False
    assert calls == ["code_sha"]
    assert not (tmp_path / OUTPUT_REL).exists()


def test_fresh_cli_preserves_first_error_stop_and_sanitized_immutable_result(
    tmp_path,
):
    _copy_inputs(tmp_path)
    provider = AuthenticationFailingProvider()

    record = run_cli(
        _options(),
        repository_root=tmp_path,
        environment_loader=lambda root: {
            "DEEPSEEK_API_KEY": "never-persist-this-secret",
        },
        provider_factory=lambda settings: provider,
        code_sha_reader=lambda root: "0" * 40,
    )

    assert len(provider.requests) == 1
    assert record.admitted is False
    assert record.domain_result.domain_calls_used == 1
    assert tuple(row.status for row in record.domain_result.cases) == (
        "executed",
        "skipped",
        "skipped",
    )
    serialized = (tmp_path / OUTPUT_REL).read_text(encoding="utf-8")
    assert "never-persist-this-secret" not in serialized
    assert "authentication_failed" in serialized

    with pytest.raises(FileExistsError, match="immutable"):
        run_cli(
            _options(),
            repository_root=tmp_path,
            code_sha_reader=lambda root: "0" * 40,
        )
