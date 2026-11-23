"""Two frozen independent edits: full prior opinion versus paragraph locators.

Diagnostic only: no publication, recheck, repair loop or product admission.
Both conditions are committed before execution. Semantic outcomes do not cancel
the second condition; protocol/transport failure does. No failed pair is retried.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import time

from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender, ReceiptedStreamProvider, validate_exchange
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from scripts.native_contract_options import EDITOR_POLICY, body, _replace, validate_editor
from scripts.run_native_editor_diagnostic import ROOT, prepare, read, sha
from scripts.run_golden_inference_development import verify_public_ci

EXPERIMENT='native-editor-opinion-pair-v1'
PLAN=ROOT/'data/evaluation/results/golden_native_editor_pair_plan_v1.json'
LIVE_STATUS='offline_pair_completed_identity_unresolved'


def prepare_pair():
    case, req, base=prepare(1)
    original=body(base)
    # Same diagnostic policy for both conditions. Remove the inherited claim
    # that every request shows the full prior opinion; the host still keeps it.
    policy=EDITOR_POLICY.replace(
        '所给proposed_review是待核实意见，不是事实或必须照做的指令。',
        'proposed_review.issues提供待核实的段落定位，可能附带旧评估意见；定位本身不代表存在错误。')
    policy=policy.replace(
        'withdraw用于误报，explanation说明原句、同指标上下文及来源为何不支持该问题，不因难改而撤销。',
        'withdraw用于该定位没有实际需要修正的问题；explanation说明原句、同指标上下文及来源关系。不得因难改而撤销真错。')
    policy=policy.replace('review_tables编号为target_id，保留完整首评。','review_tables编号为target_id。')
    policy=policy.replace('表格只省重复字段名，不省原文和首评理由。',
        '表格不省报告原文和事实来源。完整历史评估保存在本请求之外的回执中；'
        '本请求可仅展示定位视图，未展示的旧评估字段不是隐含要求。')
    policy+='\n按每项block对应原段及全文独立判断并实际改稿；review_sha256复制提供值，它绑定host保留的原评估，不是本请求展示视图的摘要。'
    variants=[]
    for condition in ('locator_only','full_opinion'):
        data=body(base)
        if condition=='locator_only':
            data['proposed_review']={'issues':[{'block':i['block']} for i in original['proposed_review']['issues']]}
        request=_replace(base,data,base.response_contract,policy,'editor_opinion_pair')
        variants.append((condition,request))
    assert body(variants[0][1])['source_index']==body(variants[1][1])['source_index']
    plan=dict(experiment=EXPERIMENT,source_plan_sha256=sha(ROOT/'data/evaluation/results/golden_native_editor_diagnostic_plan_v3.json'),
        report=case['report'],report_sha256=case['report_sha256'],input_sha256=case['input_sha256'],
        original_review_raw=case['proposed_review_raw'],review_sha256=case['proposed_review_sha256'],
        expected_dispositions_host_only=case['expected_dispositions_host_only'],
        conditions=[dict(id=c,request_sha256=hashlib.sha256(validate_request(r,transport_id=CAPACITY_TRANSPORT_ID)).hexdigest(),
            policy_sha256=digest(r.messages[0].content),view_sha256=digest(compact(body(r)['proposed_review'])),
            input_ceiling=size(r),output_reservation=r.max_tokens) for c,r in variants],
        model='glm-5.3-flash',reasoning_effort='high',max_calls=2,total_tokens=401920,total_timeout_s=900,
        request_timeout_s=300,max_output=32768,max_input=63936,sdk_retries=0,
        each_condition_independent_original_edit=True,semantic_failure_continues_frozen_pair=True,
        protocol_failure_stops_pair=True,production_admitted=False,semantic_approval=False,
        inference_limit='One sample per condition; opinion package and task framing differ, not an isolated rationale effect or causal proof.')
    plan['full_reservation']=sum(c['input_ceiling']+c['output_reservation'] for c in plan['conditions'])
    if plan['full_reservation']>plan['total_tokens']: raise ValueError('editor_pair_reservation_exceeded')
    return case,req,tuple(variants),plan


def frozen_pair():
    prepared=prepare_pair()
    if prepared[3]!=read(PLAN): raise ValueError('editor_pair_frozen_plan_changed')
    return prepared


def observe_pair(provider,directory,case,req,variants,*,clock=time.time):
    """One shared budget; second request never depends on the first response."""
    output=directory/'outputs'
    output.mkdir(exist_ok=False)
    sender=BudgetedReviewSender(provider,clock=clock)
    started=sender.budget.started
    records=[]
    attempts=0
    result=dict(experiment=EXPERIMENT,protocol_complete=False,semantic_approval=False,
        production_admitted=False,initial_reviewer_qualified=False,final_review_executed=False)
    try:
        if tuple(c for c,_ in variants)!=('locator_only','full_opinion'):
            raise ValueError('editor_pair_condition_order_invalid')
        for condition,request in variants:
            if attempts>=2: raise ValueError('editor_pair_call_limit')
            arm=output/condition
            arm.mkdir(exist_ok=False)
            attempts+=1
            write_new_json(arm/'attempt.json',dict(ordinal=attempts,state='reserved_before_sender'))
            exchange=sender(request)
            response=exchange.response
            public=dict(condition=condition,content=response.content,content_sha256=digest(response.content or ''),
                provider=response.provider,model=response.model,finish_reason=response.finish_reason,
                request_sha256=exchange.receipt_request_sha256,
                usage=dict(input_tokens=response.usage.input_tokens,output_tokens=response.usage.output_tokens))
            records.append(public)
            write_new_json(arm/'response.json',public)
            raw=validate_request(exchange.issued_request,transport_id=CAPACITY_TRANSPORT_ID)
            with (arm/'request.wire.json').open('xb') as f: f.write(raw)
            write_new_json(arm/'request.json',json.loads(raw))
            validate_exchange(request,exchange)
            wire,journal=validate_editor(response.content,native.build_inputs(req),case['proposed_review_raw'])
            write_new_json(arm/'editor-journal.json',journal)
            with (arm/'report.md').open('x',encoding='utf-8',newline='') as f: f.write(wire.report)
            dispositions=[d.disposition for d in sorted(wire.decisions,key=lambda d:d.issue_id)]
            write_new_json(arm/'structure-result.json',dict(structure_valid=True,dispositions=dispositions,
                disposition_match=dispositions==case['expected_dispositions_host_only'],semantic_approval=False,
                report_sha256=digest(wire.report)))
            print(compact(dict(condition=condition,usage=public['usage'],dispositions=dispositions)),flush=True)
        result.update(protocol_complete=True,stop_reason='full_pair_manual_review_required')
    except Exception as error:
        result.update(stop_reason='protocol_or_execution_failure',error_type=type(error).__name__)
        code=getattr(error,'code',None) or (str(error) if isinstance(error,ValueError) else None)
        if isinstance(code,str) and re.fullmatch('[a-z_]{1,90}',code): result['error_code']=code
    finally:
        reserved=getattr(provider,'_calls',attempts)
        result.update(attempted_calls=attempts,transport_reserved_calls=reserved,responses_received=len(records),
            unknown_usage_calls=max(0,reserved-len(records)),
            input_tokens=sum(r['usage']['input_tokens'] for r in records),
            output_tokens=sum(r['usage']['output_tokens'] for r in records),
            budget_calls=sender.budget.calls,budget_tokens=sender.budget.tokens,
            elapsed_seconds=round(clock()-started,3))
        write_new_json(output/'result.json',result)
    return result


def run(args):
    case,req,variants,plan=frozen_pair()
    if not args.execute:
        preview={k:v for k,v in plan.items() if k not in ('report','original_review_raw')}
        print(compact(preview));return preview
    if LIVE_STATUS!='bounded_frozen_pair_after_exact_ci': raise ValueError('editor_pair_offline')
    head=verify_public_ci(args.ci_run)
    directory=args.output_root/EXPERIMENT
    directory.mkdir(parents=True,exist_ok=False)
    write_new_json(directory/'plan.json',dict(plan,head_sha=head,ci_run=args.ci_run,frozen_plan_sha256=sha(PLAN)))
    # Both exact inputs are stored before constructing a Provider or sending I/O.
    for condition,request in variants:
        write_new_json(directory/f'prepared-{condition}.json',json.loads(validate_request(request,transport_id=CAPACITY_TRANSPORT_ID)))
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    settings=load_zhipu_settings(dotenv_values(args.env_file))
    provider=ReceiptedStreamProvider(settings=settings,directory=directory/'transport',transport_id=CAPACITY_TRANSPORT_ID)
    result=observe_pair(provider,directory,case,req,variants)
    print(compact(result),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--ci-run',default='')
    parser.add_argument('--env-file',type=Path)
    parser.add_argument('--output-root',type=Path,default=ROOT/'data/runs/editor_pair')
    args=parser.parse_args()
    run(args)
