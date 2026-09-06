"""Typed report rejections without exposing report text in diagnostics."""


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
