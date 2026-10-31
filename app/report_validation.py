"""Typed report rejections without exposing report text in diagnostics."""

from dataclasses import dataclass
import re

COACH_REPORT_HEADINGS = (
    "# RiftCoach 教练式复盘报告",
    "## 1. 总体结论",
    "## 2. 当前表现亮点",
    "## 3. 主要风险点",
    "## 4. 赢局与输局差异",
    "## 5. 下一步复盘建议",
    "## 6. 训练计划",
    "## 7. 数据边界与知识来源",
)

# Structural identities only. A task-appropriate title is not semantic approval.
_HEADING_ALIASES = {"## 6. 观摩练习计划": COACH_REPORT_HEADINGS[6]}


def report_heading_identity(text: str) -> str | None:
    for heading in (*COACH_REPORT_HEADINGS, *_HEADING_ALIASES):
        if text == heading or any(text.startswith(heading + separator) for separator in ("：", ":", " ")):
            return _HEADING_ALIASES.get(heading, heading)
    return None


@dataclass(frozen=True)
class ReportHeading:
    identity: str | None
    level: int
    start: int
    end: int


def report_headings(report: str) -> tuple[ReportHeading, ...]:
    """Read Markdown ATX headings outside fences, retaining original text offsets."""
    result, fence, offset = [], None, 0
    for raw_line in report.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        start, offset = offset, offset + len(raw_line)
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence is not None:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not line[marker.end():].strip():
                fence = None
            continue
        if marker:
            fence = marker[1]
            continue
        heading = re.match(r"^ {0,3}(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$", line)
        if heading:
            identity = report_heading_identity(heading[1] + " " + heading[2])
            result.append(ReportHeading(identity, len(heading[1]), start, offset))
    return tuple(result)


def report_section_body(report: str, identity: str) -> str:
    """Extract an unambiguous section without normalizing report text."""
    headings = [heading for heading in report_headings(report) if heading.identity is not None]
    if tuple(heading.identity for heading in headings) != COACH_REPORT_HEADINGS or identity not in COACH_REPORT_HEADINGS:
        return ""
    index = COACH_REPORT_HEADINGS.index(identity)
    end = headings[index + 1].start if index + 1 < len(headings) else len(report)
    return report[headings[index].end:end]


class ReportValidationError(ValueError):
    """Keep ValueError compatibility and an allowlisted machine-readable code."""

    CODES = frozenset({
        "report_missing_headings", "report_too_short", "unknown_report_citation",
    })

    def __init__(self, code: str, message: str) -> None:
        if not isinstance(code, str) or code not in self.CODES:
            raise ValueError("unsupported report validation code")
        self.code = code
        super().__init__(message)
