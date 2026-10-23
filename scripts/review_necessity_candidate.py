"""Offline policy candidate; no sender, credential access or runtime registration.

The historical Sol contract is unchanged. Its receivers reject this candidate's
metadata/policy rather than accepting new requests under an old version.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from app.evaluation import sol_natural_contract as baseline
from app.evaluation.golden_native_issues_review import budget_check
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from app.evaluation.source_patch_editor import report_inputs
from scripts.prepare_reviewer_profile_screen import visible, json_value

VERSION = 'offline-review-necessity-candidate-v1'
MARKER = 'offline_review_necessity_candidate'
PACKAGE = Path(__file__).resolve().parents[1] / 'data/evaluation/fixtures/review_necessity_20261023'
CASES = ('a', 'b', 'c')

# A decision procedure, not a new issue schema or a keyword-based exemption.
# Examples are outside the report's domain and cannot serve as its evidence.
NECESSITY_POLICY = '''
[必要修订判定；适用于本次全文事实审查]
提出每条issue前，先按全文及来源判断拟议补丁究竟纠正了什么实质含义：原文实际断言了什么，来源允许什么，两者在哪里冲突，或未解歧义如何影响结论或行动。将已有否定、条件、待验限定一并读入，不把作者没有作出的更强断言当成原文。
若补丁只重复已有的谨慎限定、前移范围或换成更清楚的说法，且没有改变无依据的断言或行动，不列为必要修订；可用advisories提出可选表达建议，无需为建议制造issue或补丁。解释及修法都不能把“可能误读”升级为已经存在的事实错误。
限定词不是豁免：逐个核对限定之后仍实际作出的断言、因果及行动。来源允许提出待验假设，不等于原因已证实；同样，写成条件建议也不赋予具体数值目标依据。确有独立错误时只修该错误及直接影响，保留其余正确内容。
虚构物流例（仅示范判定方法，不是报告证据）：来源只有两天延误率与一条“可查装车等待、路线安排”的排查建议，没有过程观测或达标线。报告说“延误较多，可据此选择排查线索；原因仍须查记录，不能由延误率确定”，仅再加一次“不能证明原因”没有修正实质错误。若同段又说“延误率已经证明路线安排错误”，前面的限定不能消除后句实际因果断言；须修后句。若说“如选择优化路线，下一周延误率必须低于3%”，仍须检查3%的依据，不能因条件句放过任意门槛。
以上不替代身份、来源、数字、比较范围、引用、安全及其余事实职责，不要求新增输出字段或公开思考过程。
[必要修订判定结束]
'''


def make_request(inputs, name, stage='initial'):
    base = baseline.make_request(inputs, name, stage)
    messages = base.messages
    if name == 'facts':
        messages = (replace(messages[0], content=messages[0].content + NECESSITY_POLICY), *messages[1:])
    return budget_check(replace(base, messages=messages,
        metadata={**base.metadata, MARKER: VERSION}))


def materials(package=PACKAGE):
    """Read only report/source materials; never load the evaluator sidecar."""
    context = json.loads((package / 'context.json').read_text(encoding='utf-8'))
    original = baseline.restore_context(context)
    return {case: report_inputs(original, (package / f'{case}.md').read_text(encoding='utf-8'))
            for case in CASES}


def encode(value):
    return (json.dumps(value, ensure_ascii=True, allow_nan=False, indent=2) + '\n').encode('utf-8')


def prepare(package=PACKAGE):
    """Three proposed facts-initial checks, not a new authorized paid batch."""
    files, rows = {}, []
    for case, inputs in materials(package).items():
        request = make_request(inputs, 'facts')
        size = estimate_runtime_request_input_ceiling(request)
        if size > 64000:
            raise ValueError('necessity_candidate_input_ceiling')
        raw = encode(visible(json_value(request)))
        files[f'{case}-facts.json'] = raw
        rows.append(dict(id=case, request_sha256=hashlib.sha256(raw).hexdigest(),
            report_sha256=hashlib.sha256(inputs.source.report.encode('utf-8')).hexdigest(),
            source_pack_sha256=hashlib.sha256(inputs.pack_json.encode('utf-8')).hexdigest(),
            estimated_input_ceiling=size, output_reservation=request.max_tokens))
    files['manifest.json'] = encode(dict(version=VERSION, status='offline_prepared_not_executable',
        cases=rows, provider_requests=0, authorized=False, semantic_improvement_proven=False,
        production_admitted=False, publication_allowed=False))
    return files


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    files = prepare()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        with (args.output_dir / name).open('xb') as stream:
            stream.write(raw)
    print(json.dumps(dict(status='offline_prepared_not_executable', files=len(files), provider_requests=0)))
