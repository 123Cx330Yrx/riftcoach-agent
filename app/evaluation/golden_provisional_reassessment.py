"""Offline provisional-first contract, after the first live comparison failure.

Final schema validity is not a prerequisite for correcting an assessment.
Only host-identifiable source obligations are admitted: an unresolvable span
with a real block ID protects that entire block, never an invented quotation.
Unknown blocks, missing inventories, truncated JSON and high injection stop.
No live runner is enabled by this module.
"""
from dataclasses import dataclass
from types import SimpleNamespace
import re

from app.evaluation import golden_reassessment_feasibility as full
from app.evaluation import golden_comparison_reassessment as comparison
from app.evaluation.golden_bounded_correction_requests import source_data
from app.evaluation.golden_context_review import IssueRef
from app.evaluation.golden_contextual_first_wire import FirstWire
from app.evaluation.golden_evidence_scope_v5 import normalize_json
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_review_experiment import QuoteRef, compact, digest

EXPERIMENT_ID = "golden-provisional-reassessment-offline-v1"


@dataclass(frozen=True)
class State:
    raw: str
    inputs: object
    identity: str


def inspect(raw, inputs):
    value = strict_json(normalize_json(raw))
    if not isinstance(value, dict):
        raise ValueError("provisional_object_required")
    if not isinstance(value.get("issues"), list):
        raise ValueError("provisional_issue_inventory_required")
    if any(isinstance(row, dict) and row.get("category") == "prompt_injection"
           and row.get("severity") == "high" for row in value["issues"]):
        raise ValueError("correction_security_terminal")
    if value.get("source_digest") != inputs.source.source_digest:
        raise ValueError("provisional_source_changed")
    if value.get("reviewed_blocks") != list(range(1, len(inputs.source.blocks) + 1)):
        raise ValueError("provisional_block_inventory_changed")
    expected = [i for i, (_, text) in enumerate(inputs.source.blocks, 1) if re.match(r"^#{1,6}\s", text)]
    headings = value.get("heading_reviews")
    if (not isinstance(headings, list) or any(not isinstance(h, dict) for h in headings)
            or [h.get("block_id") for h in headings] != expected):
        raise ValueError("provisional_heading_inventory_changed")
    audits = value.get("audits")
    if (not isinstance(audits, list) or any(not isinstance(a, dict) for a in audits)
            or [a.get("kind") for a in audits] != ["metric_to_ability", "cohort_comparison"]):
        raise ValueError("provisional_audit_inventory_changed")
    diagnostics = []
    try:
        FirstWire.model_validate(value, strict=True)
    except ValueError as error:
        diagnostics.extend(dict(code=e["type"], location=list(e["loc"]))
            for e in error.errors(include_input=False, include_context=False))
    protections = []
    for audit in audits:
        if not isinstance(audit.get("claims"), list):
            raise ValueError("provisional_claim_inventory_required")
        claims = []
        for index, row in enumerate(audit["claims"]):
            ref, fallback = protected_reference(row, inputs)
            claims.append(SimpleNamespace(quote_ref=ref))
            if fallback:
                diagnostics.append(dict(code="unresolved_quote_protects_complete_block",
                    audit=audit["kind"], claim_index=index, protected_block=ref.block))
            if isinstance(row, dict) and row.get("scope_source") is not None:
                try: inputs.source.resolve(row["scope_source"])
                except (ValueError, TypeError):
                    diagnostics.append(dict(code="invalid_scope_reference", audit=audit["kind"], claim_index=index))
        if len({c.quote_ref.block for c in claims}) > 24:
            raise ValueError("provisional_coverage_exceeds_final_capacity")
        protections.append(SimpleNamespace(kind=audit["kind"], claims=claims))
    # Invalid issue wording/fields can be corrected only through an explicit
    # disposition. Never silently discard the original issue or unknown block.
    for row in value["issues"]:
        protected_reference(row, inputs)
    return value, SimpleNamespace(audits=protections), diagnostics


def protected_reference(row, inputs):
    if not isinstance(row, dict) or not isinstance(row.get("quote_ref"), dict):
        raise ValueError("provisional_quote_block_required")
    block = row["quote_ref"].get("block")
    if type(block) is not int or not 1 <= block <= len(inputs.source.blocks):
        raise ValueError("provisional_unknown_source_block")
    try:
        ref = QuoteRef.model_validate(row["quote_ref"], strict=True)
        inputs.source.resolve(ref.model_dump(mode="json"))
    except ValueError:
        return QuoteRef(block=block), True
    return ref, False


def prepare(raw, inputs):
    inspect(raw, inputs)
    return State(raw, inputs, digest(compact(dict(raw=raw, inputs=inputs.data_json))))


def check_state(state, inputs):
    if state.inputs != inputs or prepare(state.raw, inputs) != state:
        raise ValueError("provisional_state_changed")


def build_request(state):
    check_state(state, state.inputs)
    value, _, diagnostics = inspect(state.raw, state.inputs)
    data = source_data(state.inputs)
    data.update(first_review=value, issue_ids=[f"i{i:03}" for i in range(1, len(value["issues"]) + 1)],
        provisional_diagnostics=diagnostics)
    # All provisional fields remain data; this does not turn the first verdict
    # into an accepted review or rewrite its raw response.
    return comparison.request_from_parts(data, state.inputs, extra_policy=
        "\n首评是未验收临时意见，provisional_diagnostics列格式/定位问题。原始错误字段仍保留；"
        "unresolved_quote_protects_complete_block要求覆盖protected_block全文，并非承认错误引用。"
        "按原文重新切分并正确引用，纠正超量来源/分类及遗漏；不能只修格式。最终必须满足完整schema。")


def apply(state, raw, *, inputs):
    check_state(state, inputs)
    before, protections, diagnostics = inspect(state.raw, inputs)
    after = full._read(raw, inputs, comparison.ComparisonWire)
    mapping = full.coverage_map(protections, after, inputs.source)
    evidence = comparison.catalog(inputs)
    bindings = comparison.validate_bindings(after, inputs, evidence)
    old_issues = []
    for row in before["issues"]:
        try: row = IssueRef.model_validate(row, strict=True).model_dump(mode="json")
        except ValueError: pass  # Must be explicitly resolved; raw value retained.
        old_issues.append(row)
    result, journal = full.finalize(old_issues, after, inputs=inputs, raw=raw,
        first_raw=state.raw, state_id=state.identity, mapping=mapping)
    journal.update(experiment=EXPERIMENT_ID, provisional_diagnostics=diagnostics,
        comparison_evidence=evidence, comparison_bindings=bindings,
        semantic_limits=["cohort_and_metric_selection", "prose_binding_consistency",
            "omitted_comparisons", "scope_relation_and_extrapolation"])
    return result, journal


# The retired comparison entry is never switched to this class. A separately
# qualified development runner imports it through golden_provisional_workflow.
from app.evaluation.golden_comparison_workflow import ComparisonReassessmentWorkflow
from app.evaluation.golden_bounded_correction_requests import PreparedCorrection


class ProvisionalReassessmentWorkflow(ComparisonReassessmentWorkflow):
    prepare_state = staticmethod(prepare)
    merge_correction = staticmethod(apply)

    @staticmethod
    def build_correction(state):
        return PreparedCorrection(state, build_request(state))
