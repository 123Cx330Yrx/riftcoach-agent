from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.providers.config import (
    ZhipuSettings,
    create_zhipu_provider,
    load_zhipu_settings,
)
from app.providers.errors import ProviderConfigurationError, ProviderResponseError
from app.providers.models import (
    ChatMessage,
    ChatRequest,
    MessageRole,
    ToolSpec,
)
from app.providers.zhipu import ZhipuProvider
from app.providers.zhipu_profiles import (
    ZHIPU_GLM52_MODEL,
    ZHIPU_GLM53_FLASH_MODEL,
    ZHIPU_GLM53_MODEL,
    ZhipuThinkingProfile,
    resolve_zhipu_thinking_profile,
)


def sdk_response(
    *,
    content: str | None = "回答",
    reasoning_content: object | None = None,
    tool_calls: list[object] | None = None,
    finish_reason: str = "stop",
) -> SimpleNamespace:
    return SimpleNamespace(
        id="safe-request-id",
        model=ZHIPU_GLM53_FLASH_MODEL,
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    content=content,
                    reasoning_content=reasoning_content,
                    tool_calls=tool_calls or [],
                ),
            )
        ],
        usage=SimpleNamespace(prompt_tokens=4, completion_tokens=3),
    )


class FakeCompletions:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self.result


class FakeClient:
    def __init__(self, result: object) -> None:
        self.completions = FakeCompletions(result)
        self.chat = SimpleNamespace(completions=self.completions)


def lookup_tool() -> ToolSpec:
    return ToolSpec(
        name="lookup",
        description="查找一条测试信息。",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    )


def test_model_resolution_keeps_legacy_and_adds_flash_profile() -> None:
    legacy = resolve_zhipu_thinking_profile("some-test-model")
    glm52 = resolve_zhipu_thinking_profile(ZHIPU_GLM52_MODEL)
    glm53 = resolve_zhipu_thinking_profile(ZHIPU_GLM53_MODEL)
    flash = resolve_zhipu_thinking_profile(ZHIPU_GLM53_FLASH_MODEL)

    assert legacy.thinking_type == "disabled"
    assert legacy.reasoning_effort is None
    assert legacy.extra_body() == {"thinking": {"type": "disabled"}}
    assert glm52.extra_body() == {"thinking": {"type": "disabled"}}
    assert glm53.extra_body() == {
        "thinking": {"type": "enabled"},
        "reasoning_effort": "low",
    }
    assert flash.profile_id == "glm-5.3-flash-enabled-max-replay"
    assert flash.preserves_reasoning_content is True
    assert flash.extra_body() == {
        "thinking": {"type": "enabled", "clear_thinking": False},
        "reasoning_effort": "max",
    }

    first = flash.extra_body()
    first["thinking"]["type"] = "disabled"
    assert flash.extra_body()["thinking"]["type"] == "enabled"


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "profile_id": "invalid",
            "model": "glm-test",
            "thinking_type": "disabled",
            "reasoning_effort": "low",
        },
        {
            "profile_id": "invalid",
            "model": "glm-test",
            "thinking_type": "enabled",
            "reasoning_effort": None,
        },
        {
            "profile_id": "invalid",
            "model": "glm-test",
            "thinking_type": "disabled",
            "clear_thinking": True,
        },
    ],
)
def test_profile_rejects_unsafe_thinking_combinations(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        ZhipuThinkingProfile(**kwargs)


def test_flash_request_uses_profile_and_retains_reasoning_for_internal_replay() -> None:
    client = FakeClient(
        sdk_response(
            content="  可公开回答  ",
            reasoning_content="不可公开的内部推理",
        )
    )
    provider = ZhipuProvider(client=client, model=ZHIPU_GLM53_FLASH_MODEL)

    response = provider.chat(
        ChatRequest(messages=(ChatMessage(MessageRole.USER, "回答。"),))
    )

    assert response.content == "可公开回答"
    assert response.reasoning_content == "不可公开的内部推理"
    assert provider.profile.profile_id == "glm-5.3-flash-enabled-max-replay"
    assert client.completions.calls[0]["extra_body"] == {
        "thinking": {"type": "enabled", "clear_thinking": False},
        "reasoning_effort": "max",
    }


def test_flash_rejects_non_string_reasoning() -> None:
    with pytest.raises(ProviderResponseError) as caught:
        ZhipuProvider(
            client=FakeClient(
                sdk_response(
                    reasoning_content={"hidden": "state"},
                )
            ),
            model=ZHIPU_GLM53_FLASH_MODEL,
        ).chat(ChatRequest(messages=(ChatMessage(MessageRole.USER, "回答。"),)))
    assert caught.value.code == "unexpected_reasoning_content"


def test_flash_tool_request_keeps_single_call_boundary_and_payload_contract() -> None:
    raw_call = SimpleNamespace(
        id="call-1",
        type="function",
        function=SimpleNamespace(
            name="lookup",
            arguments='{"query":"x"}',
        ),
    )
    client = FakeClient(
        sdk_response(
            content=None,
            tool_calls=[raw_call],
            finish_reason="tool_calls",
        )
    )
    provider = ZhipuProvider(client=client, model=ZHIPU_GLM53_FLASH_MODEL)

    response = provider.chat(
        ChatRequest(
            messages=(ChatMessage(MessageRole.USER, "查找。"),),
            tools=(lookup_tool(),),
        )
    )

    assert response.tool_calls[0].name == "lookup"
    assert client.completions.calls[0]["extra_body"] == {
        "thinking": {"type": "enabled", "clear_thinking": False},
        "reasoning_effort": "max",
    }


def test_flash_accepts_parallel_tool_calls_for_sequential_agent_consumption() -> None:
    raw_calls = [
        SimpleNamespace(
            id=f"call-{index}",
            type="function",
            function=SimpleNamespace(
                name="lookup",
                arguments='{"query":"x"}',
            ),
        )
        for index in (1, 2)
    ]
    provider = ZhipuProvider(
        client=FakeClient(
            sdk_response(
                content=None,
                tool_calls=raw_calls,
                finish_reason="tool_calls",
            )
        ),
        model=ZHIPU_GLM53_FLASH_MODEL,
    )

    response = provider.chat(
        ChatRequest(
            messages=(ChatMessage(MessageRole.USER, "查找。"),),
            tools=(lookup_tool(),),
        )
    )
    assert [call.id for call in response.tool_calls] == ["call-1", "call-2"]


def test_explicit_profile_cannot_override_model_contract() -> None:
    with pytest.raises(ValueError, match="profile"):
        ZhipuProvider(
            client=FakeClient(sdk_response()),
            model=ZHIPU_GLM53_FLASH_MODEL,
            profile=resolve_zhipu_thinking_profile(ZHIPU_GLM52_MODEL),
        )


def test_settings_and_factory_expose_the_resolved_profile_without_new_override() -> None:
    settings = load_zhipu_settings(
        {
            "LLM_PROVIDER": "zhipu",
            "LLM_API_KEY": "secret-value",
            "LLM_BASE_URL": "https://open.bigmodel.cn/api/paas/v4/",
            "LLM_MODEL": ZHIPU_GLM53_FLASH_MODEL,
        }
    )
    assert settings.thinking_profile.profile_id == "glm-5.3-flash-enabled-max-replay"
    assert settings.thinking_profile_id == "glm-5.3-flash-enabled-max-replay"

    factory_calls: list[dict] = []

    def client_factory(**kwargs: object) -> FakeClient:
        factory_calls.append(kwargs)
        return FakeClient(sdk_response())

    provider = create_zhipu_provider(settings, client_factory=client_factory)
    assert provider.profile.profile_id == "glm-5.3-flash-enabled-max-replay"
    assert factory_calls[0]["base_url"].endswith("/paas/v4/")
    assert factory_calls[0]["timeout"] == 120.0
    assert factory_calls[0]["max_retries"] == 0


def test_flash_factory_rejects_a_non_official_base_url() -> None:
    settings = ZhipuSettings(
        api_key="secret-value",
        base_url="https://example.invalid/v1/",
        model=ZHIPU_GLM53_FLASH_MODEL,
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="invalid_base_url_for_runtime_profile",
    ):
        create_zhipu_provider(settings, client_factory=lambda **_: FakeClient(sdk_response()))


def test_settings_object_derives_profile_for_known_model() -> None:
    settings = ZhipuSettings(
        api_key="secret-value",
        base_url="https://example.invalid/v1/",
        model=ZHIPU_GLM53_FLASH_MODEL,
    )
    assert settings.thinking_profile.thinking_type == "enabled"
