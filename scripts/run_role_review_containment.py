"""Two-call editor/fresh-review tail with an unchanged rejected review fixture.

This measures containment, not reviewer qualification. The failed first review
is injected offline and remains failed. Only the edit and final review are new
Provider calls; no production report is published and no old batch is resumed.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import time

from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_clarity import RoleClarityReviewWorkflow as Workflow
from app.evaluation.golden_stream_bridge import RESPONSE, REVIEW_MODEL_TRANSPORT_ID, CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.evaluation.role_qualification import ROOT, ASSETS, candidate_identity, frozen_cases, read_role_calls
from app.harness.steps import EvaluationVerdict, RevisionRequest
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from app.runtime.review_sender import SharedBudgetReviewSender
from app.runtime.runtime import _ReceiptForwardingCoachBudgetedProvider
from scripts.diagnose_block_review_route import route_environment
from scripts.diagnose_role_context import canonical_sha
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_review_model_comparison import terminal_adjudication
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout, summarize_calls

EXPERIMENT = 'role-review-containment-v1'
EVIDENCE = ROOT/'data/evaluation/results/golden_role_clarity_result_v1.json'
EVIDENCE_SHA = '2884776f4f866e67738d43bdb9f4966ec37400486ccb1e6706a0f59aee8dcdd9'
PREPARATION = ROOT/'data/evaluation/results/golden_role_containment_preparation_v1.json'
CLOSED_RESULT = ROOT/'data/evaluation/results/golden_role_containment_result_v1.json'
RUN_DIRECTORY = ROOT/'data/runs/role_containment'/EXPERIMENT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture():
    if sha(EVIDENCE) != EVIDENCE_SHA:
        raise ValueError('containment_fixture_changed')
    evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
    public = evidence['public_json_contents']
    frozen, source = next((f,s) for f,s in frozen_cases()[0] if f['key']=='claim-scope:4')
    stage = public['claim-scope-4/initial.json']
    if stage['report'] != source.report or stage['report_sha256'] != frozen['report_sha256']:
        raise ValueError('containment_fixture_source_changed')
    response = RESPONSE.validate_json(compact(public['transport/claim-scope-4/review/response-001.json']),strict=True)
    if dict(response.tool_calls[0].arguments) != stage['journal']['parsed_review']:
        raise ValueError('containment_fixture_review_changed')
    inputs = Workflow.build_inputs(source)
    payload, wire, _ = Workflow.validate_review(stage['journal']['raw'],inputs)
    if payload.verdict != 'needs_revision' or not wire.issues:
        raise ValueError('containment_fixture_verdict_changed')
    initial = Workflow.make_request(inputs)
    initial_raw = validate_request(initial,transport_id=REVIEW_MODEL_TRANSPORT_ID)
    if hashlib.sha256(initial_raw).hexdigest() != evidence['original_file_sha256']['claim-scope-4-prepared-request.json']:
        raise ValueError('containment_initial_request_changed')
    editor = Workflow.make_request(inputs,accepted=wire)
    return frozen, source, response, initial, editor


def prepare():
    if CLOSED_RESULT.exists():
        if sha(CLOSED_RESULT) != 'cb2991fc122b38ba9ef7cca3940b0e983dee41f1698741f2766eb0c22c17e2cb':
            raise ValueError('containment_historical_evidence_changed')
        saved = json.loads(CLOSED_RESULT.read_text(encoding='utf-8'))['public_json_contents']['plan.json']
        plan = saved['preparation_plan']
        if (plan != json.loads(PREPARATION.read_text(encoding='utf-8'))
                or canonical_sha(plan) != saved['plan_sha256']):
            raise ValueError('containment_historical_plan_changed')
        frozen, source, response, initial, editor = fixture()
        if (frozen['report_sha256'] != plan['original_report_sha256']
                or digest(RESPONSE.dump_json(response).decode()) != plan['injected_public_response_sha256']
                or hashlib.sha256(validate_request(editor,transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()
                    != plan['editor_request_sha256']):
            raise ValueError('containment_historical_request_changed')
        return plan, (source,response,initial,editor)
    RuntimeCompositionRoot.from_directories(skills_root=ROOT/ASSETS/'skills',
        prompt_programs_root=ROOT/ASSETS/'prompt_programs',coach_contract=ROLE_COACH_CONTRACT)
    frozen, source, response, initial, editor = fixture()
    identity = candidate_identity()
    origin = json.loads(EVIDENCE.read_text(encoding='utf-8'))['public_json_contents']['plan.json']['preparation_plan']['identity']
    if identity != origin:
        raise ValueError('containment_candidate_changed')
    plan = dict(experiment=EXPERIMENT,identity=identity,fixture_evidence_sha256=EVIDENCE_SHA,
        original_report_sha256=frozen['report_sha256'],original_input_sha256=frozen['input_sha256'],
        injected_public_response_sha256=digest(RESPONSE.dump_json(response).decode()),
        initial_prepared_request_sha256=hashlib.sha256(validate_request(initial,transport_id=REVIEW_MODEL_TRANSPORT_ID)).hexdigest(),
        editor_request_sha256=hashlib.sha256(validate_request(editor,transport_id=CAPACITY_TRANSPORT_ID)).hexdigest(),
        editor_input_ceiling=size(editor),script_sha256=digest(Path(__file__).read_text(encoding='utf-8')),
        budget=dict(max_calls=2,max_tokens=193536,max_seconds=600,max_output_per_call=32768,
            max_seconds_per_call=300,sdk_retries=0,estimated_uncached_cny='2.859008',
            estimate_scope='Conservative all-GLM reservation; actual Flash edit costs less. Not invoice or billing cap.'),
        offline_initial_injections=1,initial_review_accepted=False,labels_sent_to_model=False,
        diagnostic_only=True,review_controls_qualified=False,actual_product_task_qualified=False,production_admitted=False,
        stop_rule='Stop before final if actual edit is rejected; no reassessment/retry. Reject wrong final judgment or any unsupported final opinion. Preserve rejected first review unchanged.',
        success_scope='One observed edit/fresh-review tail contains this frozen initial review error; not original-15 reviewer qualification or full generated task.',
        failure_decision='Do not use this tail as a generic repair. Locate first leak/incorrect edit/final review; do not automatically add prompts or retries.')
    return plan, (source,response,initial,editor)


def observe(factory,directory,plan,prepared,*,adjudicate=terminal_adjudication,
            clock=time.monotonic,before_send=lambda:None):
    source, response, initial_request, editor_request = prepared
    started = clock()
    provider = factory('tail')
    wrapped = _ReceiptForwardingCoachBudgetedProvider(provider,clock=clock,coach_contract=ROLE_COACH_CONTRACT)
    sender = SharedBudgetReviewSender(wrapped)
    injected = False
    result = dict(experiment=EXPERIMENT,tail_accepted=False,initial_review_accepted=False,
        offline_initial_injections=0,review_controls_qualified=False,actual_product_task_qualified=False,production_admitted=False)

    def remaining():
        return plan['budget']['max_seconds']-(clock()-started)

    def send(request):
        nonlocal injected
        if not injected:
            if request != initial_request:
                raise ValueError('containment_initial_injection_mismatch')
            injected = True
            result['offline_initial_injections'] = 1
            return Exchange(request,response,plan['initial_prepared_request_sha256'])
        if request.metadata.get('review_phase') == 'native_business_reassessment':
            raise ValueError('containment_reassessment_forbidden')
        if wrapped.calls >= 2 or remaining() <= 0:
            raise ValueError('containment_tail_budget')
        if wrapped.calls == 0 and request != editor_request:
            raise ValueError('containment_editor_changed')
        before_send()
        available = remaining()
        if available <= 0:
            raise ValueError('containment_tail_budget')
        return sender(replace(request,timeout_s=min(request.timeout_s,available)))

    def inspect(stage,report,journal=None):
        path = directory/(stage+'.json')
        write_new_json(path,dict(stage=stage,report=report,report_sha256=digest(report),journal=journal))
        if remaining() <= 0:
            raise ValueError('containment_tail_budget')
        decision = adjudicate(path,remaining())
        if type(decision.get('accepted')) is not bool or decision.get('response_sha256') != sha(path):
            raise ValueError('containment_host_binding_invalid')
        write_new_json(directory/(stage+'-host.json'),decision)
        if not decision['accepted']:
            raise ValueError('containment_host_rejected')
        if remaining() <= 0:
            raise ValueError('containment_tail_budget')

    workflow = Workflow(send)
    try:
        initial = workflow.evaluate(source)
        write_new_json(directory/'injected-initial-journal.json',dict(workflow.last_journal,
            fixture_only=True,initial_review_accepted=False,new_provider_call=False))
        if initial.verdict is not EvaluationVerdict.NEEDS_REVISION:
            raise ValueError('containment_initial_verdict_changed')
        draft = workflow.revise(RevisionRequest(source.player_summary,source.deterministic_report,
            source.knowledge,source.report,initial))
        inspect('revision',draft.report)
        final = workflow.evaluate(replace(source,report=draft.report))
        write_new_json(directory/'final-journal.json',workflow.last_journal)
        result.update(final_verdict=final.verdict.value,final_score=final.score,final_report_sha256=digest(draft.report))
        if final.verdict is not EvaluationVerdict.PASS or final.score < ROLE_COACH_CONTRACT.descriptor()['minimum_score']:
            raise ValueError('containment_final_semantics_failed')
        inspect('final',draft.report,workflow.last_journal)
        calls = read_role_calls(directory/'transport/tail')
        if (len(calls)!=2 or not all(c['completed'] for c in calls)
                or [c['binding']['role'] for c in calls] != ['revision','review']):
            raise ValueError('containment_receipts_incomplete')
        if sum(c['usage']['input_tokens']+c['usage']['output_tokens'] for c in calls)>plan['budget']['max_tokens']:
            raise ValueError('containment_tail_budget')
        result['tail_accepted'] = True
    except BaseException as error:
        result['error_type'] = type(error).__name__
        code = getattr(error,'code',None) or (str(error) if isinstance(error,ValueError) else None)
        if isinstance(code,str) and re.fullmatch('[a-z_]{1,100}',code):
            result['error_code'] = code
    finally:
        try:
            accounting = summarize_calls(directory/'transport/tail')
        except (ValueError,OSError,KeyError,TypeError):
            accounting = dict(accounting_status='invalid_receipts',reserved_calls=None,
                completed_calls=None,unknown_usage_calls=None,total_estimated_uncached_cny=None)
            result['tail_accepted'] = False
        result.update(elapsed_seconds=round(clock()-started,3),accounting=accounting)
        write_new_json(directory/'result.json',result)
    return result


def run(args):
    if args.execute and CLOSED_RESULT.exists():
        raise ValueError('containment_batch_closed')
    plan, prepared = prepare()
    plan_sha = canonical_sha(plan)
    if not args.execute:
        if args.output:
            write_new_json(args.output,plan)
        return dict(plan_sha256=plan_sha,budget=plan['budget'],provider_requests=0,
            historical_closed=CLOSED_RESULT.exists(),execution_enabled=False)
    if (not args.env_file or not args.ci_run or args.plan_sha != plan_sha
            or plan != json.loads(PREPARATION.read_text(encoding='utf-8'))):
        raise ValueError('containment_preparation_required')
    if RUN_DIRECTORY.exists():
        raise ValueError('containment_batch_exists')
    head = verify_public_ci(args.ci_run)
    RUN_DIRECTORY.mkdir(parents=True,exist_ok=False)
    write_new_json(RUN_DIRECTORY/'plan.json',dict(preparation_plan=plan,plan_sha256=plan_sha,head_sha=head,ci_run=args.ci_run))
    write_new_json(RUN_DIRECTORY/'source.json',dict(report=prepared[0].report,
        input_json=Workflow.build_inputs(prepared[0]).data_json))
    (RUN_DIRECTORY/'prepared-editor-request.json').write_bytes(validate_request(prepared[3],transport_id=CAPACITY_TRANSPORT_ID))
    generation,reviewer = load_role_settings(args.env_file)
    factory = RunScopedRoleReceiptedProviderFactory(generator_settings=generation,reviewer_settings=reviewer,
        transport_root=RUN_DIRECTORY/'transport')
    with route_environment('direct'):
        return observe(factory,RUN_DIRECTORY,plan,prepared,before_send=lambda:require_unchanged_checkout(head))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file',type=Path)
    print(compact(run(parser.parse_args())),flush=True)
