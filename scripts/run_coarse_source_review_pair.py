"""Two source-granularity feasibility controls, not a new product candidate.

Uses unchanged correct/error inputs and the existing GLM/high comparison
executor. Historical fine-reference failures remain failures. This prospective
pair tests feasibility, not a causal attribution or a reliability estimate.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import time

from jsonschema import Draft202012Validator

from app.evaluation import golden_coarse_source_projection as coarse
from app.evaluation.coach_grounded_contract import EvaluationResponseModelV12
from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_native_tool_review import tool_result
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_clarity import RoleClarityReviewWorkflow as Workflow, RoleClarityReview
from app.evaluation.golden_semantic_review import security_terminal
from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.evaluation.role_qualification import ROOT, ASSETS, frozen_cases, candidate_identity, size
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from scripts.diagnose_block_review_route import route_environment
from scripts.diagnose_role_context import canonical_sha
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout
from scripts.run_role_task_observation import await_case_ready
from scripts.run_role_unexecuted_qualification import CLOSED_RESULT as BASELINE, CLOSED_SHA as BASELINE_SHA
from scripts.run_review_model_comparison import observe

EXPERIMENT = 'coarse-source-review-pair-v1'
KEYS = ('observed:2', 'observed:1')
RUN_DIRECTORY = ROOT/'data/runs/model_comparison'/EXPERIMENT
PREPARATION = ROOT/'data/evaluation/results/golden_coarse_source_preparation_v1.json'
CLOSED_RESULT = ROOT/'data/evaluation/results/golden_coarse_source_result_v1.json'


def prepare():
    RuntimeCompositionRoot.from_directories(skills_root=ROOT/ASSETS/'skills',
        prompt_programs_root=ROOT/ASSETS/'prompt_programs', coach_contract=ROLE_COACH_CONTRACT)
    if hashlib.sha256(BASELINE.read_bytes()).hexdigest() != BASELINE_SHA:
        raise ValueError('coarse_pair_baseline_changed')
    baseline = json.loads(BASELINE.read_text(encoding='utf-8'))
    sources = {row['key']:(row,source) for row,source in frozen_cases()[0]}
    variants, cells = [], []
    for key in KEYS:
        row,source = sources[key]
        inputs = Workflow.build_inputs(source)
        original = Workflow.make_request(inputs)
        original_raw = validate_request(original, transport_id=REVIEW_MODEL_TRANSPORT_ID)
        name = key.replace(':','-')
        if hashlib.sha256(original_raw).hexdigest() != baseline['original_file_sha256'][name+'-prepared-request.json']:
            raise ValueError('coarse_pair_baseline_request_changed')
        request = coarse.project_request(inputs)
        if coarse.restore_request(request, inputs) != original:
            raise ValueError('coarse_pair_source_loss')
        raw = validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)
        variants.append((name,inputs,request))
        cells.append(dict(id=name,key=key,input_sha256=digest(inputs.data_json),
            report_sha256=digest(source.report),expected_initial=row['expected_initial'],
            request_sha256=hashlib.sha256(raw).hexdigest(),input_reservation=size(request),output_cap=32768,
            baseline_request_sha256=hashlib.sha256(original_raw).hexdigest()))
    tokens = sum(c['input_reservation']+c['output_cap'] for c in cells)
    cost = (Decimal(tokens-65536)*8+Decimal(65536)*28)/1_000_000
    paths = ('scripts/run_coarse_source_review_pair.py','scripts/run_review_model_comparison.py',
        'scripts/run_role_task_observation.py','app/evaluation/golden_coarse_source_projection.py')
    plan = dict(experiment=EXPERIMENT,baseline_sha256=BASELINE_SHA,baseline_candidate=candidate_identity(),
        source_sha256={p:digest((ROOT/p).read_text(encoding='utf-8')) for p in paths},cells=cells,
        proposed_diagnostic_budget=dict(max_calls=2,max_seconds_total=600,max_seconds_per_call=300,
            total_token_reservation=tokens,estimated_uncached_cny=str(cost),hard_billing_cap=False),
        model='glm-5.3',reasoning_effort='high',sdk_retries=0,labels_sent_to_model=False,
        intervention='Only source-address navigation, allowed-reference schema and address instructions; all report/source values preserved.',
        stop_rule='Stop on any rejected whole-output/source review, wrong verdict, protocol/identity/transport/budget failure; no recovery, editing or retry.',
        decision='Both full-source controls accepted only supports a broader qualification decision; any failure rejects this as a sufficient fix. No causal or reliability claim from historical comparison.',
        review_controls_qualified=False,actual_product_task_qualified=False,production_admitted=False)
    if CLOSED_RESULT.exists():
        raw = CLOSED_RESULT.read_bytes()
        if hashlib.sha256(raw).hexdigest() != 'f7c8a787816e98ca797fdd0337ec1e6ddb94999206687220df7631b62331a4a8':
            raise ValueError('coarse_pair_closed_evidence_changed')
        frozen = json.loads(raw)['public_json_contents']['plan.json']
        plan['source_sha256'] = frozen['preparation_plan']['source_sha256']
        if plan != frozen['preparation_plan'] or canonical_sha(plan) != frozen['plan_sha256']:
            raise ValueError('coarse_pair_closed_request_changed')
    return plan,variants


def inspect_response(prepared,exchange,inputs):
    """Check this diagnostic's own wire contract; never alter a model's IDs."""
    coarse.restore_request(prepared,inputs)
    raw = tool_result(prepared,exchange)
    value = json.loads(raw)
    if security_terminal(value):
        raise ValueError('native_security_terminal')
    Draft202012Validator(prepared.tools[0].input_schema).validate(value)
    wire = RoleClarityReview.model_validate(value,strict=True)
    if wire.issue_resolutions:
        raise ValueError('coarse_pair_unexpected_prior_review')
    selected, issues = [], []
    for number,issue in enumerate(wire.issues,1):
        if issue.block > len(inputs.source.blocks) or issue.category=='prompt_injection':
            raise ValueError('coarse_pair_invalid_block_or_security')
        refs = coarse.resolve_refs(inputs,issue.source_ids)
        selected.append(dict(block=issue.block,issue=number,selected_sources=refs))
        issues.append(dict(issue.model_dump(exclude={'source_ids','block'}),
            quote=inputs.source.blocks[issue.block-1][1],evidence=issue.explanation))
    markers=[m.block for m in wire.advisories]
    if len(set(markers))!=len(markers) or any(n>len(inputs.source.blocks) for n in markers):
        raise ValueError('coarse_pair_invalid_marker')
    EvaluationResponseModelV12.model_validate(dict(score=wire.score,verdict=wire.verdict,
        summary='Diagnostic model review; semantic acceptance requires independent full-source inspection.',
        passed_checks=[],issues=issues),strict=True)
    if wire.verdict=='pass':
        available={r['citation_id'] for r in json.loads(inputs.data_json)['knowledge']['citations']}
        cited=set(re.findall(r'\[(K\d+)\]',inputs.source.report))
        if cited-available or available and not cited:
            raise ValueError('coarse_pair_unreported_knowledge_citation')
        if wire.score<ROLE_COACH_CONTRACT.descriptor()['minimum_score']:
            raise ValueError('coarse_pair_pass_below_threshold')
    journal=dict(raw=raw,raw_sha256=digest(raw),parsed_review=value,selected_sources=selected,
        policy_sha256=digest(prepared.messages[0].content),input_sha256=digest(inputs.data_json),
        report_sha256=digest(inputs.source.report),semantic_approval=False,production_admitted=False)
    return dict(score=wire.score,verdict=wire.verdict,issue_blocks=[i.block for i in wire.issues],advisory_blocks=markers),journal


def adjudicate_file(path,remaining,plan,*,clock=time.monotonic,sleep=time.sleep):
    deadline=clock()+remaining
    cell=next(c for c in plan['cells'] if c['id']==path.parent.name)
    response_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    decision_path=path.with_name('host-decision.json')
    write_new_json(path.with_name('host-required.json'),dict(response_sha256=response_sha,
        input_sha256=cell['input_sha256'],report_sha256=cell['report_sha256'],remaining_seconds=remaining))
    while True:
        available=deadline-clock()
        if available<=0:
            raise ValueError('coarse_pair_host_deadline')
        try:
            decision=json.loads(decision_path.read_text(encoding='utf-8'))
        except (FileNotFoundError,UnicodeDecodeError,json.JSONDecodeError):
            sleep(min(.25,available));continue
        independent=path.with_name('independent-review.json')
        other=json.loads(independent.read_text(encoding='utf-8'))
        if (type(decision.get('accepted')) is not bool or clock()>=deadline
                or decision.get('response_sha256')!=response_sha
                or decision.get('independent_sha256')!=hashlib.sha256(independent.read_bytes()).hexdigest()
                or any(r.get(k)!=v for r in (decision,other) for k,v in dict(response_sha256=response_sha,
                    input_sha256=cell['input_sha256'],report_sha256=cell['report_sha256'],accepted=decision['accepted']).items())
                or any(not isinstance(r.get('source_review'),str) or not r['source_review'].strip() for r in (decision,other))):
            raise ValueError('coarse_pair_host_binding_invalid')
        if decision['accepted'] and any(r.get('defects')!=[] for r in (decision,other)):
            raise ValueError('coarse_pair_host_rejected_defects')
        journal=json.loads(path.with_name('journal.json').read_text(encoding='utf-8'))
        expected='pass' if cell['expected_initial']=='accept' else 'needs_revision'
        if decision['accepted'] and journal['parsed_review']['verdict']!=expected:
            raise ValueError('coarse_pair_wrong_verdict')
        return decision


def run(args):
    if args.execute and (RUN_DIRECTORY.exists() or CLOSED_RESULT.exists()):
        raise ValueError('coarse_pair_closed_or_exists')
    plan,variants=prepare()
    sha=canonical_sha(plan)
    if not args.execute:
        if args.output: write_new_json(args.output,plan)
        return dict(plan_sha256=sha,budget=plan['proposed_diagnostic_budget'],provider_requests=0,execution_enabled=False)
    if (not args.env_file or not args.ci_run or args.plan_sha!=sha
            or plan!=json.loads(PREPARATION.read_text(encoding='utf-8'))):
        raise ValueError('coarse_pair_preparation_required')
    head=verify_public_ci(args.ci_run)
    RUN_DIRECTORY.mkdir(parents=True,exist_ok=False)
    write_new_json(RUN_DIRECTORY/'plan.json',dict(preparation_plan=plan,plan_sha256=sha,head_sha=head,ci_run=args.ci_run))
    for name,inputs,request in variants:
        write_new_json(RUN_DIRECTORY/(name+'-source.json'),dict(input_json=inputs.data_json,report=inputs.source.report))
    settings=load_role_settings(args.env_file)[1]
    provider=ReceiptedStreamProvider(settings=settings,directory=RUN_DIRECTORY/'transport',transport_id=REVIEW_MODEL_TRANSPORT_ID)
    with route_environment('direct'):
        return observe(provider,RUN_DIRECTORY,variants,plan,inspect_response=inspect_response,
            adjudicate=lambda p,t:adjudicate_file(p,t,plan),before_case=await_case_ready,
            before_send=lambda:require_unchanged_checkout(head))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file',type=Path)
    args=parser.parse_args()
    result=run(args)
    print(compact(result),flush=True)
    if args.execute and not result['pair_accepted']: raise SystemExit(1)
