"""Prospective accepted-tail run with pinned Host tasks; no old-batch restart.

Reuse the frozen workload, model requests, budget and observer. A new run_id
and preparation explicitly bind the prospective checkpoint/abort adapters.
The observer's experiment label is the unchanged workload label, not the run_id.
"""
import argparse
import json
from pathlib import Path
import re
import time

from scripts import run_document_accepted_tails as legacy
from scripts import host_review_task_checkpoint as checkpoint

base = legacy.base
backend, Exchange = legacy.backend, legacy.Exchange
KEYS, STAGES = legacy.KEYS, legacy.STAGES
HISTORICAL_RUN = legacy.HISTORICAL_RUN
SEAL_SHA = legacy.SEAL_SHA
controls = legacy.controls
EXPERIMENT = legacy.EXPERIMENT
RUN_ID = 'document-checkpoint-tails-20261009'
SOURCE_FILES = (*legacy.SOURCE_FILES,
    'scripts/run_document_checkpoint_tails.py',
    'scripts/document_checkpoint_tail_handoff.py',
    'scripts/seal_document_checkpoint_tails.py',
    'scripts/host_review_task_checkpoint.py')
ABORT_KIND = 'document-checkpoint-tail-operator-abort-v1'
ABORT_REASONS = ('native_binding_failure','checkpoint_unavailable','reviewer_unavailable',
    'source_or_request_changed')


def prepare(*,root_thread_id,independent_thread_id):
    plan = legacy.prepare(root_thread_id=root_thread_id,independent_thread_id=independent_thread_id)
    plan.update(run_id=RUN_ID,host_task_checkpoint=dict(version=checkpoint.VERSION,
        required_for_submit=True,read_after_recovery_and_before_final=True,
        no_primary_opinion_access=True,checkpoint_is_not_review_attestation=True),
        operator_abort_kind=ABORT_KIND)
    plan['source_sha256'].update({p:base.digest((base.ROOT/p).read_text(encoding='utf-8'))
        for p in SOURCE_FILES if p not in plan['source_sha256']})
    return plan


def validate_abort(value,bound):
    if (not isinstance(value,dict) or set(value) != {'kind','binding','reason','native_event_reference'}
            or value['kind'] != ABORT_KIND or value['binding'] != bound
            or value['reason'] not in ABORT_REASONS
            or (value['native_event_reference'] is not None and
                (not isinstance(value['native_event_reference'],str) or not re.fullmatch(
                    r'[0-9a-f-]{36}/[0-9a-f-]{36}/msg_[0-9a-f]+',value['native_event_reference'])))):
        raise ValueError('checkpoint_tail_abort_binding_or_format')


def wait_reviews(path,remaining):
    path = Path(path)
    bound = json.loads(path.read_bytes())['binding']
    submission = path.with_name('review-submission.json')
    abort = path.with_name('operator-abort.json')
    print(base.compact(dict(host_review_required=str(path),submission=str(submission),
        operator_abort=str(abort),remaining_host_seconds=remaining)),flush=True)
    deadline = time.monotonic()+remaining
    while time.monotonic()<deadline:
        if abort.exists():
            if submission.exists():raise ValueError('checkpoint_tail_conflicting_host_decision')
            validate_abort(json.loads(abort.read_bytes()),bound)
            raise ValueError('checkpoint_tail_operator_abort')
        if submission.exists():return json.loads(submission.read_bytes())
        time.sleep(.25)
    raise ValueError('coarse_diagnostic_host_deadline')


def observe(factory,directory,plan,*,event_source,adjudicate=wait_reviews,before_send=lambda:None):
    if plan.get('run_id') != RUN_ID or plan.get('host_task_checkpoint',{}).get('version') != checkpoint.VERSION:
        raise ValueError('checkpoint_tail_plan')
    from scripts import document_checkpoint_tail_handoff as handoff
    def inspect_checkpoint(path,remaining):
        submission = adjudicate(path,remaining)
        folder = Path(path).parent
        required = json.loads(Path(path).read_bytes())
        value = json.loads((folder/'stage.json').read_bytes())
        bound = required['binding']
        expected_task = json.loads(handoff.task_from_stage(plan,value,bound,folder.parent))
        handoff.validate_checkpoint_files(folder,submission,expected_task,plan,bound)
        # The legacy observer next checks the in-memory stage and binding,
        # native authorship, report flags and semantic quality before any send.
        return submission
    return legacy.observe(factory,directory,plan,event_source=event_source,
        adjudicate=inspect_checkpoint,before_send=before_send)


def execute(args,plan):
    directory = base.ROOT/'data/runs/model_comparison'/RUN_ID
    if directory.exists():raise ValueError('checkpoint_tail_closed_or_exists')
    if (not args.preparation or not args.env_file or not args.codex_executable
            or args.plan_sha != base.canonical_sha(plan) or plan != json.loads(args.preparation.read_bytes())):
        raise ValueError('checkpoint_tail_frozen_preparation_required')
    head = base.verify_public_ci(args.ci_run)
    base.require_unchanged_checkout(head)
    with base.CodexReadOnlyClient(args.codex_executable) as client:
        base.verify_native_principals(client,plan)
        event_source = base.CodexHostReviewEventSource(client,plan)
        base.require_execution_event_source(plan,event_source)
        generator,reviewer = base.load_role_settings(args.env_file)
        factory = backend.ProviderFactory(generator_settings=generator,reviewer_settings=reviewer,
            transport_root=directory/'transport')
        directory.mkdir(parents=True,exist_ok=False)
        base.write_new_json(directory/'plan.json',dict(preparation_plan=plan,
            plan_sha256=base.canonical_sha(plan),execution_head_sha=head,ci_run=args.ci_run))
        with base.route_environment('direct'):
            return observe(factory,directory,plan,event_source=event_source,
                before_send=lambda:base.require_unchanged_checkout(head))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root-thread-id',required=True)
    parser.add_argument('--independent-thread-id',required=True)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--execute',action='store_true')
    for name in ('preparation','env-file','codex-executable'):parser.add_argument('--'+name,type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    args = parser.parse_args()
    plan = prepare(root_thread_id=args.root_thread_id,independent_thread_id=args.independent_thread_id)
    if args.execute:result=execute(args,plan)
    else:
        if args.output:base.write_new_json(args.output,plan)
        result=dict(plan_sha256=base.canonical_sha(plan),run_id=RUN_ID,budget=plan['budget'],provider_calls=0)
    print(base.compact(result),flush=True)
    if args.execute and not result['scan_completed']:raise SystemExit(1)


if __name__ == '__main__':main()
