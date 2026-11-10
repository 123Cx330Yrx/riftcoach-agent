"""Deliver exact, receipt-bound policies to human stage reviewers.

This is a prospective task writer, not a provider or submission adapter.
Legacy builders and closed-batch replay stay byte-for-byte unchanged. Source,
stage and request validation is delegated to the existing live material readers.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.codex_review_event_source import TASK_KIND, review_task
from scripts.review_independence_contract import required_binding

VERSION = 'document-host-policy-delivery-v1'
STAGES = ('initial', 'revision', 'final')


def _policy(raw, expected_sha256):
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('host_policy_request_digest')
    # Do not normalize or repair JSON received from a receipt.
    from app.evaluation.golden_inference_scope_v5 import strict_json
    request = strict_json(raw.decode('utf-8'))
    messages = request.get('messages', [])
    systems = [m for m in messages if m.get('role') == 'system']
    if (len(systems) != 1 or not messages or messages[0] != systems[0]
            or not isinstance(systems[0].get('content'), str)
            or not systems[0]['content'].strip()):
        raise ValueError('host_policy_system_message')
    policy = systems[0]['content']
    return dict(request_sha256=expected_sha256,
        policy_sha256=hashlib.sha256(policy.encode('utf-8')).hexdigest(),
        policy_text=policy)


def with_policies(task, current_raw, *, initial_raw=None, initial_sha256=None):
    """Enrich an already verified native task without changing its binding.

The caller must validate the stage/receipt prefix first. Hashes bind policies
to those requests; their presence cannot prove that a reviewer applies them.
"""
    from app.evaluation.golden_inference_scope_v5 import strict_json
    value = strict_json(task)
    if (value.get('kind') != TASK_KIND or set(value) != {'kind', 'binding', 'instructions'}
            or not isinstance(value['instructions'], str) or not value['instructions'].strip()):
        raise ValueError('host_policy_base_task')
    bound = value['binding']
    if bound != required_binding(bound) or bound['stage'] not in STAGES:
        raise ValueError('host_policy_stage_binding')
    current = _policy(current_raw, bound['request_sha256'])
    policies = [dict(applies_to=bound['stage'], **current)]
    if bound['stage'] == 'revision':
        if initial_raw is None or initial_sha256 is None:
            raise ValueError('host_policy_initial_review_required')
        policies.insert(0, dict(applies_to='initial_review',
            **_policy(initial_raw, initial_sha256)))
    elif initial_raw is not None or initial_sha256 is not None:
        raise ValueError('host_policy_unexpected_initial_reference')
    reference = json.dumps(dict(version=VERSION, policies=policies),
        ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    instructions = (
        value['instructions'] + '\n\n'
        'Business-policy reference below is copied exactly from the verified issued request(s). '
        'Read the full policy together with the complete report, sources and output. '
        'Its provider tool/JSON instructions describe the model contract being assessed; '
        'they do not replace this Host task\'s output envelope or authorize calls, edits or tools. '
        'Assess every issue, explanation, correction and advisory under that contract. '
        'Advisory markers cannot hide a real error; optional wording preferences alone are not errors. '
        'For a disputed interpretation, state the actual asserted proposition, its whole-document '
        'basis and the source conflict or material unresolved ambiguity in source_review/defect.detail. '
        'Do not infer a universal or causal claim solely from a keyword. Explicit unsupported claims '
        'remain defects. Do not rewrite the output or manufacture reviewer agreement. '
        'Policy delivery proves neither semantic correctness nor historical reviewer ignorance.\n'
        'BEGIN VERIFIED BUSINESS-POLICY REFERENCE\n' + reference
        + '\nEND VERIFIED BUSINESS-POLICY REFERENCE')
    return review_task(bound, instructions)


def scan_task(directory, key):
    from scripts import document_review_scan_handoff as legacy
    # Legacy task() calls material() with closed=False and validates all receipts.
    task = legacy.task(directory, key)
    raw = (Path(directory) / legacy.runner.arm_name(key) / 'issued-request.json').read_bytes()
    return with_policies(task, raw)


def original_task(directory, key, stage):
    from scripts.role_stage_review_drafts import binding
    directory = Path(directory)
    if (directory / 'result.json').exists():
        raise ValueError('host_policy_batch_closed')
    bound = binding(directory, key, stage, profile='document-review', live=True)
    arm = directory / key.replace(':', '-')
    if ((arm / 'case-completed.json').exists() or (arm / f'{stage}-host.json').exists()
            or (arm / f'decision-{stage}.json').exists()):
        raise ValueError('host_policy_stage_closed')
    fields = ('key', 'input_sha256', 'stage', 'stage_sha256', 'response_sha256',
        'report_sha256', 'source_file_sha256', 'request_sha256', 'provider_response_sha256')
    fixed = {name: bound[name] for name in fields}
    if 'final_input_sha256' in bound:
        fixed['final_input_sha256'] = bound['final_input_sha256']
    needs_report = stage != 'initial' or bound['expected_initial'] == 'accept'
    report_rule = (
        'Include final_report with report_sha256, reviewer, source_review, '
        'facts_and_sources_correct, correct_content_preserved, identity_and_goal_preserved, '
        'true_errors_fixed. When accepted=true, all four boolean conditions must be true. '
        'Check every changed and retained part of the actual full report. '
        if needs_report else
        'Set final_report=null. You are assessing the initial opinion, not certifying the '
        'erroneous source report as fixed. Include target_and_correction_valid boolean; '
        'accept only when detection, explanations and correction intent are all sound. ')
    instructions = (
        f'Independently assess the actual {stage} stage in {arm}. '
        'Read complete source.json input_json/report, stage JSON, journal, prior stages, '
        'and actual transport requests and public model output. Do not inspect private reasoning. '
        'Check all facts, sources, comparisons, scope, identity, goals, dates, knowledge citations, '
        'corrections, advisories, editor reasons and preserved content. Original report errors correctly '
        'detected by the model belong in source_review, not Host defects. '
        'No Provider calls or file edits. Return ONLY JSON {binding: exact six task fields, '
        'review: assessment}. In review retain these exact metadata fields: '
        + json.dumps(fixed, ensure_ascii=False) + '. '
        'Include reviewer, source_review, accepted boolean and defects [{kind, detail}]. '
        'accepted=true requires defects=[]; rejection requires concrete defects. '
        'Valid kinds: missed_error,false_positive,unsupported_explanation,wrong_correction,'
        'unsupported_source,internal_contradiction,wrong_final_report,correct_content_lost,'
        'identity_or_goal_changed. ' + report_rule
        + 'Do not supply independent_source_event or primary_attestation; provenance is imported '
        'from your real native final. No expected label substitutes for full-source judgment.')
    transport = directory / 'transport' / key.replace(':', '-')
    ordinal = STAGES.index(stage) + 1
    role_dir = 'generation' if stage == 'revision' else 'review'
    raw = (transport / role_dir / f'request-{ordinal:03d}.json').read_bytes()
    initial_raw = initial_sha = None
    if stage == 'revision':
        # binding() validated the entire prefix. Read its independently recorded
        # first receipt digest rather than trusting a newly supplied file hash.
        from app.evaluation.document_review_qualification import read_calls
        from scripts.diagnose_role_context import canonical_sha
        calls = read_calls(transport)
        if (len(calls) != ordinal or canonical_sha([c['artifact_sha256'] for c in calls])
                != bound['receipt_prefix_sha256']):
            raise ValueError('host_policy_receipt_prefix_changed')
        initial_sha = calls[0]['binding']['request_sha256']
        initial_raw = (transport / 'review' / 'request-001.json').read_bytes()
    return with_policies(review_task(bound, instructions), raw,
        initial_raw=initial_raw, initial_sha256=initial_sha)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, choices=('scan', 'document-review'))
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--key', required=True)
    parser.add_argument('--stage', default='initial', choices=STAGES)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.profile == 'scan' and args.stage != 'initial':
        parser.error('scan only supports initial')
    task = (scan_task(args.directory, args.key) if args.profile == 'scan'
        else original_task(args.directory, args.key, args.stage))
    if args.output:
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(task + '\n')
    else:
        print(task)


if __name__ == '__main__':
    main()
