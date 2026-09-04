"""Candidate-only output boundary for untrusted instruction echoes.

The normal product path keeps its existing fail-closed evaluator.  This small
helper is used by an explicitly versioned candidate boundary to distinguish a
clearly worded refusal that happens to quote an unsafe marker from an output
that emits the marker as an instruction/result.  A quoted refusal is redacted
before evaluation and publication; ambiguous occurrences are rejected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Sequence


class DraftSafetyError(ValueError):
    """Raised when a draft contains an ambiguous or executed unsafe marker."""

    code = "draft_injection_detected"

    def __init__(self) -> None:
        # Do not include the marker or draft text in an exception that could
        # cross a public receipt boundary.
        super().__init__(self.code)


@dataclass(frozen=True)
class DraftSafetyResult:
    report: str
    disposition: Literal["clean", "redacted"]
    redacted_marker_count: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.report, str) or not self.report.strip():
            raise ValueError("report must be non-blank")
        if self.disposition not in {"clean", "redacted"}:
            raise ValueError("disposition is invalid")
        if (
            isinstance(self.redacted_marker_count, bool)
            or not isinstance(self.redacted_marker_count, int)
            or self.redacted_marker_count < 0
        ):
            raise ValueError("redacted_marker_count must be non-negative")
        if self.disposition == "clean" and self.redacted_marker_count:
            raise ValueError("clean result cannot report redactions")
        if self.disposition == "redacted" and not self.redacted_marker_count:
            raise ValueError("redacted result must report a redaction")


_SEGMENT_BREAKS = frozenset("\r\n。！？!?；;．.")
_REFUSAL_CUES = (
    "不执行",
    "不会执行",
    "不遵循",
    "不会遵循",
    "不按照",
    "不会按照",
    "不会照做",
    "不能照做",
    "不能按此",
    "不应执行",
    "不输出",
    "不会输出",
    "拒绝",
    "忽略这条指令",
    "忽略该指令",
    "仅作为数据",
    "仅作数据",
    "把它当作数据",
    "do not follow",
    "will not comply",
    "cannot comply",
    "can't comply",
    "not an instruction",
    "treat it as data",
    "treat this as data",
    "ignore this instruction",
)
_REDACTION = "[已省略不可信指令标识]"


def sanitize_forbidden_markers(
    report: str,
    markers: Sequence[str],
) -> DraftSafetyResult:
    """Redact only markers inside an explicit refusal; otherwise fail closed.

    The function is deliberately marker-agnostic: callers provide the frozen
    case markers, while the decision relies on a refusal envelope rather than
    a case-specific string or a single consumed test asset.
    """

    if not isinstance(report, str) or not report.strip():
        raise ValueError("report must be non-blank")
    normalized = tuple(
        marker.strip()
        for marker in markers
        if isinstance(marker, str) and marker.strip()
    )
    if len(set(normalized)) != len(normalized):
        raise ValueError("markers must be unique non-blank strings")
    current = report
    redacted = 0
    for marker in normalized:
        matches = list(re.finditer(re.escape(marker), current))
        if not matches:
            continue
        if any(
            not _is_explicit_refusal(current, match.start(), match.end())
            for match in matches
        ):
            raise DraftSafetyError()
        current = current.replace(marker, _REDACTION)
        redacted += len(matches)
    if redacted:
        return DraftSafetyResult(
            report=current,
            disposition="redacted",
            redacted_marker_count=redacted,
        )
    return DraftSafetyResult(report=current, disposition="clean")


def _is_explicit_refusal(text: str, start: int, end: int) -> bool:
    segment_start = start
    while segment_start > 0 and text[segment_start - 1] not in _SEGMENT_BREAKS:
        segment_start -= 1
    segment_end = end
    while segment_end < len(text) and text[segment_end] not in _SEGMENT_BREAKS:
        segment_end += 1
    segment = text[segment_start:segment_end].casefold()
    return any(cue.casefold() in segment for cue in _REFUSAL_CUES)


__all__ = [
    "DraftSafetyError",
    "DraftSafetyResult",
    "sanitize_forbidden_markers",
]
