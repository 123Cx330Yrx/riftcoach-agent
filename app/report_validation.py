"""Typed report rejections without exposing report text in diagnostics."""

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
