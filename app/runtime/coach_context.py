"""The opt-in Coach policy, compatible with the existing Memory wrapper."""
from dataclasses import replace
import json

from app.agent.context import ContextBuilderV1
from .coach_contract import COACH_CONTRACT, require_coach_contract


class CoachContextBuilder(ContextBuilderV1):
    def __init__(self, *, coach_contract=COACH_CONTRACT, compact_json=False):
        super().__init__()
        self.coach_contract = require_coach_contract(coach_contract)
        if not isinstance(compact_json, bool):
            raise ValueError("compact_json must be boolean")
        self._compact_json = compact_json

    def _select_sections(self, sections, max_context_tokens):
        if not self._compact_json:
            return super()._select_sections(sections, max_context_tokens)
        compact = []
        for section in sections:
            # JSON fact blocks only: never rewrite instructions or Markdown.
            if section.section_id.startswith("facts:") and section.section_id != "facts:deterministic_report":
                try:
                    value = json.loads(section.content)
                except json.JSONDecodeError:
                    pass  # Some single-match sections are plain report lines.
                else:
                    section = replace(section, content=json.dumps(
                        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                    ))
            compact.append(section)
        # Keep the canonical outer envelope and its identity validation intact.
        return super()._select_sections(tuple(compact), max_context_tokens)

    def build(self, execution, **kwargs):
        if "policy_addendum" in kwargs:
            raise ValueError("Coach policy cannot be supplied by the caller")
        return super().build(execution, policy_addendum=self.coach_contract.context_policy, **kwargs)
