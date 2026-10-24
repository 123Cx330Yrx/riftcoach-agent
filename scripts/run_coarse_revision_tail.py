"""Bounded actual edit/fresh-review follow-through, with a frozen initial receipt."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from app.evaluation.golden_role_coarse import RoleCoarseReviewWorkflow as Workflow, CONTRACT_ID
from app.evaluation.golden_stream_bridge import RESPONSE, validate_request, CAPACITY_TRANSPORT_ID, REVIEW_MODEL_TRANSPORT_ID
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_journal import write_new_json
from app.evaluation.role_qualification import ROOT, frozen_cases, size
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from app.runtime.coach_contract import COARSE_ROLE_COACH_CONTRACT
from app.evaluation.golden_coarse_source_projection import VERSION as PROJECTION
from app.evaluation.coarse_role_qualification import prepare_qualification
from scripts.diagnose_role_context import canonical_sha
from scripts.run_role_review_containment import observe
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout
from scripts.run_golden_inference_development import verify_public_ci
from scripts.diagnose_block_review_route import route_environment

EXPERIMENT = 'coarse-revision-tail-v1'
EVIDENCE = ROOT/'data/evaluation/results/golden_coarse_source_result_v1.json'
EVIDENCE_SHA = 'f7c8a787816e98ca797fdd0337ec1e6ddb94999206687220df7631b62331a4a8'
RUN_DIRECTORY = ROOT/'data/runs/role_containment'/EXPERIMENT
PREPARATION = ROOT/'data/evaluation/results/golden_coarse_tail_preparation_v1.json'
CLOSED_RESULT = ROOT/'data/evaluation/results/golden_coarse_tail_result_v1.json'
CLOSED_SHA = '78258d19166cd6f8124db496fdebefd81f8f8b32f054960c5f8ec85335c5deaa'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    if sha(EVIDENCE) != EVIDENCE_SHA:
        raise ValueError('coarse_tail_evidence_changed')
    evidence = json.loads(EVIDENCE.read_bytes())
    public = evidence['public_json_contents']
    source = next(s for f,s in frozen_cases()[0] if f['key']=='observed:2')
    inputs = Workflow.build_inputs(source)
    response = RESPONSE.validate_json(compact(public['observed-2/response.json']), strict=True)
    journal = public['observed-2/journal.json']
    initial = Workflow.make_request(inputs)
    initial_sha = hashlib.sha256(validate_request(initial,transport_id=REVIEW_MODEL_TRANSPORT_ID)).hexdigest()
    if (digest(inputs.data_json) != journal['input_sha256'] or digest(source.report) != journal['report_sha256']
            or initial_sha != evidence['original_file_sha256']['observed-2/request.raw.json']
            or response.tool_calls[0].arguments != journal['parsed_review']):
        raise ValueError('coarse_tail_fixture_identity')
    for name in ('host-decision.json','independent-review.json'):
        host = public['observed-2/'+name]
        if (host['accepted'] is not True or host['defects'] != []
                or host['response_sha256'] != evidence['original_file_sha256']['observed-2/response.json']
                or host['input_sha256'] != digest(inputs.data_json)
                or host['report_sha256'] != digest(source.report)):
            raise ValueError('coarse_tail_fixture_not_accepted')
    payload, wire, _ = Workflow.validate_review(journal['raw'],inputs)
    if payload.verdict != 'needs_revision':
        raise ValueError('coarse_tail_fixture_verdict')
    editor = Workflow.make_request(inputs,accepted=wire)
    paths = ('scripts/run_coarse_revision_tail.py','scripts/run_role_review_containment.py',
        'app/evaluation/golden_role_coarse.py','app/evaluation/golden_coarse_source_projection.py')
    identity = prepare_qualification()[0]["identity"]
    plan = dict(experiment=EXPERIMENT,identity=identity,workflow_id=CONTRACT_ID,fixture_evidence_sha256=EVIDENCE_SHA,
        original_report_sha256=digest(source.report),original_input_sha256=digest(inputs.data_json),
        initial_prepared_request_sha256=initial_sha,
        injected_public_response_sha256=digest(RESPONSE.dump_json(response).decode()),
        editor_request_sha256=hashlib.sha256(validate_request(editor,transport_id=CAPACITY_TRANSPORT_ID)).hexdigest(),
        editor_input_ceiling=size(editor),source_sha256={p:digest((ROOT/p).read_text(encoding='utf-8')) for p in paths},
        budget=dict(max_calls=2,max_tokens=193536,max_seconds=600,max_output_per_call=32768,
            max_seconds_per_call=300,sdk_retries=0,estimated_uncached_cny='2.859008',
            estimate_scope='Conservative all-GLM reservation, not invoice; Flash edit costs less.'),
        offline_initial_injections=1,initial_review_accepted=True,diagnostic_only=True,
        review_controls_qualified=False,actual_product_task_qualified=False,production_admitted=False,
        stop_rule='Reject any incorrect edit, source/identity/transport/budget error or rejected final review. No recovery or retry.',
        success_scope='Actual edit and fresh final review of one frozen error, not a continuous original task or original15 qualification.')
    if size(editor)+32768 > 96768:
        raise ValueError('coarse_tail_editor_capacity')
    if CLOSED_RESULT.exists():
        if sha(CLOSED_RESULT) != CLOSED_SHA:
            raise ValueError('coarse_tail_closed_evidence_changed')
        closed = json.loads(CLOSED_RESULT.read_bytes())
        saved = closed['public_json_contents']['plan.json']
        frozen = saved['preparation_plan']
        # Preserve execution-time implementation identity while reconstructing
        # the original input, accepted review, editor and budget exactly.
        plan.update(identity=frozen['identity'], source_sha256=frozen['source_sha256'])
        if (plan != frozen or canonical_sha(plan) != saved['plan_sha256']
                or plan != json.loads(PREPARATION.read_bytes())):
            raise ValueError('coarse_tail_closed_preparation_changed')
    return plan,(source,response,initial,editor)


def adjudicate_file(path, remaining):
    deadline = time.monotonic()+remaining
    required = dict(response_sha256=sha(path),stage=path.stem)
    write_new_json(path.with_name(path.stem+'-host-required.json'),required)
    decision_path = path.with_name(path.stem+'-host-decision.json')
    independent = path.with_name(path.stem+'-independent.json')
    while time.monotonic() < deadline:
        try:
            decision = json.loads(decision_path.read_bytes())
            other = json.loads(independent.read_bytes())
        except (FileNotFoundError,UnicodeDecodeError,json.JSONDecodeError):
            time.sleep(.25)
            continue
        if (type(decision.get('accepted')) is not bool or other.get('accepted') is not decision['accepted']
                or decision.get('independent_sha256') != sha(independent)
                or any(any(row.get(k)!=v for k,v in required.items()) for row in (decision,other))
                or any(not isinstance(row.get('source_review'),str) or not row['source_review'].strip() for row in (decision,other))
                or decision['accepted'] and any(row.get('defects')!=[] for row in (decision,other))):
            raise ValueError('coarse_tail_host_binding')
        return decision
    raise ValueError('coarse_tail_host_deadline')


def run(args):
    if args.execute and (RUN_DIRECTORY.exists() or CLOSED_RESULT.exists()):
        raise ValueError('coarse_tail_closed_or_exists')
    plan,prepared = prepare()
    if not args.execute:
        if args.output: write_new_json(args.output,plan)
        return dict(plan_sha256=canonical_sha(plan),budget=plan['budget'],provider_requests=0,
            historical_closed=CLOSED_RESULT.exists(),execution_enabled=False)

    if (not args.env_file or not args.ci_run or args.plan_sha!=canonical_sha(plan)
            or plan!=json.loads(PREPARATION.read_bytes())):
        raise ValueError('coarse_tail_preparation_required')
    head = verify_public_ci(args.ci_run)
    RUN_DIRECTORY.mkdir(parents=True,exist_ok=False)
    write_new_json(RUN_DIRECTORY/'plan.json',dict(preparation_plan=plan,plan_sha256=canonical_sha(plan),head_sha=head,ci_run=args.ci_run))
    write_new_json(RUN_DIRECTORY/'source.json',dict(report=prepared[0].report,input_json=Workflow.build_inputs(prepared[0]).data_json))
    (RUN_DIRECTORY/'prepared-editor-request.json').write_bytes(validate_request(prepared[3],transport_id=CAPACITY_TRANSPORT_ID))
    generation,reviewer = load_role_settings(args.env_file)
    factory = RunScopedRoleReceiptedProviderFactory(generator_settings=generation,reviewer_settings=reviewer,
        transport_root=RUN_DIRECTORY/'transport',source_projection=PROJECTION)
    with route_environment('direct'):
        return observe(factory,RUN_DIRECTORY,plan,prepared,workflow_type=Workflow,initial_review_accepted=True,
            coach_contract=COARSE_ROLE_COACH_CONTRACT,adjudicate=adjudicate_file,
            before_send=lambda:require_unchanged_checkout(head))



if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file',type=Path)
    args = parser.parse_args()
    result = run(args)
    print(compact(result),flush=True)
    if args.execute and not result["tail_accepted"]: raise SystemExit(1)
