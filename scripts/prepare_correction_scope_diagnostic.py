"""Offline source-preserving diagnostic preparation; no live entry or admission.

The prospective variant retains every issue field and full report/source. It
tests output responsibility, not an economic special case or deleted evidence.
"""
import argparse
from dataclasses import replace
import hashlib
from pathlib import Path

from app.evaluation.coarse_role_qualification import frozen_cases, size
from app.evaluation.golden_role_coarse import RoleCoarseReviewWorkflow as Workflow
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import validate_request, REVIEW_MODEL_TRANSPORT_ID

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'correction-scope-responsibility-diagnostic-v1'
RULE = ('审查输出也必须遵守上述事实、范围与来源规则。suggested_correction只修复explanation已确认的实际问题'
        '及有来源支持的直接影响；不得另行扩展到未确认有问题的指标、对象、比较组或量词。'
        '修法里的说明和示例都逐项核对，不让正确示例掩盖错误的总指令；不能确认的替换断言不要当作确定修法。')


def variant(inputs):
    base = Workflow.make_request(inputs)
    changed = replace(base, messages=(replace(base.messages[0], content=base.messages[0].content+'\n'+RULE),
                                      *base.messages[1:]))
    if replace(changed, messages=base.messages) != base or changed.messages[1:] != base.messages[1:]:
        raise ValueError('correction_scope_non_policy_change')
    return base, changed


def prepare():
    rows, selected = [], {}
    for frozen, source in frozen_cases()[0]:
        inputs = Workflow.build_inputs(source)
        base, changed = variant(inputs)
        original_raw = validate_request(base, transport_id=REVIEW_MODEL_TRANSPORT_ID)
        variant_raw = validate_request(changed, transport_id=REVIEW_MODEL_TRANSPORT_ID)
        row = dict(key=frozen['key'], input_sha256=frozen['input_sha256'],
            original_request_sha256=hashlib.sha256(original_raw).hexdigest(),
            diagnostic_request_sha256=hashlib.sha256(variant_raw).hexdigest(),
            original_policy_sha256=digest(base.messages[0].content),
            diagnostic_policy_sha256=digest(changed.messages[0].content),
            input_ceiling=size(changed), output_cap=changed.max_tokens,
            source_messages_identical=True, schema_identical=True, other_parameters_identical=True)
        rows.append(row)
        if frozen['key'] in ('attribution:1','claim-scope:1'):
            selected[frozen['key']] = variant_raw
    return dict(kind=VERSION, stage='offline_preparation', change=RULE, cases=rows,
        proposed_case_order=['attribution:1','claim-scope:1'],
        prior_failure_export_sha256='d509d516f40739963ed9ac11679fea757ccd83a902e049cefb5e4110c947b69e',
        original_issue_fields_preserved=True, labels_sent_to_model=False,
        proposed_budget=dict(max_calls=2,max_tokens=193536,max_seconds=600,sdk_retries=0),
        stop_rule='First substantive issue in the full response stops this direction; no synonym variants.',
        limits='Preparation is not execution, causal proof, correction quality, original15 qualification or product admission.',
        provider_requests=0, execution_enabled=False, review_controls_qualified=False,
        actual_product_task_qualified=False, production_admitted=False), selected


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result,_=prepare()
    if args.output:
        write_new_json(args.output,result)
    print(compact(dict(preparation_sha256=digest(compact(result)),cases=len(result['cases']),
        provider_requests=0,execution_enabled=False)))
