from __future__ import annotations

from types import SimpleNamespace

from app.evaluation.glm53_flash_capability_matrix import (
    FlashCapabilityMatrixRunner,
    MatrixSourceIdentity,
    _red_png_data_url,
)


def _response(
    *,
    content: str | None,
    request_id: str,
    reasoning: str | None = None,
    tool_calls: list[SimpleNamespace] | None = None,
    finish_reason: str = "stop",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=request_id,
        model="glm-5.3-flash",
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    content=content,
                    reasoning_content=reasoning,
                    tool_calls=tool_calls or [],
                ),
            )
        ],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )


def _tool_call(name: str, call_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments="{}"),
    )


def _stream_text() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            id="stream-text",
            model="glm-5.3-flash",
            choices=[
                SimpleNamespace(
                    finish_reason=None,
                    delta=SimpleNamespace(
                        content="RIFT", reasoning_content="stream-think ", tool_calls=None
                    ),
                )
            ],
            usage=None,
        ),
        SimpleNamespace(
            id="stream-text",
            model="glm-5.3-flash",
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    delta=SimpleNamespace(
                        content="COACH_F6_OK", reasoning_content=None, tool_calls=None
                    ),
                )
            ],
            usage=None,
        ),
        SimpleNamespace(
            id="stream-text",
            model="glm-5.3-flash",
            choices=[],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        ),
    ]


def _stream_tool() -> list[SimpleNamespace]:
    fragment = SimpleNamespace(
        index=0,
        id="stream-call",
        type="function",
        function=SimpleNamespace(name="matrix_lookup_alpha", arguments="{}"),
    )
    return [
        SimpleNamespace(
            id="stream-tool",
            model="glm-5.3-flash",
            choices=[
                SimpleNamespace(
                    finish_reason="tool_calls",
                    delta=SimpleNamespace(
                        content=None, reasoning_content="tool-think", tool_calls=[fragment]
                    ),
                )
            ],
            usage=None,
        ),
        SimpleNamespace(
            id="stream-tool",
            model="glm-5.3-flash",
            choices=[],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        ),
    ]


class _FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self._counter = 0

    def create(self, **kwargs):
        self.calls.append(kwargs)
        self._counter += 1
        if kwargs.get("stream"):
            if kwargs.get("extra_body", {}).get("tool_stream"):
                return iter(_stream_tool())
            return iter(_stream_text())
        messages = kwargs["messages"]
        if isinstance(messages[0].get("content"), list):
            return _response(content="RED", request_id=f"f8-{self._counter}")
        if kwargs.get("response_format"):
            return _response(
                content='{"marker":"RIFTCOACH_F2_OK","score":100}',
                request_id=f"f2-{self._counter}",
                reasoning="f2-reasoning",
            )
        tool_names = [
            row["function"]["name"]
            for row in kwargs.get("tools", [])
        ]
        if "matrix_lookup_alpha" in tool_names and "matrix_lookup_beta" in tool_names:
            if any(row.get("role") == "tool" for row in messages):
                return _response(content="RIFTCOACH_F3_OK", request_id=f"f3-{self._counter}")
            return _response(
                content=None,
                request_id=f"f3-{self._counter}",
                reasoning="f3-reasoning",
                finish_reason="tool_calls",
                tool_calls=[
                    _tool_call("matrix_lookup_alpha", "f3-a"),
                    _tool_call("matrix_lookup_beta", "f3-b"),
                ],
            )
        if "matrix_game_facts" in tool_names:
            if any(row.get("role") == "tool" for row in messages):
                return _response(
                    content="PLAYER_FACTS RIFTCOACH_F5_OK",
                    request_id=f"f5-{self._counter}",
                )
            return _response(
                content=None,
                request_id=f"f5-{self._counter}",
                reasoning="f5-reasoning",
                finish_reason="tool_calls",
                tool_calls=[_tool_call("matrix_game_facts", "f5-a")],
            )
        if len(str(messages)) > 50_000:
            return _response(
                content="F4_BEGIN,F4_MIDDLE,F4_END",
                request_id=f"f4-{self._counter}",
                reasoning="f4-reasoning",
            )
        return _response(
            content="RIFTCOACH_F1_OK",
            request_id=f"f1-{self._counter}",
            reasoning="f1-reasoning",
        )


class _FakeClient:
    def __init__(self) -> None:
        self.completions = _FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


def test_matrix_runs_all_cases_with_hard_call_budget_and_redaction() -> None:
    client = _FakeClient()
    identity = MatrixSourceIdentity(
        head_sha="a" * 40,
        origin_main_sha="a" * 40,
        worktree_dirty=True,
        worktree_patch_sha256="b" * 64,
    )
    report = FlashCapabilityMatrixRunner(
        client=client,
        code_identity=identity,
        now=lambda: __import__("datetime").datetime(2026, 8, 31, tzinfo=__import__("datetime").timezone.utc),
    ).run()

    assert report.resources.calls_used == 11
    assert report.resources.total_tokens == 165
    assert all(case.status == "passed" for case in report.cases)
    assert report.verdicts.production_admitted is False
    assert "f3-reasoning" not in report.model_dump_json()
    assert len(client.completions.calls) == 11


def test_red_png_data_url_is_a_small_valid_data_url() -> None:
    value = _red_png_data_url()
    assert value.startswith("data:image/png;base64,")
    assert len(value) < 500
