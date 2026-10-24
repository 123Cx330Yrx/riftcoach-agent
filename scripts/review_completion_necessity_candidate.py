"""Offline completion-policy contrast; no sender, secrets or runtime registration.

Full reports and evidence are shared by the two arms. Evaluator expectations
and the retained failed opinion are never read by request preparation.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from app.evaluation import sol_necessity_contract as baseline
from app.evaluation.golden_native_issues_review import budget_check
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from app.evaluation.source_patch_editor import report_inputs
from scripts.prepare_reviewer_profile_screen import visible, json_value

VERSION = 'offline-completion-necessity-contrast-v1'
MARKER = 'offline_completion_necessity_contrast'
PACKAGE = baseline.ROOT/'data/evaluation/fixtures/completion_necessity_20261024'
CASES = ('a', 'b', 'c', 'd')
ARMS = ('baseline', 'candidate')

# A falsifiable decision procedure, not a role-keyword exemption, new issue
# schema, extra review call or a fix claimed to work before a real comparison.
COMPLETION_NECESSITY_POLICY = '''
[完成度必要修订判定方法]
提出issue前，先确定实际用户要求或本次既有资料消费义务，再按全文确定该义务是否已完成。区分原文实际安排的对象、动作和用途，与你认为更清晰的改写；已有直接管辖后文的限定必须一并理解，不能把未说明的对象补成另一个人，再据此判为越界。只需措辞澄清且不改变实际任务或行动时，使用既有advisories，不制造必要补丁。
限定不是豁免：若后文明确要求与用户任务相冲突的对象、用途或动作，前文的范围声明不能消除该实际冲突。缺失任务也须实查全文；已有具体行动若实际使用了所要求的资料，即使不重复在同一段，也不能再报缺失。仅列数据、仅说可研究或重复边界，仍不能代替资料到具体行动的连接。
补丁只补真实缺口及其直接影响。提交前逐项对照before与after，保留与该缺口无关且来源支持的事实、条件和观察参照；不是为了修任务完成度而删除正确数字或替换整套行动。解释和reason不能凭空添加原文没有作出的更强主张。本方法不重复裁决事实专责，不新增用户要求、输出字段或公开思考过程。
虚构展览例，仅说明方法而非报告证据：用户只要观察展品，报告先明确后文都是观展记录练习，再说“选择练习色彩，下一批作品记录两项指标”，不能仅因“练习”便补成读者必须亲自创作。若后句明确要求“你本人创作作品，并把展品数值当作个人达标线”，则是真实用途冲突，前文限定不能豁免。若另有义务要求将展品年代连到观展行动，仅列年代不够；已据年代选择一组展品并比较材料，则不能仍以没有行动报错。补这个缺口不需要删除原有、来源支持的展品尺寸。
[完成度必要修订判定结束]
'''


def encode(value):
    return (json.dumps(value, ensure_ascii=True, allow_nan=False, indent=2)+'\n').encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def materials(package=PACKAGE):
    """Read only material inputs, never labels, old outputs or Host judgments."""
    context = json.loads((package/'context.json').read_text(encoding='utf-8'))
    original = baseline.restore_context(context)
    return {case: report_inputs(original, (package/f'{case}.md').read_text(encoding='utf-8'))
            for case in CASES}


def make_request(inputs, arm='candidate', stage='initial'):
    if arm not in ARMS or stage not in ('initial', 'fresh'):
        raise ValueError('completion_contrast_arm_or_stage')
    base = baseline.make_request(inputs, 'completion', stage)
    if arm == 'baseline':
        return base
    return budget_check(replace(base,
        messages=(replace(base.messages[0], content=base.messages[0].content+COMPLETION_NECESSITY_POLICY),
                  *base.messages[1:]),
        metadata={**base.metadata, MARKER: VERSION}))


def prepare(package=PACKAGE):
    files, rows = {}, []
    for case, inputs in materials(package).items():
        for arm in ARMS:
            request = make_request(inputs, arm)
            ceiling = estimate_runtime_request_input_ceiling(request)
            if ceiling > 64000:
                raise ValueError('completion_contrast_input_ceiling')
            raw = encode(visible(json_value(request)))
            name = f'{case}-{arm}.json'
            files[name] = raw
            rows.append(dict(case=case, arm=arm, file=name,
                request_sha256=sha(raw), report_sha256=sha(inputs.source.report.encode('utf-8')),
                source_pack_sha256=sha(inputs.pack_json.encode('utf-8')),
                non_system_messages_sha256=sha(encode(json_value(request.messages[1:]))),
                tools_sha256=sha(encode(json_value(request.tools))),
                estimated_input_ceiling=ceiling, output_reservation=request.max_tokens))
    files['manifest.json'] = encode(dict(kind=VERSION,
        status='offline_material_only_not_an_execution_plan', requests=rows,
        candidate_policy_sha256=sha(COMPLETION_NECESSITY_POLICY.encode('utf-8')),
        provider_requests=0, key_reads=0, authorized=False, execution_ready=False,
        semantic_improvement_proven=False, production_admitted=False, publication_allowed=False,
        familiar_development_material=True, actual_application=False, fresh_evidence=False,
        limits=['A policy hypothesis and full-source controls, not model-quality results.',
                'Baseline and candidate differ only in system policy and an offline marker.',
                'Evaluator labels and retained opinions are excluded from model inputs.',
                'No candidate receiver, paid launcher, continuation import or new grant exists.']))
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    output = parser.parse_args().output_dir.absolute()
    if output.resolve().is_relative_to(baseline.ROOT/'data/runs'):
        raise ValueError('completion_contrast_outside_runs_required')
    files = prepare()
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        with (output/name).open('xb') as stream:
            stream.write(raw)
    print(json.dumps(dict(files=len(files), provider_requests=0, execution_ready=False), ensure_ascii=True))


if __name__ == '__main__':
    main()
