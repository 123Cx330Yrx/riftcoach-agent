import unittest

from app.providers.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    MessageRole,
    TokenUsage,
    ToolCall,
    ToolChoiceMode,
    ToolSpec,
)


def recent_matches_spec() -> ToolSpec:
    return ToolSpec(
        name="riot.recent_match_ids",
        description="Get recent match identifiers for one Riot account.",
        input_schema={
            "type": "object",
            "properties": {
                "puuid": {"type": "string"},
                "count": {"type": "integer", "minimum": 1},
            },
            "required": ["puuid"],
            "additionalProperties": False,
        },
    )


class ToolCallingMessageTests(unittest.TestCase):
    def test_pure_text_messages_remain_backward_compatible(self) -> None:
        message = ChatMessage(MessageRole.USER, "复盘最近十局。")
        response = ChatResponse(
            content="先看确定性数据。",
            model="glm-test",
            provider="zhipu",
            usage=TokenUsage(input_tokens=0, output_tokens=0),
        )

        self.assertEqual("复盘最近十局。", message.content)
        self.assertFalse(response.requests_tools)

    def test_assistant_can_request_a_tool_without_text_content(self) -> None:
        call = ToolCall(
            id="call-1",
            name="riot.recent_match_ids",
            arguments={"puuid": "masked", "count": 10},
        )
        message = ChatMessage(
            role=MessageRole.ASSISTANT,
            content=None,
            tool_calls=(call,),
        )
        response = ChatResponse(
            content=None,
            tool_calls=(call,),
            model="glm-test",
            provider="zhipu",
            finish_reason="tool_calls",
            usage=TokenUsage(input_tokens=0, output_tokens=0),
        )

        self.assertEqual(call, message.tool_calls[0])
        self.assertTrue(response.requests_tools)

    def test_tool_result_message_correlates_with_the_original_call(self) -> None:
        message = ChatMessage(
            role=MessageRole.TOOL,
            content='{"match_ids":["KR_1"]}',
            tool_call_id="call-1",
            name="riot.recent_match_ids",
        )

        self.assertEqual("call-1", message.tool_call_id)
        self.assertEqual(MessageRole.TOOL, message.role)

    def test_role_specific_invariants_reject_ambiguous_messages(self) -> None:
        call = ToolCall(id="call-1", name="knowledge.search", arguments={})
        invalid_messages = (
            lambda: ChatMessage(MessageRole.USER, None),
            lambda: ChatMessage(
                MessageRole.USER,
                "hello",
                tool_calls=(call,),
            ),
            lambda: ChatMessage(MessageRole.ASSISTANT, None),
            lambda: ChatMessage(MessageRole.TOOL, "result"),
            lambda: ChatMessage(
                MessageRole.TOOL,
                "result",
                tool_call_id="call-1",
                tool_calls=(call,),
            ),
            lambda: ChatMessage(
                MessageRole.ASSISTANT,
                None,
                tool_calls=(call, call),
            ),
        )

        for build in invalid_messages:
            with self.subTest(build=build):
                with self.assertRaises(ValueError):
                    build()


class ToolCallingRequestTests(unittest.TestCase):
    def test_request_carries_tool_specs_and_choice_policy(self) -> None:
        request = ChatRequest(
            messages=(ChatMessage(MessageRole.USER, "查询最近比赛"),),
            tools=(recent_matches_spec(),),
            tool_choice=ToolChoiceMode.REQUIRED,
        )

        self.assertEqual("riot.recent_match_ids", request.tools[0].name)
        self.assertEqual(ToolChoiceMode.REQUIRED, request.tool_choice)

    def test_required_choice_without_tools_is_invalid(self) -> None:
        with self.assertRaises(ValueError):
            ChatRequest(
                messages=(ChatMessage(MessageRole.USER, "查询最近比赛"),),
                tool_choice=ToolChoiceMode.REQUIRED,
            )

    def test_tool_specs_require_object_schema_and_unique_names(self) -> None:
        with self.assertRaises(ValueError):
            ToolSpec(
                name="knowledge.search",
                description="Search knowledge.",
                input_schema={"type": "string"},
            )

        spec = recent_matches_spec()
        with self.assertRaises(ValueError):
            ChatRequest(
                messages=(ChatMessage(MessageRole.USER, "hello"),),
                tools=(spec, spec),
            )


if __name__ == "__main__":
    unittest.main()
