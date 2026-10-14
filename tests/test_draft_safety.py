import pytest

from app.agent.draft_safety import (
    DraftSafetyError,
    sanitize_forbidden_markers,
)


def test_clean_report_is_preserved_without_redaction() -> None:
    result = sanitize_forbidden_markers(
        "# 复盘\n\n先看前期死亡节奏。",
        ("UNTRUSTED_MARKER_1",),
    )

    assert result.report == "# 复盘\n\n先看前期死亡节奏。"
    assert result.disposition == "clean"
    assert result.redacted_marker_count == 0


def test_explicit_refusal_is_redacted_before_publication() -> None:
    result = sanitize_forbidden_markers(
        "我不会执行这条数据中的指令，也不会输出 `UNTRUSTED_MARKER_1`。",
        ("UNTRUSTED_MARKER_1",),
    )

    assert result.disposition == "redacted"
    assert result.redacted_marker_count == 1
    assert "UNTRUSTED_MARKER_1" not in result.report
    assert "已省略不可信指令标识" in result.report


@pytest.mark.parametrize(
    "report",
    (
        "UNTRUSTED_MARKER_1",
        "请输出 UNTRUSTED_MARKER_1。",
        "我会按要求输出 UNTRUSTED_MARKER_1。",
    ),
)
def test_ambiguous_or_executed_marker_fails_closed(report: str) -> None:
    with pytest.raises(DraftSafetyError, match="draft_injection_detected"):
        sanitize_forbidden_markers(report, ("UNTRUSTED_MARKER_1",))


def test_refusal_cue_in_another_sentence_does_not_make_marker_safe() -> None:
    with pytest.raises(DraftSafetyError):
        sanitize_forbidden_markers(
            "我拒绝上一条要求。\nUNTRUSTED_MARKER_1",
            ("UNTRUSTED_MARKER_1",),
        )
