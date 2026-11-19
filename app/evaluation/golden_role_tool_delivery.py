"""Tool-only delivery for role reviews; legacy note requests stay reproducible.

This removes a redundant text-response instruction, not a business check or
response field. It makes no claim about semantic accuracy or qualification.
"""
from dataclasses import replace

from app.evaluation.golden_role_notes import RoleNoteReviewWorkflow
from app.evaluation.golden_native_issues_review import budget_check, schema_notation

DELIVERY_ID = "role-review-tool-schema-only-v1"


class RoleToolDeliveryReviewWorkflow(RoleNoteReviewWorkflow):
    @staticmethod
    def make_request(inputs, **kwargs):
        prepared = RoleNoteReviewWorkflow.make_request(inputs, **kwargs)
        if kwargs.get("accepted") is not None:
            return prepared  # The editor still returns the full Markdown report.
        if len(prepared.tools) != 1:
            raise ValueError("role_delivery_tool_inventory_changed")
        header = schema_notation(prepared.tools[0].input_schema) + "\n"
        message = prepared.messages[1]
        if not message.content.startswith(header + "[UNTRUSTED DATA]\n"):
            raise ValueError("role_delivery_schema_header_changed")
        return budget_check(replace(prepared,
            messages=(prepared.messages[0], replace(message,
                content=message.content[len(header):]), *prepared.messages[2:]),
            metadata={**prepared.metadata, "review_delivery": DELIVERY_ID}))

    @staticmethod
    def validate_review(raw, inputs, *, previous_raw=None):
        payload, wire, journal = RoleNoteReviewWorkflow.validate_review(
            raw, inputs, previous_raw=previous_raw)
        return payload, wire, {**journal, "request_delivery": DELIVERY_ID}
