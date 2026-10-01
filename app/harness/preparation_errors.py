"""Body-free, typed diagnostics shared by Agent and Harness preparation."""

DRAFT_PREPARATION_CODES = frozenset({
    "agent_request_compilation_failed",
    "agent_loop_failed",
    "agent_loop_incomplete",
    "agent_context_budget_exceeded",
    "agent_final_text_missing",
    "agent_result_invalid",
    "knowledge_tool_failed",
    "knowledge_evidence_invalid",
})


class DraftPreparationError(RuntimeError):
    """The message is private; only an allowlisted code may be persisted."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        if code is not None and (not isinstance(code, str) or code not in DRAFT_PREPARATION_CODES):
            raise ValueError("unsupported draft preparation code")
        self.code = code
        super().__init__(message)
