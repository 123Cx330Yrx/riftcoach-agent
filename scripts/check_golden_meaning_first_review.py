"""Offline whole-report meaning-first comparison; no model or live success."""
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path

from app.evaluation import golden_meaning_first_review as candidate
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from app.harness.steps import EvaluationRequest, RevisionRequest
from app.providers.models import ChatResponse, TokenUsage
from scripts.check_golden_reassessment_feasibility import measured
from scripts.check_golden_typed_review import projection, rebind, issue, RAW_PATH
from scripts.run_golden_context_controls import load_inputs, UTTERANCE
from scripts.run_golden_contextual_review import select_cases


# Analyst-authored development fixtures. These are never imported by the live
# runner or first-request builder; they only simulate first-response content.
READINGS = {
    3: "本段分别描述全体混合样本和中单子样本；经济/伤害逐行关系限于四场中单，补刀又区分混合与同位置；早期死亡比较是混合组。",
    5: "主体是四场中单的平均表现以及其中一场艾尼维亚；结果较好不等于防抓或对线能力优秀。",
    6: "这两场胜局各自与含自身的整体样本均值对照，不是完整胜负组逐行比较。",
    7: "描述单场辅助视野结果，并否定其独自证明意识或与中单混评。",
    10: "延续总体结论中的四场中单经济与伤害比较；泛称标题不另建混合位置集合。",
    11: "举出两场不同位置的极端结果；单英雄一场的样本不支持英雄强弱判断。",
    13: "表格明确比较五局混合位置样本的赢输均值，需要结合后文的位置构成说明。",
    14: "先解释混合表格，再给同位置中单对照；对艾尼维亚的参团解释是待验证假设，未断言因果。",
    16: "选择两场中单作一负一胜的单局对照，观察潜在原因；不是全部中单赢输组的均值比较。",
    17: "提出参团时机和资源分配是否有关的问题并明确留作假设。",
    18: "当期外部快照中的排名和胜率只用于提出条件性验证问题，不解释历史输赢。",
    20: "训练目标未指定，因此接下来的方案没有被玩家采用。",
    21: "若选择中单，以全部四场中单补刀中位数及早期死亡整体均值为自我基线；不指胜負组均值。",
    22: "若选择辅助，结合一场辅助结果和外部当前快照提出验证问题；不是固定训练决定。",
    23: "训练选项不改写历史比赛位置，也不据此判断长期主位置或补位意图。",
    25: "分别声明玩家比赛资料来源、静态名称映射版本和样本限制；静态版本不是比赛版本。",
    26: "列出知识引用编号及相应文件和章节，需对照所给知识元数据。",
    27: "区分外部当前快照与官方补丁发布时间；声明没有补丁正文，不能作平衡性结论。",
    28: "列出缺少录像而无法判断的细节，是来源边界声明。",
}


def fixture_reading(value, inputs, *, original_inputs=None):
    rows, seen = [], set()
    for row in [c for a in value["audits"] for c in a["claims"]] + value["source_checks"]:
        quote = row["quote_ref"]
        identity = compact(quote)
        if identity in seen: continue
        seen.add(identity)
        block = quote["block"]
        # Negative report includes one extra standalone paragraph. Resolve
        # identity through exact text rather than assume stable numeric IDs.
        if original_inputs:
            text = inputs.source.resolve(quote)
            try: block = original_inputs.source.reference(text)["block"]
            except ValueError: block = 10
        rows.append(dict(quote_ref=quote, context_refs=[row["scope_source"]] if row.get("scope_source") else [],
            interpretation=READINGS[block]))
    return dict(report_sha256=digest(inputs.source.report), reviewed_blocks=list(range(1, len(inputs.source.blocks) + 1)),
        readings=rows, issues=[])


def fixtures(args):
    summary, source, knowledge, cases = load_inputs(args.source_run, args.base_report)
    controls = select_cases(cases)
    reqs = [EvaluationRequest(summary, source, knowledge, c["report"], UTTERANCE) for c in controls]
    inputs = [candidate.MeaningFirstWorkflow.build_inputs(r) for r in reqs]
    original = strict_json(strict_json(RAW_PATH.read_bytes())["content"])
    positive = projection(original, inputs[0])
    negative = rebind(positive, inputs[0], inputs[1], controls[0]["target"], controls[1]["target"])
    target = inputs[1].source.reference(controls[1]["target"])
    row = next(c for a in negative["audits"] for c in a["claims"] if c["quote_ref"] == target)
    row.update(decision="beyond_sample", scope_source=None, comparisons=[],
        explanation="该句把有限样本关系外推为未来必然，前文四场样本限定不能证明它。")
    negative.update(score=70, verdict="needs_revision", issues=[issue(inputs[1], target["block"])])
    values = [positive, negative]
    readings = [fixture_reading(positive, inputs[0]), fixture_reading(negative, inputs[1], original_inputs=inputs[0])]
    # Deliberately wrong first understanding: the final stage must be allowed to
    # correct it, not preserve an interpretation as if it were evidence.
    for i, reading in enumerate(readings):
        ref = inputs[i].source.reference(controls[i]["target"])
        row = next(r for r in reading["readings"] if r["quote_ref"] == ref)
        row["interpretation"] = ("错误的脚本首读：按五场混合样本理解经济和伤害差异。" if i == 0
            else "错误的脚本首读：把未来都会如此误当成前文有限样本内的观察。")
    return controls, reqs, inputs, values, readings


def audit(args):
    controls, reqs, inputs, values, readings = fixtures(args)
    shapes = []
    for control, current, value, reading in zip(controls, inputs, values, readings, strict=True):
        state = candidate.prepare(compact(reading), current)
        result, journal = candidate.apply(state, compact(value), inputs=current)
        shapes.append(dict(case_id=control["id"], report_sha256=digest(current.source.report),
            scripted_final_verdict=result.verdict, first=measured(candidate.first_request(current)),
            second=measured(candidate.second_request(state)), first_readings=len(reading["readings"]),
            protected_spans=len(journal["source_coverage"]), first_reading_intentionally_wrong=True))
    growth = []
    for count, length in ((25, 80), (30, 70), (32, 80), (25, 140)):
        expanded = deepcopy(readings[0])
        expanded["readings"] = (expanded["readings"] * 3)[:count]
        for row in expanded["readings"]:
            row["interpretation"] = ("额外语义内容，仅作输入尺寸测量。" * 10)[:length]
        try:
            ceiling = measured(candidate.second_request(candidate.prepare(compact(expanded), inputs[0])))
            growth.append(dict(readings=count, chars_each=length, input_ceiling=ceiling, admitted=True))
        except ValueError as error:
            if str(error) != "bounded_correction_request_budget_exceeded": raise
            growth.append(dict(readings=count, chars_each=length, admitted=False, provider_called=False))
    replies = [compact(readings[1]), compact(values[1]), reqs[0].report, compact(readings[0]), compact(values[0])]
    requests = []
    def send(request):
        requests.append(request)
        response = ChatResponse(provider="offline-script", model="synthetic", content=replies[len(requests)-1],
            finish_reason="stop", usage=TokenUsage(input_tokens=0, output_tokens=0))
        return Exchange(request, response, hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())
    flow = candidate.MeaningFirstWorkflow(send)
    initial = flow.evaluate(reqs[1])
    revised = flow.revise(RevisionRequest(reqs[1].player_summary, reqs[1].deterministic_report, reqs[1].knowledge, reqs[1].report, initial))
    final = flow.evaluate(replace(reqs[1], report=revised.report))
    assert final.verdict.value == "pass" and flow.calls == 5
    old = strict_json(Path("data/evaluation/results/golden_typed_review_offline_v1.json").read_text(encoding="utf-8"))
    for file, expected in old["source_hashes"].items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != expected: raise ValueError("historical_receipt_changed")
    phases = [dict(phase=r.metadata["review_phase"], input_ceiling=measured(r), output_reservation=r.max_tokens) for r in requests]
    return dict(experiment=candidate.EXPERIMENT_ID, provider_calls=0, synthetic_only=True,
        semantic_approval=False, live_qualified=False, shapes=shapes, synthetic_growth=growth,
        structural_benefits=["first_reading_cannot_access_source_arithmetic", "wrong_first_interpretation_is_correctable",
            "native_final_review_retained", "same_five_call_workflow"],
        full_scripted_path=dict(phases=phases, all_inputs_within_limit=all(p["input_ceiling"] <= 63936 for p in phases),
            conservative_input_plus_full_output=sum(p["input_ceiling"] + p["output_reservation"] for p in phases),
            limit=401920, admission="actual_usage_plus_next_reservation", live_time_verified=False),
        previous_typed_path=old["scripted_full_revision_path"]["phases"], source_hashes=old["source_hashes"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-run", "base-report", "output"): parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = audit(args)
    write_new_json(args.output, result)
    print(compact({k: result[k] for k in ("shapes", "full_scripted_path", "semantic_approval")}))


if __name__ == "__main__": main()
