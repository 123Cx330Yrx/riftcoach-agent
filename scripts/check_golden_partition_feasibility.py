"""Offline two-part review feasibility; synthetic witnesses, never a live entry.

Host assigns ordered source blocks, both requests retain all original context.
Only the second response owns the global verdict; explicit edits preserve first
judgments by default. Final validation reuses the unchanged TypedReview contract.
Run prints evidence only; it does not write receipts or call any Provider.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import re
from types import SimpleNamespace
from typing import Literal

from pydantic import Field
from jsonschema import Draft202012Validator

from app.evaluation import golden_typed_review as typed
from app.evaluation.golden_bounded_correction_requests import UntitledSchema, _request, source_data
from app.evaluation.golden_context_review import HeadingRef, IssueRef
from app.evaluation.golden_contextual_correction import FULL_CONTEXT_RULE
from app.evaluation.golden_contextual_requests import project, restore, _tables, _restore_tables, revision_request
from app.evaluation.golden_integrated_review import Strict
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_review_experiment import QuoteRef, compact, digest
from app.evaluation.golden_schema_notation import schema_notation
from scripts.check_golden_meaning_first_review import fixtures, measured
from scripts.check_golden_provisional_reading_review import whole_body_fixture
from scripts.check_golden_typed_review import rebind, issue


class Partial(UntitledSchema, Strict):
    heading_reviews: list[HeadingRef] = Field(max_length=64)
    audits: list[typed.TypedAudit] = Field(min_length=2, max_length=2)
    source_checks: list[typed.SourceCheck] = Field(max_length=32)
    issues: list[IssueRef]


class BlockReplacement(Strict):
    block: int = Field(ge=1, le=64)
    heading_review: HeadingRef | None
    audits: list[typed.TypedAudit] = Field(min_length=2, max_length=2)
    source_checks: list[typed.SourceCheck] = Field(max_length=32)


class FinalPartial(Partial):
    # Entire blocks can regroup or change lanes; old claim counts don't bind
    # correction capacity. Original issues are a separate global obligation.
    replacements: list[BlockReplacement] = Field(max_length=64)
    issue_resolutions: list[typed.TypedResolution]
    score: int = Field(ge=0, le=100)
    verdict: Literal["pass", "needs_revision", "fail"]
    summary: str = Field(min_length=1, max_length=1200)
    passed_checks: list[str] = Field(max_length=12)


def allocation(inputs):
    body = [i for i, (_, text) in enumerate(inputs.source.blocks, 1) if not re.match(r"^#{1,6}\s", text)]
    cut = body[(len(body) + 1) // 2 - 1]
    return [list(range(1, cut + 1)), list(range(cut + 1, len(inputs.source.blocks) + 1))]


def split_fixture(value, blocks, *, final=False):
    result = dict(heading_reviews=[deepcopy(h) for h in value["heading_reviews"] if h["block_id"] in blocks],
        audits=[dict(kind=a["kind"], claims=[deepcopy(c) for c in a["claims"] if c["quote_ref"]["block"] in blocks])
                for a in value["audits"]],
        source_checks=[deepcopy(c) for c in value["source_checks"] if c["quote_ref"]["block"] in blocks],
        issues=[deepcopy(i) for i in value["issues"] if i["quote_ref"]["block"] in blocks])
    if final:
        # Final issues are global. Any first issue absent here needs a resolution.
        result.update({k: deepcopy(value[k]) for k in ("issues", "score", "verdict", "summary", "passed_checks")})
        result.update(replacements=[], issue_resolutions=[])
    return result


def _rows(value):
    return [c for a in value["audits"] for c in a["claims"]] + value["source_checks"]


def _partial_check(raw, inputs, blocks, model, *, provisional=False):
    value = strict_json(raw)
    if not isinstance(value, dict) or any(not isinstance(value.get(k), list)
            for k in ("audits", "heading_reviews", "source_checks", "issues")):
        raise ValueError("partition_inventory_required")
    if not provisional: model.model_validate(value, strict=True)
    if [a["kind"] for a in value["audits"]] != ["metric_to_ability", "cohort_comparison"]:
        raise ValueError("partition_audit_inventory")
    if not provisional and [h["block_id"] for h in value["heading_reviews"]] != [
            b for b in blocks if re.match(r"^#{1,6}\s", inputs.source.blocks[b-1][1])]:
        raise ValueError("partition_heading_inventory")
    for row in _rows(value):
        if (not isinstance(row, dict) or not isinstance(row.get("quote_ref"), dict)
                or type(row["quote_ref"].get("block")) is not int or row["quote_ref"]["block"] not in blocks):
            raise ValueError("partition_primary_outside_assignment")
        if not provisional: inputs.source.resolve(row["quote_ref"])
    for row in value["issues"]:
        if row["category"] == "prompt_injection" and row["severity"] == "high":
            raise ValueError("correction_security_terminal")
        if not provisional: inputs.source.resolve(row["quote_ref"])
    return value


def first_diagnostics(value):
    try: Partial.model_validate(value, strict=True)
    except ValueError as error:
        return [dict(code=e["type"], location=list(e["loc"])) for e in error.errors(include_input=False, include_context=False)]
    return []


def merge(first_raw, second_raw, inputs):
    assigned = allocation(inputs)
    before = _partial_check(first_raw, inputs, assigned[0], Partial, provisional=True)
    second = _partial_check(second_raw, inputs, assigned[1], FinalPartial)
    corrected = deepcopy(before)
    seen = set()
    for replacement in second["replacements"]:
        block = replacement["block"]
        if block in seen or block not in assigned[0]: raise ValueError("partition_replacement_invalid")
        seen.add(block)
        heading = replacement["heading_review"]
        part = dict(audits=replacement["audits"], source_checks=replacement["source_checks"],
            heading_reviews=[heading] if heading else [], issues=[])
        _partial_check(compact(part), inputs, [block], Partial)
        for target, fresh in zip(corrected["audits"], part["audits"], strict=True):
            target["claims"] = [c for c in target["claims"] if c["quote_ref"]["block"] != block] + fresh["claims"]
        corrected["source_checks"] = [c for c in corrected["source_checks"] if c["quote_ref"]["block"] != block] + part["source_checks"]
        corrected["heading_reviews"] = [h for h in corrected["heading_reviews"] if h["block_id"] != block] + part["heading_reviews"]
    corrected["heading_reviews"].sort(key=lambda h: h["block_id"])
    merged = {k: deepcopy(second[k]) for k in ("score", "verdict", "summary", "passed_checks", "issues", "issue_resolutions")}
    merged.update(source_digest=inputs.source.source_digest,
        reviewed_blocks=list(range(1, len(inputs.source.blocks) + 1)),
        heading_reviews=corrected["heading_reviews"] + second["heading_reviews"],
        audits=[dict(kind=a["kind"], claims=a["claims"] + b["claims"])
                for a, b in zip(corrected["audits"], second["audits"], strict=True)],
        source_checks=corrected["source_checks"] + second["source_checks"])
    body = [b for group in assigned for b in group if not re.match(r"^#{1,6}\s", inputs.source.blocks[b-1][1])]
    obligations = [("host_full_body", SimpleNamespace(quote_ref=QuoteRef(block=b))) for b in body]
    result, journal = typed.finalize(compact(merged), inputs=inputs, old_rows=obligations,
        old_issues=before["issues"], first_raw=first_raw, diagnostics=first_diagnostics(before))
    return result, journal, merged


def table_partial(value, *, restore_value=False):
    result = deepcopy(value)
    def convert(rows):
        if not restore_value: return _tables(enumerate(rows, 1))
        restored = _restore_tables(rows)
        return [restored[i] for i in range(1, len(restored) + 1)]
    for audit in result["audits"]: audit["claims"] = convert(audit["claims"])
    for field in ("heading_reviews", "source_checks", "issues"): result[field] = convert(result[field])
    return result


def operand_projection(value, inputs, *, restore_value=False):
    """Only exact full-cohort operands are derivable; model still selects cohort.

    This is a reversible representation experiment, not a natural-language
    selection heuristic or a new proof of semantic correctness.
    """
    result = deepcopy(value)
    groups = typed.comparison.catalog(inputs)["cohorts"]
    count = 0
    for audit in result["audits"]:
        for claim in audit["claims"]:
            for calc in claim["comparisons"] + claim["summaries"]:
                group = groups[calc["cohort"]]
                members = sorted(group["wins"] + group["losses"])
                if not group["complete"]: raise ValueError("partition_members_incomplete")
                if restore_value:
                    # Order is preserved too, so projection remains exact, not
                    # merely equivalent under the current set validator.
                    calc["operand_refs"] = [members[i] for i in calc.pop("operand_order")]
                else:
                    original = calc.pop("operand_refs")
                    if len(original) != len(set(original)) or set(original) != set(members):
                        raise ValueError("partition_noncanonical_members")
                    calc["operand_order"] = [members.index(i) for i in original]
                count += 1
    return result, count


def operand_wire_schema(model):
    schema = model.model_json_schema()
    for name in ("Comparison", "SummaryCalculation"):
        node = schema["$defs"][name]
        node["properties"].pop("operand_refs")
        node["required"].remove("operand_refs")
    return schema


def host_operands(value, inputs, *, expand=False):
    """A distinct wire omits members, which host derives from chosen full cohort.

    No cohort, metric, operation, reported value, evidence ref or explanation is
    inferred. All alternatives stay in context. Original order is audit data;
    the new wire defines expansion in source-index order, not model order.
    """
    result, ledger = deepcopy(value), []
    groups = typed.comparison.catalog(inputs)["cohorts"]
    portions = [("body", result), *[(f"replacement/{i}", p) for i, p in enumerate(result.get("replacements", []))]]
    for location, portion in portions:
        for ai, audit in enumerate(portion["audits"]):
            for ci, claim in enumerate(audit["claims"]):
                for field in ("comparisons", "summaries"):
                    for oi, calc in enumerate(claim[field]):
                        group = groups.get(calc["cohort"])
                        if not group or not group["complete"]: raise ValueError("partition_members_incomplete")
                        members = sorted(group["wins"] + group["losses"])
                        if expand:
                            if "operand_refs" in calc: raise ValueError("partition_unexpected_wire_operands")
                            calc["operand_refs"] = members
                        else:
                            supplied = calc.pop("operand_refs")
                            if len(supplied) != len(set(supplied)) or set(supplied) != set(members):
                                raise ValueError("partition_noncanonical_members")
                        ledger.append(dict(location=[location, ai, ci, field, oi],
                            selected_cohort=calc["cohort"], metric=calc["metric"], expanded_operands=members))
    return result, ledger


def arithmetic_ledger(prior, inputs):
    """Host recomputation for model-selected operations, without semantic assent."""
    comparisons, summaries, links, errors = [], [], [], []
    def register(rows, row):
        if row not in rows: rows.append(row)
        return rows.index(row) + 1
    for ai, audit in enumerate(prior["audits"], 1):
        for ci, raw in enumerate(audit["claims"], 1):
            try:
                claim = typed.TypedClaim.model_validate(raw, strict=True)
                wire = SimpleNamespace(audits=[SimpleNamespace(kind=audit["kind"], claims=[claim])])
                bindings = typed.comparison.validate_bindings(wire, inputs, typed.comparison.catalog(inputs))[0]["bindings"]
                sums = typed.validate_summaries(wire, inputs)
            except ValueError as error:
                errors.append([ai, ci, type(error).__name__, str(error).splitlines()[0][:120]])
                continue
            cids = [register(comparisons, {k: v for k, v in b.items() if k not in ("wins", "losses")}) for b in bindings]
            sids = [register(summaries, {k: v for k, v in s.items() if k not in ("quote_ref", "operand_refs")}) for s in sums]
            if cids or sids: links.append([ai, ci, cids, sids])
    return dict(comparisons=_tables(enumerate(comparisons, 1)), summaries=_tables(enumerate(summaries, 1)),
        claim_links=links, errors=errors, semantic_approval=False)


POLICY = typed.POLICY.replace("这是第二次且最后一次完整重评。", "这是同源全文上下文下的分批审查。") + """
这是离线合同原型。host给assigned_blocks；完整报告和原始来源仍全部可见，范围引用可跨批。只为本批主句生成audits/source_checks，但其他段发现的安全/事实问题仍须列issues。正文每个字符必须被完整判断覆盖；仅覆盖字符不表示语义正确。
首批无整篇score/verdict/summary/passed_checks字段，也不能宣称整篇通过。二批first_partial逐字保留首批全部判断、解释、来源和问题，未替换块host原样保留；首批是可纠正临时意见，first_diagnostics不是报告错误。需要纠正时用replacements返回首批该block的完整替代判断，可重新拆合或换审查类别，不能删错误尾句。无论首批有无提及，最终均须覆盖全部原文和标题。
二批issues是整篇最终问题清单，首批问题消失或变更必须逐项issue_resolutions引用真实来源处置，i编号按首批issues的一基顺序。二批依据全文与合并后的全部判断给全局score/verdict/summary，不是局部分数平均。二批不要重复未修改首批内容。host最终合并并执行原TypedReview全部严格校验。
输出不抄source_digest/reviewed_blocks；这些身份/清单由host绑定。heading_reviews只列本批标题。table视图按columns恢复rows的[一基编号,值数组]，所有原值保留。
"""


def request(inputs, assigned, *, prior=None, tables=False, include_catalog=False, derive_operands=False, host_ledger=False):
    data = source_data(inputs)
    original = deepcopy(data)
    if tables:
        data = project(data)
        assert restore(data) == original
    data.update(assigned_blocks=assigned, source_catalog=typed.build_catalog(inputs).prompt_index())
    if include_catalog: data["comparison_evidence"] = typed.comparison.prompt_catalog(inputs)
    if derive_operands:
        data["complete_cohort_members"] = {key: sorted(group["wins"] + group["losses"])
            for key, group in typed.comparison.catalog(inputs)["cohorts"].items() if group["complete"]}
    if prior is not None:
        wire_prior = host_operands(prior, inputs)[0] if derive_operands else deepcopy(prior)
        data["first_partial"] = table_partial(wire_prior) if tables else wire_prior
        if tables: assert table_partial(data["first_partial"], restore_value=True) == wire_prior
        data["issue_ids"] = [f"i{i:03}" for i in range(1, len(prior["issues"]) + 1)]
        data["first_diagnostics"] = first_diagnostics(prior)
        if host_ledger: data["host_arithmetic"] = arithmetic_ledger(prior, inputs)
    built = _request(data, POLICY, Partial if prior is None else FinalPartial,
        "offline_partition_first" if prior is None else "offline_partition_final")
    schema = compact(built.response_contract.schema_dict())
    assert built.messages[1].content.startswith(schema + "\n")
    contract = built.response_contract
    if derive_operands:
        contract = replace(contract, json_schema=operand_wire_schema(Partial if prior is None else FinalPartial))
        policy = built.messages[0].content + ("\n本实验wire不输出comparisons/summaries的operand_refs；"
            "模型仍依据原文选择cohort、metric及operation/reported，host只按所选完整cohort从原始行展开成员并记审计。"
            "evidence_refs仍须实际引用这些成员，不由host补。所有cohort均可选，不能因数值同向而换样本。")
        built = replace(built, messages=(replace(built.messages[0], content=policy), *built.messages[1:]))
    if host_ledger:
        policy = built.messages[0].content + ("\nhost_arithmetic是对首批模型自行选择的运算所作的确定性复算，"
            "按tables恢复比较/汇总，claim_links为[audit一基,claim一基,比较结果编号列表,汇总结果编号列表]。"
            "已有精确结果无需再手算；必须核对原句究竟选择了哪个对象/样本/指标，及这些计算能否支持判断，"
            "数值正确不证明样本正确。errors仅计算或结构诊断，不自动等于报告错误。")
        built = replace(built, messages=(replace(built.messages[0], content=policy), *built.messages[1:]))
    message = replace(built.messages[1], content=schema_notation(contract.schema_dict()) +
        built.messages[1].content[len(schema):])
    return replace(built, response_contract=contract, messages=(built.messages[0], message, *built.messages[2:]))


def must_reject(action):
    try: action()
    except (ValueError, IndexError) as error: return str(error).splitlines()[0]
    raise AssertionError("adverse fixture unexpectedly accepted")


def audit(args):
    controls, reqs, inputs, values, _ = fixtures(args)
    values[0] = whole_body_fixture(values[0])
    values[1] = rebind(values[0], inputs[0], inputs[1], controls[0]["target"], controls[1]["target"])
    ref = inputs[1].source.reference(controls[1]["target"])
    target = next(c for a in values[1]["audits"] for c in a["claims"] if c["quote_ref"] == ref)
    target.update(decision="beyond_sample", scope_source=None, comparisons=[],
        explanation="独立未来断言超出四场中单样本所能支持的范围。")
    values[1]["audits"][1]["claims"].append(dict(quote_ref=inputs[1].source.reference("样本只有四场。"),
        decision="direct_supported", evidence_refs=[7, 9, 10, 11], comparisons=[], summaries=[],
        explanation="中单子样本确实四场，不证明后文未来断言。"))
    values[1].update(score=70, verdict="needs_revision", issues=[issue(inputs[1], ref["block"])])
    shapes, batches, requests = [], [], []
    for control, current, value in zip(controls, inputs, values, strict=True):
        groups = allocation(current)
        first, second = split_fixture(value, groups[0]), split_fixture(value, groups[1], final=True)
        result, journal, merged = merge(compact(first), compact(second), current)
        # Host sorting/interleaving is represented by final semantics, never a
        # rewrite of untouched first values or explanations.
        assert all(merged["audits"][i]["claims"][:len(a["claims"])] == a["claims"] for i, a in enumerate(first["audits"]))
        assert merged["source_checks"][:len(first["source_checks"])] == first["source_checks"]
        builds = {name: [request(current, groups[0], tables=t, include_catalog=c, derive_operands=d, host_ledger=l),
            request(current, groups[1], prior=first, tables=t, include_catalog=c, derive_operands=d, host_ledger=l)]
            for name, t, c, d, l in (("raw", False, False, False, False), ("tables", True, False, False, False),
                ("tables_with_catalog", True, True, False, False), ("host_operands", True, False, True, False),
                ("host_operands_with_catalog", True, True, True, False), ("host_operands_with_ledger", True, False, True, True))}
        first_wire, _ = host_operands(first, current)
        second_wire, _ = host_operands(second, current)
        Draft202012Validator(operand_wire_schema(Partial)).validate(first_wire)
        Draft202012Validator(operand_wire_schema(FinalPartial)).validate(second_wire)
        expanded_first, first_expansion = host_operands(first_wire, current, expand=True)
        expanded_second, second_expansion = host_operands(second_wire, current, expand=True)
        host_result, _, host_merged = merge(compact(expanded_first), compact(expanded_second), current)
        assert host_result == result
        assert host_operands(expanded_first, current)[0] == first_wire
        assert host_operands(expanded_second, current)[0] == second_wire
        projected, n = operand_projection(first, current)
        assert operand_projection(projected, current, restore_value=True)[0] == first
        shapes.append(dict(case_id=control["id"], report_sha256=digest(current.source.report),
            assigned_blocks=groups, scripted_verdict=result.verdict, final_body_spans=len(journal["source_coverage"]),
            input_ceilings={k: [measured(r) for r in rs] for k, rs in builds.items()},
            synthetic_output_chars=[len(compact(first)), len(compact(second))],
            whole_final_output_chars=len(compact(merged)), unchanged_first_values_preserved=True,
            host_arithmetic=dict(chars=len(compact(arithmetic_ledger(first, current))),
                no_semantic_approval=True, errors=arithmetic_ledger(first, current)["errors"]),
            explicit_host_operands=dict(output_chars=[len(compact(first_wire)), len(compact(second_wire))],
                expansions=len(first_expansion) + len(second_expansion), final_canonical_equal=True,
                model_selectors_and_all_other_values_preserved=True,
                expansion_ledger_sha256=digest(compact(first_expansion + second_expansion))),
            operand_projection=dict(operations=n, original_chars=len(compact(first)),
                projected_chars=len(compact(projected)), exact_roundtrip=True,
                conclusion="operand_order_kept_for_exactness; no_model_reasoning_saving_proven")))
        batches.append((first, second, merged))
        requests.append(builds)
    bad_first, bad_second, bad_merged = batches[1]
    dropped = deepcopy(bad_second); dropped["issues"] = []
    dropped.update(verdict="pass", score=95)
    # Keep a supported final claim so the old-issue disposition guard itself is
    # exercised separately from unsupported-claim/nonpass consistency.
    checks = dict(first_cannot_claim_global=must_reject(lambda: Partial.model_validate(dict(bad_first, score=100), strict=True)),
        missing_issues_rejected=must_reject(lambda: merge(compact(bad_first), compact(dropped), inputs[1])))
    first, second, _ = batches[0]
    cut = deepcopy(second)
    victim = cut["source_checks"].pop()
    checks["omitted_body_rejected"] = must_reject(lambda: merge(compact(first), compact(cut), inputs[0]))
    modified = deepcopy(first)
    chosen = next((i, c) for i, c in enumerate(modified["audits"][0]["claims"], 1) if c["quote_ref"].get("head") is None)
    edited = deepcopy(second)
    i, row = chosen
    shorter = deepcopy(row)
    text = inputs[0].source.resolve(row["quote_ref"])
    shorter["quote_ref"] = inputs[0].source.reference(text[:12])
    block = row["quote_ref"]["block"]
    part = split_fixture(batches[0][2], [block])
    part["audits"][0]["claims"] = [shorter if c["quote_ref"] == row["quote_ref"] else c for c in part["audits"][0]["claims"]]
    edited["replacements"] = [dict(block=block, heading_review=None, audits=part["audits"], source_checks=part["source_checks"])]
    checks["first_tail_deletion_rejected"] = must_reject(lambda: merge(compact(modified), compact(edited), inputs[0]))
    # Overlong wrong reference and duplicate provisional claims can be replaced
    # as a complete block, including changing lane/grouping. No old judgment is
    # silently accepted or deleted: original first bytes remain the journal.
    broken = deepcopy(first)
    old = broken["audits"][0]["claims"][i-1]
    old["quote_ref"]["head"] = "错位超长引用" * 12
    broken["audits"][0]["claims"].append(deepcopy(old))
    corrected = deepcopy(second)
    full_part = split_fixture(batches[0][2], [block])
    corrected["replacements"] = [dict(block=block, heading_review=None,
        audits=full_part["audits"], source_checks=full_part["source_checks"])]
    repaired, repair_journal, _ = merge(compact(broken), compact(corrected), inputs[0])
    assert repaired.verdict == "pass" and repair_journal["first_raw"] == compact(broken)
    checks["bad_first_whole_block_replacement"] = dict(verdict=repaired.verdict,
        diagnostics=len(first_diagnostics(broken)), raw_preserved=True,
        second_input_ceiling=measured(request(inputs[0], allocation(inputs[0])[1], prior=broken, tables=True)))
    # Add an intentionally false provisional issue, then require an explicit
    # source-backed disposal without deleting its original malformed locator.
    false_first = deepcopy(first)
    false_issue = issue(inputs[0], 20)
    false_issue["quote_ref"]["head"] = "不在原文的错误超长定位" * 8
    false_first["issues"].append(false_issue)
    resolved_second = deepcopy(second)
    resolved_second["issue_resolutions"] = [dict(target_id="i001", evidence_refs=[],
        sources=[dict(key="request/utterance", kind="user_request", path=[])],
        explanation="合成合同见证：依据实际任务原文撤销首批误报；不证明自动纠错质量。")]
    cleared, cleared_journal, _ = merge(compact(false_first), compact(resolved_second), inputs[0])
    assert cleared.verdict == "pass" and cleared_journal["resolved_issues"][0]["before"] == false_issue
    checks["malformed_first_issue_explicitly_resolved"] = dict(raw_issue_preserved=True,
        second_input_ceiling=measured(request(inputs[0], allocation(inputs[0])[1], prior=false_first,
            tables=True, derive_operands=True)), semantic_approval=False)
    revision = revision_request(inputs[1], typed.TypedReview.model_validate(bad_merged, strict=True),
        FULL_CONTEXT_RULE + typed.REVISION_POLICY,
        comparison_review=dict(source_catalog=typed.build_catalog(inputs[1]).prompt_index()))
    paths = {}
    for mode in requests[0]:
        chain = [*requests[1][mode], revision, *requests[0][mode]]
        ceilings = [measured(r) for r in chain]
        paths[mode] = dict(input_ceilings=ceilings, per_request_admitted=[n <= 63936 for n in ceilings],
            calls=5, revisions=1, conservative_input_plus_full_output=sum(ceilings) + 5 * 32768,
            total_limit=401920, admission="actual_usage_plus_next_reservation_not_sum_of_maxima",
            live_latency_verified=False, elapsed_limit_s=900)
    return dict(experiment="offline-host-partition-feasibility-v1", provider_calls=0,
        synthetic_only=True, semantic_approval=False, runtime_registered=False,
        shapes=shapes, adverse_checks=checks, five_call_shape=paths,
        limitations=["frozen_full_context_and_synthetic_values_only", "second_schema_errors_terminal_no_third_evaluation_slot",
            "block_replacements_allow_regrouping_but_large_error_sets_may_exceed_budget", "first_false_issues_need_explicit_resolution",
            "full_context_does_not_prove_cross_batch_semantic_consistency", "global_score_owned_by_second_model_not_host_math",
            "no_latency_or_actual_token_measurement", "first_complete_output_growth_may_exceed_second_input_limit"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, default=Path("data/runs/golden_slice/golden_20260910_compact_1cd694d"))
    parser.add_argument("--base-report", type=Path, default=Path("data/runs/inference_development/inference-dev-c69cb3e-evidence-v7-report/revised-report.md"))
    print(compact(audit(parser.parse_args())))


if __name__ == "__main__": main()
