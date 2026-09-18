"""Source-aware review batches with host computation and one global decision.

Experimental workflow only. Original source and provisional output are retained;
host calculations do not select a claim's meaning or approve its interpretation.
"""
from copy import deepcopy
from dataclasses import dataclass, replace
import re
from types import SimpleNamespace
from typing import Literal

from pydantic import Field

from app.evaluation import golden_typed_review as typed
from app.evaluation.golden_bounded_correction_requests import (
    PreparedCorrection, UntitledSchema, budget_check, source_data,
)
from app.evaluation.golden_context_review import HeadingRef, IssueRef
from app.evaluation.golden_contextual_requests import project, _tables, _restore_tables, revision_request
from app.evaluation.golden_contextual_correction import FULL_CONTEXT_RULE
from app.evaluation.golden_grounded_reading_review import provisional_json
from app.evaluation.golden_integrated_review import Strict
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_evidence_scope_v5 import normalize_json
from app.evaluation.golden_review_experiment import QuoteRef, compact, digest
from app.evaluation.golden_schema_notation import schema_notation
from app.evaluation.golden_typed_source_checks import SourceLiteral
from app.providers.models import ChatMessage, ChatRequest, MessageRole
from app.providers.structured import contract_for_model

EXPERIMENT_ID = "golden-computed-partition-review-v1"
LIVE_STATUS = "bounded_development_after_exact_ci"
LIVE_BLOCK_REASON = ""


def require_live_qualification():
    if LIVE_STATUS != "bounded_development_after_exact_ci":
        raise ValueError(LIVE_BLOCK_REASON or "computed_partition_requires_whole_method_qualification")


class ComparisonChoice(Strict):
    cohort: Literal["selected", "TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
    metric: typed.comparison.Metric


class SummaryChoice(ComparisonChoice):
    operation: Literal["mean", "median"]
    reported: str = Field(pattern=r"^[0-9]+(?:\.[0-9]{1,6})?%?$", max_length=24)


class Claim(typed.TypedClaim):
    comparisons: list[ComparisonChoice] = Field(max_length=78)
    summaries: list[SummaryChoice] = Field(max_length=8)


class Audit(Strict):
    kind: Literal["metric_to_ability", "cohort_comparison"]
    claims: list[Claim] = Field(max_length=24)


class SourceChoice(Strict):
    key: str = Field(min_length=1, max_length=160)
    path: list[str | int] = Field(max_length=12)


class LiteralChoice(SourceLiteral):
    source: SourceChoice


class SourceCheck(typed.SourceCheck):
    sources: list[SourceChoice] = Field(max_length=12)
    literals: list[LiteralChoice] = Field(max_length=24)


class Resolution(typed.TypedResolution):
    sources: list[SourceChoice] = Field(max_length=12)


class Partial(UntitledSchema, Strict):
    heading_reviews: list[HeadingRef] = Field(max_length=64)
    audits: list[Audit] = Field(min_length=2, max_length=2)
    source_checks: list[SourceCheck] = Field(max_length=32)
    issues: list[IssueRef]


class BlockReplacement(Strict):
    block: int = Field(ge=1, le=64)
    heading_review: HeadingRef | None
    audits: list[Audit] = Field(min_length=2, max_length=2)
    source_checks: list[SourceCheck] = Field(max_length=32)


class FinalPartial(Partial):
    replacements: list[BlockReplacement] = Field(max_length=64)
    issue_resolutions: list[Resolution]
    score: int = Field(ge=0, le=100)
    verdict: Literal["pass", "needs_revision", "fail"]
    summary: str = Field(min_length=1, max_length=1200)
    passed_checks: list[str] = Field(max_length=12)


def body_blocks(inputs):
    return [b for b, (_, text) in enumerate(inputs.source.blocks, 1) if not re.match(r"^#{1,6}\s", text)]


def allocation(inputs):
    body = body_blocks(inputs)
    if not body:
        raise ValueError("partition_body_required")
    # The second request carries the first result as well as all source data.
    # Reserve input room for that provisional result and its corrections.
    cut = body[(len(body) + 2) // 3 - 1]
    return tuple(range(1, cut + 1)), tuple(range(cut + 1, len(inputs.source.blocks) + 1))


def rows(value):
    return [c for a in value["audits"] for c in a["claims"]] + value["source_checks"]


def check_inventory(value, inputs, assigned, *, provisional=False):
    if not isinstance(value, dict) or any(not isinstance(value.get(k), list)
            for k in ("audits", "heading_reviews", "source_checks", "issues")):
        raise ValueError("partition_inventory_required")
    if (any(not isinstance(a, dict) or not isinstance(a.get("claims"), list) for a in value["audits"])
            or [a.get("kind") for a in value["audits"]] != ["metric_to_ability", "cohort_comparison"]):
        raise ValueError("partition_audit_inventory")
    if any(isinstance(i, dict) and i.get("category") == "prompt_injection" and i.get("severity") == "high"
            for i in value["issues"]):
        raise ValueError("correction_security_terminal")
    # Admit imperfect opinions, not unbounded objects or unknown coordinates.
    if len(rows(value)) > 128 or len(value["heading_reviews"]) > 64:
        raise ValueError("partition_provisional_capacity")
    for row in rows(value) + value["issues"]:
        ref = row.get("quote_ref") if isinstance(row, dict) else None
        if (not isinstance(ref, dict) or type(ref.get("block")) is not int
                or not 1 <= ref["block"] <= len(inputs.source.blocks)):
            raise ValueError("partition_unknown_primary_block")
        if not provisional:
            inputs.source.resolve(ref)
    for row in rows(value):
        if row["quote_ref"]["block"] not in assigned:
            raise ValueError("partition_primary_outside_assignment")
    for row in value["heading_reviews"]:
        if not isinstance(row, dict) or type(row.get("block_id")) is not int or row["block_id"] not in assigned:
            raise ValueError("partition_heading_outside_assignment")
    if not provisional and [h["block_id"] for h in value["heading_reviews"]] != [
            b for b in assigned if re.match(r"^#{1,6}\s", inputs.source.blocks[b-1][1])]:
        raise ValueError("partition_heading_inventory")


@dataclass(frozen=True)
class State:
    raw: str
    inputs: object
    value_json: str
    diagnostics: tuple


def prepare(raw, inputs):
    value, repeated = provisional_json(raw)
    check_inventory(value, inputs, allocation(inputs)[0], provisional=True)
    diagnostics = list(repeated)
    try:
        Partial.model_validate(value, strict=True)
    except ValueError as error:
        diagnostics.extend(dict(code=e["type"], location=list(e["loc"]))
            for e in error.errors(include_input=False, include_context=False))
    for i, row in enumerate(rows(value)):
        for name in ("quote_ref", "scope_source"):
            if row.get(name) is not None:
                try: inputs.source.resolve(row[name])
                except (ValueError, TypeError):
                    diagnostics.append(dict(code="unresolved_first_reference", row=i, field=name))
    mentioned = {c["quote_ref"]["block"] for c in rows(value)}
    missing = sorted(set(body_blocks(inputs)).intersection(allocation(inputs)[0]) - mentioned)
    if missing:
        diagnostics.append(dict(code="omitted_first_body_blocks", blocks=missing))
    return State(raw, inputs, compact(value), tuple(diagnostics))


def check_state(state, inputs):
    if state.inputs != inputs or prepare(state.raw, inputs) != state:
        raise ValueError("partition_state_changed")


def table_partial(value, *, restore=False):
    result = deepcopy(value)
    def atom(row, keys, *, optional=False):
        if restore:
            return row["unparsed"] if isinstance(row, dict) else dict(zip(keys, row, strict=not optional))
        valid = isinstance(row, dict) and (set(row) == set(keys) or
            (optional and any(set(row) == set(keys[:n]) for n in range(1, len(keys) + 1))))
        return [row[k] for k in keys if k in row] if valid else {"unparsed": row}
    def nested(items):
        for row in items:
            for field in ("quote_ref", "scope_source"):
                if field in row and row[field] is not None:
                    row[field] = atom(row[field], ("block", "head", "tail"), optional=True)
            for field, keys in (("comparisons", ("cohort", "metric")),
                    ("summaries", ("cohort", "metric", "operation", "reported"))):
                if isinstance(row.get(field), list):
                    row[field] = [atom(op, keys) for op in row[field]]
        return items
    def convert(items):
        if not restore:
            return _tables(enumerate(nested(items), 1))
        restored = _restore_tables(items)
        return nested([restored[n] for n in range(1, len(restored) + 1)])
    for audit in result["audits"]:
        audit["claims"] = convert(audit["claims"])
    for field in ("heading_reviews", "source_checks", "issues"):
        result[field] = convert(result[field])
    return result


def request(inputs, *, state=None):
    from app.evaluation.golden_computed_evidence import build
    from app.evaluation.golden_partition_policy import POLICY
    data = project(source_data(inputs))
    data.update(assigned_blocks=allocation(inputs)[int(state is not None)],
        source_catalog=typed.build_catalog(inputs).prompt_index(), computed_evidence=build(inputs))
    if state is not None:
        check_state(state, inputs)
        value = strict_json(state.value_json)
        projected = table_partial(value)
        if table_partial(projected, restore=True) != value:
            raise ValueError("partition_first_projection_loss")
        data.update(first_partial=projected, first_diagnostics=list(state.diagnostics),
            issue_ids=[f"i{i:03}" for i in range(1, len(value["issues"]) + 1)])
    phase = "computed_partition_final" if state else "computed_partition_first"
    model = FinalPartial if state else Partial
    contract = contract_for_model(name=phase, version="1.0.0", output_model=model)
    source = data.pop("deterministic_source_facts")
    instruction = ("本次是第二批，核查首批意见和全部上下文后给最终整篇裁决。" if state else
                   "本次是首批，只交本批临时判断及发现的问题，不给整篇裁决。")
    return budget_check(ChatRequest(messages=(
        ChatMessage(role=MessageRole.SYSTEM, content=POLICY + "\n" + instruction),
        ChatMessage(role=MessageRole.USER, content=schema_notation(contract.schema_dict()) +
            "\n[UNTRUSTED DATA]\n" + compact(data) + "\n[END UNTRUSTED DATA]"),
        ChatMessage(role=MessageRole.USER, content="[UNTRUSTED deterministic_source_facts]\n" + source +
            "\n[END UNTRUSTED deterministic_source_facts]")),
        response_contract=contract, max_tokens=32768, timeout_s=300, temperature=1.0, top_p=.95,
        metadata={"harness_step": "evaluate", "review_phase": phase}))


def expand_operands(value, inputs):
    result, ledger = deepcopy(value), []
    groups = typed.comparison.catalog(inputs)["cohorts"]
    for ai, audit in enumerate(result["audits"]):
        for ci, claim in enumerate(audit["claims"]):
            for field in ("comparisons", "summaries"):
                for oi, calc in enumerate(claim[field]):
                    group = groups.get(calc["cohort"])
                    if not group or not group["complete"]:
                        raise ValueError("partition_selected_cohort_incomplete")
                    if "operand_refs" in calc:
                        raise ValueError("partition_wire_operands_forbidden")
                    members = sorted(group["wins"] + group["losses"])
                    calc["operand_refs"] = members
                    ledger.append(dict(location=[ai, ci, field, oi], cohort=calc["cohort"], members=members))
    return result, ledger


def expand_source_kinds(value, inputs):
    result, ledger = deepcopy(value), []
    catalog = typed.build_catalog(inputs)
    references = []
    for i, check in enumerate(result["source_checks"]):
        references += [(["source_checks", i, "sources", j], source) for j, source in enumerate(check["sources"])]
        references += [(["source_checks", i, "literals", j, "source"], item["source"])
            for j, item in enumerate(check["literals"])]
    for i, resolution in enumerate(result["issue_resolutions"]):
        references += [(["issue_resolutions", i, "sources", j], source) for j, source in enumerate(resolution["sources"])]
    for location, source in references:
        if "kind" in source:
            raise ValueError("partition_wire_source_kind_forbidden")
        source["kind"] = catalog.get(source["key"]).kind
        ledger.append(dict(location=location, key=source["key"], kind=source["kind"]))
    return result, ledger


def apply(state, raw, *, inputs):
    check_state(state, inputs)
    assigned = allocation(inputs)
    before = strict_json(state.value_json)
    second = strict_json(normalize_json(raw))
    FinalPartial.model_validate(second, strict=True)
    check_inventory(second, inputs, assigned[1])
    corrected = deepcopy(before)
    seen = set()
    for replacement in second["replacements"]:
        block = replacement["block"]
        if block in seen or block not in assigned[0]:
            raise ValueError("partition_replacement_invalid")
        seen.add(block)
        heading = replacement["heading_review"]
        part = dict(audits=replacement["audits"], source_checks=replacement["source_checks"],
            heading_reviews=[heading] if heading else [], issues=[])
        Partial.model_validate(part, strict=True)
        check_inventory(part, inputs, [block])
        for old, new in zip(corrected["audits"], part["audits"], strict=True):
            old["claims"] = [c for c in old["claims"] if c["quote_ref"]["block"] != block] + new["claims"]
        corrected["source_checks"] = [c for c in corrected["source_checks"] if c["quote_ref"]["block"] != block] + part["source_checks"]
        corrected["heading_reviews"] = [h for h in corrected["heading_reviews"] if h["block_id"] != block] + part["heading_reviews"]
    corrected["heading_reviews"].sort(key=lambda h: h["block_id"])
    merged = {k: deepcopy(second[k]) for k in ("score", "verdict", "summary", "passed_checks", "issues", "issue_resolutions")}
    merged.update(source_digest=inputs.source.source_digest, reviewed_blocks=list(range(1, len(inputs.source.blocks) + 1)),
        heading_reviews=corrected["heading_reviews"] + second["heading_reviews"],
        audits=[dict(kind=a["kind"], claims=a["claims"] + b["claims"])
                for a, b in zip(corrected["audits"], second["audits"], strict=True)],
        source_checks=corrected["source_checks"] + second["source_checks"])
    # Strictly validate the complete wire before host-derived operand expansion.
    complete_wire = dict(merged)
    for key in ("source_digest", "reviewed_blocks"):
        complete_wire.pop(key)
    FinalPartial.model_validate(dict(complete_wire, replacements=[]), strict=True)
    native, ledger = expand_operands(merged, inputs)
    native, source_ledger = expand_source_kinds(native, inputs)
    obligations = [("host_full_body", SimpleNamespace(quote_ref=QuoteRef(block=b))) for b in body_blocks(inputs)]
    result, journal = typed.finalize(compact(native), inputs=inputs, old_rows=obligations,
        old_issues=before["issues"], first_raw=state.raw, diagnostics=state.diagnostics)
    journal.update(experiment=EXPERIMENT_ID, first_raw=state.raw, final_raw=raw,
        first_raw_sha256=digest(state.raw), final_response_sha256=digest(raw),
        input_sha256=digest(inputs.data_json), assigned_blocks=assigned,
        provisional_values=before, replacements=second["replacements"], operand_expansion=ledger,
        source_kind_expansion=source_ledger,
        native_final=compact(native), semantic_approval=False, live_qualified=False)
    return result, journal


class ComputedPartitionWorkflow(typed.TypedReviewWorkflow):
    first_phase = "computed_partition_first"
    correction_phase = "computed_partition_final"
    prepare_state = staticmethod(prepare)
    build_first = staticmethod(request)
    merge_correction = staticmethod(apply)

    @staticmethod
    def build_correction(state):
        return PreparedCorrection(state, request(state.inputs, state=state))

    def build_revision(self, req, canonical, inputs):
        verified, journal = apply(prepare(self.last_journal["first_raw"], inputs),
            self.last_journal["final_raw"], inputs=inputs)
        if verified != canonical:
            raise ValueError("partition_revision_evaluation_changed")
        review = typed.TypedReview.model_validate(strict_json(journal["native_final"]), strict=True)
        return revision_request(inputs, review, FULL_CONTEXT_RULE + typed.REVISION_POLICY,
            comparison_review=dict(source_catalog=typed.build_catalog(inputs).prompt_index()))
