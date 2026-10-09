"""Read-only accepted-tail replay; public whitelist and create-only export."""
import argparse
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path

from app.evaluation.golden_stream_bridge import REQUEST
from scripts import run_document_accepted_tails as runner
from scripts import document_accepted_tail_handoff as handoff

base = runner.base


def replay(directory, *, event_source):
    directory = Path(directory)
    saved = json.loads((directory/'plan.json').read_bytes())
    plan = saved['preparation_plan']
    if plan != runner.prepare(root_thread_id=plan['root_thread_id'],
            independent_thread_id=plan['review_principals']['independent']['principal_id']) or saved['plan_sha256'] != base.canonical_sha(plan):
        raise ValueError('accepted_tail_seal_plan_changed')
    base.require_execution_event_source(plan,event_source)
    result = json.loads((directory/'result.json').read_bytes())
    variants = runner.controls()
    keys = [c['key'] for c in result['cases']]
    if keys != list(runner.KEYS[:len(keys)]) or result['unexecuted_keys'] != list(runner.KEYS[len(keys):]):
        raise ValueError('accepted_tail_seal_case_inventory')
    paths = ['plan.json','result.json']
    calls = []
    stages = []
    unverified_host_files = []
    historical_count = 0
    for index,case in enumerate(result['cases']):
        key = case['key']
        arm_name = key.replace(':','-')
        arm = directory/arm_name
        _,source,inputs,initial,historical,edit = variants[index]
        if json.loads((arm/'source.json').read_bytes()) != dict(input_json=inputs.data_json,report=source.report):
            raise ValueError('accepted_tail_seal_source_changed')
        historical_path = arm/'historical-initial-journal.json'
        if historical_path.exists():
            flow = runner.backend.Workflow(lambda request:historical)
            flow.evaluate(source)
            if json.loads(historical_path.read_bytes()) != dict(flow.last_journal,
                    historical_input=True,initial_review_accepted=True,new_provider_call=False):
                raise ValueError('accepted_tail_seal_historical_changed')
            historical_count += 1
        transport = directory/'transport'/arm_name
        actual = runner.backend.read_calls(transport)
        issued = [s for s in runner.STAGES if (arm/s/'issued-request.json').exists()]
        if issued != list(runner.STAGES[:len(issued)]) or len(actual) > len(issued):
            raise ValueError('accepted_tail_seal_call_inventory')
        if len(actual) < len(issued):
            # Only the final unreceipted attempt of a hard-stopped batch may be
            # represented by its real local issued bytes, never a fake receipt.
            if len(issued) != len(actual)+1 or index != len(keys)-1 or not result.get('error_type'):
                raise ValueError('accepted_tail_seal_receiptless_position')
            raw = (arm/issued[-1]/'issued-request.json').read_bytes()
            data = json.loads(raw)
            request = REQUEST.validate_json(raw,strict=True)
            request = replace(request,**{k:data[k] for k in ('temperature','timeout_s','top_p')})
            actual.append(dict(request=request,usage=None,completed=False,receipt_missing=True,
                binding=dict(request_sha256=base.sha(arm/issued[-1]/'issued-request.json'))))
        for name,call in zip(issued,actual,strict=True):
            role = 'revision' if name == 'revision' else 'review'
            if runner.backend.role_for_request(call['request']) != role:
                raise ValueError('accepted_tail_seal_role_changed')
            raw = base.validate_request(call['request'],transport_id=base.CAPACITY_TRANSPORT_ID
                if name == 'revision' else base.REVIEW_MODEL_TRANSPORT_ID)
            if raw != (arm/name/'issued-request.json').read_bytes() or base.sha(arm/name/'issued-request.json') != call['binding']['request_sha256']:
                raise ValueError('accepted_tail_seal_issued_request_changed')
            if name == 'revision':
                expected = edit
            else:
                _,prior,_ = handoff.material(directory,key,'revision',closed=True,variants=variants)
                expected = runner.backend.Workflow.make_request(runner.backend.Workflow.build_inputs(
                    replace(source,report=prior['report'])))
            metadata = dict(call['request'].metadata)
            if (metadata.pop('coach_budget_contract',None) != 'coach-bounded-review-v2'
                    or not 0 < call['request'].timeout_s <= expected.timeout_s
                    or replace(call['request'],timeout_s=expected.timeout_s,metadata=metadata) != expected):
                raise ValueError('accepted_tail_seal_pending_request_changed')
            response_path = arm/name/'response.json'
            if response_path.exists() and (call.get('response') is None or
                    json.loads(response_path.read_bytes()) != base.public_response(json.loads(base.RESPONSE.dump_json(call['response'])))):
                raise ValueError('accepted_tail_seal_pending_response_changed')
        calls.extend(actual)
        if [s['stage'] for s in case['stages']] != list(runner.STAGES[:len(case['stages'])]):
            raise ValueError('accepted_tail_seal_stage_inventory')
        for recorded in case['stages']:
            name = recorded['stage']
            _,value,bound = handoff.material(directory,key,name,closed=True,variants=variants)
            submission = json.loads((arm/name/'host-reviews.json').read_bytes())
            if submission != json.loads((arm/name/'review-submission.json').read_bytes()):
                raise ValueError('accepted_tail_seal_submission_changed')
            accepted = base.validate_reviews(submission,value,bound,plan,event_source)
            if recorded != dict(stage=name,binding=bound,host_accepted=accepted):
                raise ValueError('accepted_tail_seal_opinion_changed')
            stages.append(dict(key=key,**recorded))
            paths += [f'{arm_name}/{name}/{f}' for f in ('issued-request.json','response.json',
                'stage.json','review-required.json','review-submission.json','host-reviews.json')]
        terminal = arm/'case-result.json'
        if terminal.exists():
            if json.loads(terminal.read_bytes()) != case:raise ValueError('accepted_tail_seal_case_result_changed')
            names = [s['stage'] for s in case['stages']]
            flags = [s['host_accepted'] for s in case['stages']]
            expected_failure = None
            if names == ['revision'] and flags == [False]:expected_failure = 'revision_host_rejected'
            elif names == ['revision','final'] and flags[0]:
                final = json.loads((arm/'final/stage.json').read_bytes())['journal']['parsed_review']
                if (case['final_verdict'],case['final_score']) != (final['verdict'],final['score']):
                    raise ValueError('accepted_tail_seal_fresh_changed')
                if not flags[1]:expected_failure = 'fresh_host_rejected'
                elif final['verdict'] != 'pass' or final['score'] < 85:expected_failure = 'fresh_not_pass'
            else:raise ValueError('accepted_tail_seal_case_terminal_changed')
            if case['semantic_accepted'] != (expected_failure is None) or case.get('semantic_failure') != expected_failure:
                raise ValueError('accepted_tail_seal_semantic_outcome_changed')
            if len(actual) != len(names):raise ValueError('accepted_tail_seal_rejected_case_continued')
            paths.append(f'{arm_name}/case-result.json')
        elif index != len(keys)-1 or not result.get('error_type'):
            raise ValueError('accepted_tail_seal_incomplete_case')
        for filename in ('source.json','historical-initial-journal.json'):
            if (arm/filename).exists():paths.append(f'{arm_name}/{filename}')
        for name in issued[len(case['stages']):]:
            # Pending native/identity failures are hashed, but uncertified host
            # contents never enter the public JSON whitelist.
            for filename in ('issued-request.json','response.json','stage.json','review-required.json'):
                if (arm/name/filename).exists():paths.append(f'{arm_name}/{name}/{filename}')
            for filename in ('host-reviews.json','review-submission.json'):
                if (arm/name/filename).exists():unverified_host_files.append(f'{arm_name}/{name}/{filename}')
    known = sum(sum(c['usage'].values()) for c in calls if c['usage'] is not None)
    unknown = sum(c['usage'] is None for c in calls)
    reserved = sum(base.size(c['request'])+c['request'].max_tokens for c in calls if c['usage'] is None)
    complete = len(keys) == len(runner.KEYS) and not result.get('error_type')
    if (result['calls'] != len(calls) or result['known_tokens'] != known
            or result['historical_initial_inputs'] != historical_count
            or result['unknown_reserved_tokens'] != reserved or result['scan_completed'] != complete
            or result['diagnostic_accepted'] != (complete and all(c['semantic_accepted'] for c in result['cases']))
            or any(result[k] is not False for k in ('product_admitted','original15_qualified','review_controls_qualified'))):
        raise ValueError('accepted_tail_seal_accounting_changed')
    cost = Decimal(0)
    for c in calls:
        if c['usage'] is not None:
            _,model = runner.backend.CONTRACT.request_identity(c['request'])
            price = runner.backend.CONTRACT.pricing_profiles['zhipu',model]
            cost += (Decimal(c['usage']['input_tokens'])*price.input_cost_per_million
                + Decimal(c['usage']['output_tokens'])*price.output_cost_per_million)/1_000_000
    public = {p:json.loads((directory/p).read_bytes()) for p in dict.fromkeys(paths)}
    def check(value):
        if isinstance(value,dict):
            if {'api_key','authorization','access_token'} & value.keys() or value.get('reasoning_content') is not None:
                raise ValueError('accepted_tail_seal_private_field')
            for v in value.values():check(v)
        elif isinstance(value,list):
            for v in value:check(v)
    check(public)
    return dict(kind='document-accepted-tails-result-v1',execution_result=result,stages=stages,
        historical_seal_sha256=runner.SEAL_SHA,historical_credit=0,
        accounting=dict(calls=len(calls),known_tokens=known,unknown_usage_calls=unknown,
            local_attempts_without_transport_receipt=sum(c.get('receipt_missing',False) for c in calls),
            known_usage_estimated_uncached_cny=str(cost),unknown_usage_is_not_free=True),
        public_json_contents=public,unverified_host_files=unverified_host_files,
        original_file_sha256={p.relative_to(directory).as_posix():base.sha(p) for p in sorted(directory.rglob('*')) if p.is_file()},
        review_controls_qualified=False,actual_product_task_qualified=False,production_admitted=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=base.ROOT/'data/runs/model_comparison'/runner.EXPERIMENT)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--codex-executable',type=Path,required=True)
    args = parser.parse_args()
    plan = json.loads((args.directory/'plan.json').read_bytes())['preparation_plan']
    with base.CodexReadOnlyClient(args.codex_executable) as client:
        source = base.CodexHostReviewEventSource(client,plan)
        value = replay(args.directory,event_source=source)
        if args.output:base.write_new_json(args.output,value)
        print(base.compact(dict(replayed=True,calls=value['accounting']['calls'],provider_calls=0)))


if __name__ == '__main__':main()
