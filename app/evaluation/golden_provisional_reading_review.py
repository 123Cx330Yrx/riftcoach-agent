"""Advisory first reading; host-owned complete body coverage and strict final.

Untrusted first output must be complete unambiguous JSON with identifiable
readings/issues. Schema/location defects are retained as diagnostics, not
rewritten opinions or accepted facts. Final validation remains strict.
"""
from dataclasses import dataclass, replace
from copy import deepcopy
import re
from types import SimpleNamespace

from app.evaluation import golden_grounded_reading_review as first
from app.evaluation import golden_meaning_first_review as meaning
from app.evaluation import golden_typed_review as typed
from app.evaluation.golden_bounded_correction_requests import PreparedCorrection, _request, budget_check, source_data
from app.evaluation.golden_contextual_requests import project, _tables, _restore_tables, revision_request
from app.evaluation.golden_contextual_correction import FULL_CONTEXT_RULE
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_review_experiment import QuoteRef, compact, digest
from app.evaluation.golden_schema_notation import schema_notation

EXPERIMENT_ID = "golden-provisional-reading-review-v1"
LIVE_STATUS = "offline_only"
LIVE_BLOCK_REASON = "provisional_reading_final_review_deadline"


def require_live_qualification():
    if LIVE_STATUS != "bounded_development_after_exact_ci":
        raise ValueError(LIVE_BLOCK_REASON or "provisional_reading_requires_qualification")


@dataclass(frozen=True)
class State:
    raw: str
    inputs: object
    value_json: str
    diagnostics: tuple


def first_request(inputs):
    # Same proposed reading schema and task as the grounded candidate. This
    # change is about advisory admission and final coverage, not another hint.
    request = first.first_request(inputs)
    return replace(request, metadata={**request.metadata, "review_phase": "provisional_report_reading"})


def body_blocks(inputs):
    return [i for i, (_, text) in enumerate(inputs.source.blocks, 1)
        if not re.match(r"^#{1,6}\s", text)]


def prepare(raw, inputs):
    value, repeated = first.provisional_json(raw)
    if not isinstance(value, dict) or not isinstance(value.get("readings"), list) or not isinstance(value.get("issues"), list):
        raise ValueError("provisional_reading_inventory_required")
    if any(isinstance(i, dict) and i.get("category") == "prompt_injection" and i.get("severity") == "high"
           for i in value["issues"]):
        raise ValueError("correction_security_terminal")
    if len(value["readings"]) > 64 or len(value["issues"]) > 16:
        raise ValueError("provisional_reading_capacity_exceeded")
    diagnostics = list(repeated)
    try:
        first.ReportReading.model_validate(value, strict=True)
    except ValueError as error:
        diagnostics.extend(dict(code=e["type"], location=list(e["loc"]))
            for e in error.errors(include_input=False, include_context=False))
    mentioned = set()
    for field in ("readings", "issues"):
        for n, row in enumerate(value[field]):
            if not isinstance(row, dict):
                raise ValueError("provisional_reading_object_required")
            # The issue/source block must be a real host coordinate. Other
            # malformed fields remain raw data for explicit correction.
            ref = row.get("quote_ref")
            if (not isinstance(ref, dict) or type(ref.get("block")) is not int or
                    not 1 <= ref["block"] <= len(inputs.source.blocks)):
                raise ValueError("provisional_reading_unknown_block")
            mentioned.add(ref["block"])
            try:
                inputs.source.resolve(ref)
            except ValueError:
                diagnostics.append(dict(code="invalid_first_reference_retained", location=[field, n, "quote_ref"]))
            contexts = row.get("context_refs", [])
            if isinstance(contexts, list):
                for j, context in enumerate(contexts):
                    try: inputs.source.resolve(context)
                    except (ValueError, TypeError):
                        diagnostics.append(dict(code="invalid_first_context_retained", location=[field, n, "context_refs", j]))
    missing = sorted(set(body_blocks(inputs)) - mentioned)
    if missing:
        diagnostics.append(dict(code="first_body_blocks_omitted", blocks=missing))
    return State(raw, inputs, compact(value), tuple(diagnostics))


def _check(state, inputs):
    if state.inputs != inputs or prepare(state.raw, inputs) != state:
        raise ValueError("provisional_reading_state_changed")


POLICY = meaning.EVIDENCE_POLICY.split("\nreading_tables按", 1)[0].replace(
    "reading_tables的quote_ref保护首步原文字符，可合并、拆分、纠正类别，不得删错误尾句、换源或清空判断求通过；仍检查全文遗漏。",
    "required_body_blocks由程序列出全部正文段。每段全部原文须由最终audits/source_checks的quote_ref共同覆盖；不可因首读漏句、错定位或无结论而漏掉正文。标题仍逐项heading_reviews，有断言的标题须audit。"
) + """
reading_tables保留全部首读假说，interpretation不是事实或答案。先独立审查每个正文段，再核对首读；须纠正错误解释而非只修格式。first_diagnostics描述首读缺陷，不是报告错误。previous_issues原值即使格式错误也须逐条处置，i编号见issue_ids。
优先整段quote_ref；拆分时须覆盖全部字符（含列表前缀与结尾），同段多个事实、假设与条件均须处理。最终结构严格，不得重复键。全部原始资料已提供，没有预计算比较答案导航。
"""


def second_request(state):
    _check(state, state.inputs)
    value = strict_json(state.value_json)
    data = source_data(state.inputs)
    readings = project_readings(value["readings"])
    tables = _tables(enumerate(readings, 1))
    restored = _restore_tables(tables)
    restored = dict(enumerate(restore_readings([restored[i] for i in range(1, len(readings) + 1)]), 1))
    if [restored[i] for i in range(1, len(value["readings"]) + 1)] != value["readings"]:
        raise ValueError("provisional_reading_projection_loss")
    data.update(reading_tables=tables, previous_issues=value["issues"],
        issue_ids=[f"i{i:03}" for i in range(1, len(value["issues"]) + 1)],
        first_extra={k: v for k, v in value.items() if k not in ("readings", "issues")},
        diagnostic_groups=project_diagnostics(state.diagnostics), required_body_blocks=body_blocks(state.inputs),
        source_catalog=typed.build_catalog(state.inputs).prompt_index())
    restored_diagnostics = {i: dict(row, code=code) for code, tables in data["diagnostic_groups"]
        for i, row in _restore_tables(tables).items()}
    if [restored_diagnostics[i] for i in range(1, len(state.diagnostics) + 1)] != list(state.diagnostics):
        raise ValueError("provisional_diagnostics_projection_loss")
    policy = POLICY.replace("first_diagnostics", "diagnostic_groups") + """
首读引用用[block,head?,tail?]保留原值；其余形状用{unparsed:原值}。diagnostic_groups为[code,tables]组，tables按columns还原rows的[序号,值数组]后补入code，按序号排序；reading_tables同法还原。首读引用不保证有效。
"""
    request = _request(project(data), policy, typed.TypedReview, "provisional_evidence_review")
    schema = compact(request.response_contract.schema_dict())
    message = request.messages[1]
    if not message.content.startswith(schema + "\n"):
        raise ValueError("provisional_reading_schema_message_changed")
    message = replace(message, content=schema_notation(request.response_contract.schema_dict()) + message.content[len(schema):])
    return budget_check(replace(request, messages=(request.messages[0], message, *request.messages[2:])))


def _reference_projection(value, *, restore=False):
    if restore:
        return value["unparsed"] if isinstance(value, dict) else dict(zip(("block", "head", "tail"), value, strict=False))
    if isinstance(value, dict) and set(value) in ({"block"}, {"block", "head"}, {"block", "head", "tail"}):
        return [value[key] for key in ("block", "head", "tail") if key in value]
    return {"unparsed": value}


def project_readings(readings, *, restore=False):
    result = deepcopy(readings)
    for row in result:
        row["quote_ref"] = _reference_projection(row["quote_ref"], restore=restore)
        if isinstance(row.get("context_refs"), list):
            row["context_refs"] = [_reference_projection(ref, restore=restore) for ref in row["context_refs"]]
    return result


def restore_readings(readings):
    return project_readings(readings, restore=True)


def project_diagnostics(diagnostics):
    groups = {}
    for i, row in enumerate(diagnostics, 1):
        groups.setdefault(row["code"], []).append((i, {k: v for k, v in row.items() if k != "code"}))
    return [[code, _tables(rows)] for code, rows in groups.items()]


def apply(state, raw, *, inputs):
    _check(state, inputs)
    value = strict_json(state.value_json)
    obligations = body_blocks(inputs)
    # Final heading_reviews covers every heading. A provisional reading cannot
    # force a navigation heading into a factual audit; assertion headings must
    # still pass the final validator's complete assertion coverage check.
    rows = [("host_full_body", SimpleNamespace(quote_ref=QuoteRef(block=b))) for b in obligations]
    result, journal = typed.finalize(raw, inputs=inputs, old_rows=rows, old_issues=value["issues"],
        first_raw=state.raw, diagnostics=state.diagnostics)
    journal.update(experiment=EXPERIMENT_ID, required_body_blocks=body_blocks(inputs),
        first_parse_diagnostics=state.diagnostics, reading_hypotheses=value,
        input_sha256=digest(inputs.data_json), first_raw_sha256=digest(state.raw))
    return result, journal


class ProvisionalReadingWorkflow(first.GroundedReadingWorkflow):
    first_phase = "provisional_report_reading"
    correction_phase = "provisional_evidence_review"
    prepare_state = staticmethod(prepare)
    build_first = staticmethod(first_request)
    merge_correction = staticmethod(apply)

    @staticmethod
    def build_correction(state):
        return PreparedCorrection(state, second_request(state))

    def build_revision(self, req, canonical, inputs):
        verified, _ = apply(prepare(self.last_journal["first_raw"], inputs), self.last_journal["final_raw"], inputs=inputs)
        if verified != canonical:
            raise ValueError("provisional_reading_revision_evaluation_changed")
        review = typed.full._read(self.last_journal["final_raw"], inputs, typed.TypedReview)
        return revision_request(inputs, review, FULL_CONTEXT_RULE + typed.REVISION_POLICY,
            comparison_review=dict(source_catalog=typed.build_catalog(inputs).prompt_index()))
