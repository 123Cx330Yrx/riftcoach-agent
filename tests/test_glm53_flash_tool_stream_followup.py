from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import app.evaluation.glm53_flash_tool_stream_followup as followup
from app.evaluation.glm53_flash_capability_matrix import MatrixSourceIdentity


def _chunk(*, finish_reason=None, tool_calls=None, reasoning=None, usage=None):
    return SimpleNamespace(
        id="followup-request",
        model="glm-5.3-flash",
        choices=(
            [
                SimpleNamespace(
                    finish_reason=finish_reason,
                    delta=SimpleNamespace(
                        content=None,
                        reasoning_content=reasoning,
                        tool_calls=tool_calls,
                    ),
                )
            ]
            if finish_reason is not None or tool_calls or reasoning
            else []
        ),
        usage=usage,
    )


def _tool_fragment():
    return SimpleNamespace(
        index=0,
        id="call-followup",
        type="function",
        function=SimpleNamespace(
            name="matrix_lookup_alpha",
            arguments='{"query":"x"}',
        ),
    )


class _FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return iter(
            [
                _chunk(
                    reasoning="private reasoning",
                    tool_calls=[_tool_fragment()],
                ),
                _chunk(
                    finish_reason="tool_calls",
                    usage=SimpleNamespace(prompt_tokens=12, completion_tokens=34),
                ),
                SimpleNamespace(
                    id="followup-request",
                    model="glm-5.3-flash",
                    choices=[],
                    usage=SimpleNamespace(prompt_tokens=12, completion_tokens=34),
                ),
            ]
        )


class _FakeClient:
    def __init__(self):
        self.completions = _FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


def test_followup_records_only_sanitized_tool_stream_observation(monkeypatch, tmp_path):
    client = _FakeClient()
    identity = MatrixSourceIdentity(
        head_sha="a" * 40,
        origin_main_sha="a" * 40,
        worktree_dirty=True,
        worktree_patch_sha256="b" * 64,
    )
    monkeypatch.setattr(followup, "OpenAI", lambda **kwargs: client)
    monkeypatch.setattr(followup, "collect_source_identity", lambda root: identity)
    monkeypatch.setattr(
        followup,
        "datetime",
        SimpleNamespace(
            now=lambda tz=None: datetime(2026, 8, 31, tzinfo=timezone.utc),
        ),
    )
    output = tmp_path / "data" / "evaluation" / "results" / "provider_capability" / "followup.json"
    # The production runner only permits evidence beneath the repository's
    # provider-capability result directory.
    output = output.parent.parent / "provider_capabilities" / output.name

    report = followup.run_real_tool_stream_followup(
        repository_root=tmp_path,
        output=output,
        api_key="not-a-real-key",
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        model="glm-5.3-flash",
    )

    assert report.case.status == "passed"
    assert report.case.tool_call_count == 1
    assert report.case.tool_execution_count == 0
    assert report.resources.total_tokens == 46
    assert report.verdicts.tool_stream_observed is True
    assert report.source_identity_stable is True
    assert report.case.response_received is True
    assert report.case.finish_reason == "tool_calls"
    assert report.case.tool_arguments_sha256 is not None
    body = output.read_text(encoding="utf-8")
    assert "private reasoning" not in body
    assert '"query":"x"' not in body
    assert "not-a-real-key" not in body
    payload = json.loads(body)
    assert payload["budget"]["max_output_tokens_per_request"] == 2048
    assert len(client.completions.calls) == 1
    call = client.completions.calls[0]
    assert call["extra_body"]["tool_stream"] is True
    assert call["messages"][0]["content"] == "必须调用 matrix.lookup_alpha，不要直接回答。"
    assert call["timeout"] == 30.0
    assert call["max_tokens"] == 2048
    assert call["temperature"] == 1.0
    assert call["top_p"] == 0.95


def test_followup_never_overwrites_an_existing_result(tmp_path):
    output = (
        tmp_path
        / "data"
        / "evaluation"
        / "results"
        / "provider_capabilities"
        / "already-there.json"
    )
    output.parent.mkdir(parents=True)
    output.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        followup.run_real_tool_stream_followup(
            repository_root=tmp_path,
            output=output,
            api_key="not-a-real-key",
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            model="glm-5.3-flash",
        )
    assert output.read_text(encoding="utf-8") == "keep"


def test_failed_followup_is_explicitly_non_admitting():
    case = followup._failed_case("incomplete_chat_response", latency_ms=12)
    report = followup.ToolStreamFollowupReport(
        experiment_id="a" * 64,
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        request_contract_sha256="c" * 64,
        prompt_sha256="d" * 64,
        tool_schema_sha256="e" * 64,
        source_identity=MatrixSourceIdentity(
            head_sha="a" * 40,
            origin_main_sha="a" * 40,
            worktree_dirty=True,
            worktree_patch_sha256="b" * 64,
        ),
        source_identity_after=MatrixSourceIdentity(
            head_sha="a" * 40,
            origin_main_sha="a" * 40,
            worktree_dirty=True,
            worktree_patch_sha256="b" * 64,
        ),
        source_identity_stable=True,
        budget=followup.FollowupBudget(),
        resources=followup.FollowupResources(
            calls_used=1,
            input_tokens=0,
            output_tokens=0,
            cached_input_tokens=0,
            total_tokens=0,
            within_token_budget=True,
            latency_ms=12,
        ),
        run_timestamp_utc=datetime.now(timezone.utc),
        case=case,
        unsupported_boundaries=("not a production gate",),
        verdicts=followup.FollowupVerdict(tool_stream_observed=False),
    )
    assert report.case.status == "failed"
    assert report.case.error_code == "incomplete_chat_response"
    assert report.verdicts.production_admitted is False
