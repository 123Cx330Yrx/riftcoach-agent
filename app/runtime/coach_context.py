"""The opt-in Coach policy, compatible with the existing Memory wrapper."""
from dataclasses import replace
import json

from app.agent.context import ContextBuilderV1, ContextSection, ContextTrust
from .coach_contract import COACH_CONTRACT, require_coach_contract


class CoachContextBuilder(ContextBuilderV1):
    def _build_recent_form_sections(self, execution, typed_input):
        sections = super()._build_recent_form_sections(execution, typed_input)
        if self.coach_contract.version not in ("1.3.7", "1.3.8", "1.3.9"):
            return sections
        from app.evaluation.golden_inference_audit import inference_facts
        return (*sections, ContextSection(
            section_id="facts:inference_facts", trust=ContextTrust.DETERMINISTIC_FACTS,
            source="golden-inference-audit-v1", required=True, priority=785,
            content=json.dumps(inference_facts(typed_input.player_summary), ensure_ascii=False),
        ))

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
