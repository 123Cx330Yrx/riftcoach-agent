"""Append-only human working opinions for explicitly opted-in observations.

These records are not quality decisions or new task time. A final submission
only materializes the unchanged human-review files consumed by the old gates.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import digest
from app.evaluation.golden_stream_bridge import REQUEST
from app.evaluation.role_task_outcome import ReportAssessment, StageAssessment, stage_identity
from scripts.diagnose_role_context import canonical_sha
from scripts.role_host_identity import candidate_sha256

MODE_V1 = 'independent-drafts-v1'
MODE_V2 = 'independent-drafts-v2'
# Kept as the legacy fixture default. New frozen plans must opt into MODE_V2.
MODE = MODE_V1
SUPPORTED_MODES = frozenset((MODE_V1, MODE_V2))
MODE_FIELD = 'host_review_submission_mode'
STAGES = ('initial', 'revision', 'final')


def _fail(code):
    raise ValueError('host_review_' + code)


def _read(path):
    return json.loads(path.read_bytes())


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    # Same bytes as the existing durable, create-only golden writer.
    return (json.dumps(value, sort_keys=True, ensure_ascii=True,
        separators=(',', ':')) + '\n').encode()


def plan_mode(run, *, required=False):
    path = Path(run)/'plan.json'
    if not path.exists():
        if required:
            _fail('plan_missing')
        return None  # Legacy standalone file-handoff tests have no run plan.
    saved = _read(path)
    plan = saved['preparation_plan']
    mode = plan.get(MODE_FIELD)
    if mode is not None and (mode not in SUPPORTED_MODES or saved.get('plan_sha256') != canonical_sha(plan)):
        _fail('plan_mode_or_hash')
    return mode


def _paths(run, key, stage):
    run = Path(run).resolve()
    if stage not in STAGES:
        _fail('stage')
    arm = run/key.replace(':', '-')
    if arm.resolve().parent != run:
        _fail('path')
    return run, arm, arm/(stage+'.json'), arm/'review-drafts'/stage


def _formal_names(stage):
    return ('independent-'+stage+'-review.json', 'primary-'+stage+'-review.json',
        'decision-'+stage+'.json')


def _open(run, arm, stage, *, partial_submission=False):
    if (run/'result.json').exists() or (arm/'case-completed.json').exists() or (arm/(stage+'-host.json')).exists():
        _fail('closed')
    if (arm/('decision-'+stage+'.json')).exists():
        _fail('already_submitted')
    if not partial_submission and any((arm/name).exists() for name in _formal_names(stage)):
        _fail('formal_file_exists')


def binding(run, key, stage, *, profile=None, live=False):
    """Bind the actual frozen plan, source, stage and complete receipt prefix."""
    from scripts.role_continuation import rebuild_stage_prefix
    run, arm, path, _ = _paths(run, key, stage)
    if plan_mode(run) not in SUPPORTED_MODES:
        _fail('opt_in_required')
    saved = _read(run/'plan.json')
    plan = saved['preparation_plan']
    # Select by the saved execution identity, then validate the complete trusted
    # identity below. A profile label alone never authorizes a different policy.
    from app.evaluation import correction_scope_qualification, boundary_examples_qualification
    backends = {'correction-scope': correction_scope_qualification,
                'boundary-examples': boundary_examples_qualification}
    matched = [name for name, candidate in backends.items()
               if plan.get('identity', {}).get('workflow_id') == candidate.CONTRACT_ID]
    if len(matched) != 1 or profile is not None and profile != matched[0]:
        _fail('opt_in_required')
    profile = matched[0]
    backend = backends[profile]
    rows = [r for r in plan['cases'] if r['key'] == key]
    if len(rows) != 1:
        _fail('case')
    row = rows[0]
    required_path = arm/(stage+'-host-required.json')
    required = _read(required_path)
    if (required.get(MODE_FIELD) != plan[MODE_FIELD]
            or required.get('stage_file') != path.name
            or required.get('decision_file') != 'decision-'+stage+'.json'
            or required.get('response_sha256') != _sha(path)):
        _fail('required_binding')
    value, source = _read(path), _read(arm/'source.json')
    frozen_source = [(f, s) for f, s in backend.old.frozen_cases()[0] if f['key'] == key]
    if len(frozen_source) != 1:
        _fail('case')
    frozen, original_source = frozen_source[0]
    expected_source = dict(input_json=backend.Workflow.build_inputs(original_source).data_json,
        report=original_source.report, input_sha256=frozen['input_sha256'], report_sha256=frozen['report_sha256'])
    if source != expected_source:
        _fail('original_source_changed')
    if (value['key'] != key or value['stage'] != stage
            or value['report_sha256'] != digest(value['report'])
            or source['input_sha256'] != row['input_sha256']
            or source['report_sha256'] != row['report_sha256']
            or digest(source['report']) != row['report_sha256']
            or (stage == 'initial' and value['report'] != source['report'])
            or _sha(run/(key.replace(':', '-')+'-prepared-request.json')) != row['request_sha256']):
        _fail('source_or_stage_binding')
    calls = backend.read_calls(run/'transport'/key.replace(':', '-'))
    ordinal = STAGES.index(stage) + 1
    prefix = calls[:ordinal]
    if (len(prefix) != ordinal or (live and len(calls) != ordinal)
            or [c['binding']['role'] for c in prefix] != ['review', 'revision', 'review'][:ordinal]
            or not all(c['completed'] and c['usage'] is not None for c in prefix)):
        _fail('actual_call_inventory')
    prepared = REQUEST.validate_json((run/(key.replace(':', '-')+'-prepared-request.json')).read_bytes(), strict=True)
    issued = prefix[0]['request']
    metadata = dict(issued.metadata)
    metadata.pop('coach_budget_contract', None)
    if replace(issued, timeout_s=prepared.timeout_s, metadata=metadata) != prepared or issued.timeout_s > prepared.timeout_s:
        _fail('actual_request_changed')
    stages, _ = rebuild_stage_prefix(original_source, prefix, backend)
    expected_stage = stages[-1]
    if value != dict(expected_stage, key=key, report_sha256=digest(expected_stage['report'])):
        _fail('actual_stage_changed')
    if (expected_stage['journal'] is not None
            and _read(arm/(stage+'-journal.json')) != expected_stage['journal']):
        _fail('actual_journal_changed')
    call = prefix[-1]['binding']
    transport = run/'transport'/key.replace(':', '-')
    actual = dict(run_directory=run.as_posix(), profile=profile,
        plan_file_sha256=_sha(run/'plan.json'), plan_sha256=saved['plan_sha256'],
        candidate_sha256=candidate_sha256(plan['identity'], backend=backend),
        key=key, input_sha256=row['input_sha256'], prepared_request_sha256=row['request_sha256'],
        stage=stage, stage_sha256=stage_identity(value), response_sha256=_sha(path),
        report_sha256=digest(value['report']), source_file_sha256=_sha(arm/'source.json'),
        required_file_sha256=_sha(required_path), call_ordinal=ordinal,
        request_sha256=call['request_sha256'],
        provider_response_sha256=_sha(transport/call['raw_directory']/f'response-{ordinal:03d}.json'),
        receipt_prefix_sha256=canonical_sha([c['artifact_sha256'] for c in prefix]),
        expected_initial=row['expected_initial'])
    if value['journal'] is not None:
        actual['final_input_sha256'] = value['journal']['input_sha256']
    return actual


def _review(review, bound, confirmed):
    if type(confirmed) is not bool or not isinstance(review, dict):
        _fail('confirmation_required')
    fields = ('key', 'input_sha256', 'stage', 'stage_sha256', 'response_sha256',
        'report_sha256', 'source_file_sha256', 'request_sha256', 'provider_response_sha256')
    fields += ('final_input_sha256',) if 'final_input_sha256' in bound else ()
    if any(k in review and review[k] != bound[k] for k in fields):
        _fail('review_binding')
    value = dict(review, **{k: bound[k] for k in fields})
    if not all(isinstance(value.get(k), str) and value[k].strip() for k in ('reviewer', 'source_review')):
        _fail('review_reason_required')
    if not confirmed and value.get('accepted') is None:
        return value  # An unresolved working opinion cannot be submitted.
    StageAssessment.model_validate({k: value[k] for k in
        ('stage', 'stage_sha256', 'reviewer', 'source_review', 'accepted', 'defects')})
    needs_report = bound['stage'] != 'initial' or bound['expected_initial'] == 'accept'
    if needs_report:
        report = ReportAssessment.model_validate(value.get('final_report'))
        if report.report_sha256 != bound['report_sha256']:
            _fail('report_binding')
        if confirmed and value['accepted'] and not all((
                report.facts_and_sources_correct, report.correct_content_preserved,
                report.identity_and_goal_preserved, report.true_errors_fixed)):
            _fail('report_not_accepted')
    elif confirmed and value['accepted'] and value.get('target_and_correction_valid') is not True:
        _fail('correction_confirmation_required')
    return value


def _principal_registry(run):
    """Load the v2 plan registry; identity comes from the host contract."""
    from scripts import review_independence_contract as contract
    saved = _read(Path(run) / 'plan.json')
    plan = saved['preparation_plan']
    if plan.get(MODE_FIELD) != MODE_V2:
        return None
    registry = plan.get('review_principals')
    if not isinstance(registry, dict) or set(registry) != {'primary', 'independent'}:
        _fail('principal_registry_incomplete')
    try:
        contract._registry(plan)
    except ValueError as exc:
        _fail(str(exc).removeprefix('review_independence_'))
    return registry


def _verify_principal_review(run, bound, review, *, role, event_source=None, trusted_event=None):
    registry = _principal_registry(run)
    if registry is None:
        return
    from scripts import review_independence_contract as contract
    try:
        plan = _read(Path(run) / 'plan.json')['preparation_plan']
        if role == 'primary':
            contract.validate_primary_attestation(review, plan=plan, bound=bound)
        else:
            contract.validate_independent_event(review, plan=plan, bound=bound,
                                                event=trusted_event, event_source=event_source)
    except ValueError as exc:
        _fail(str(exc).removeprefix('review_independence_'))


def _chain(directory, bound, *, run=None, event_source=None):
    if not directory.exists():
        return []
    paths = sorted(directory.iterdir())
    chain, previous = [], None
    for index, path in enumerate(paths, 1):
        if not path.is_file() or path.name != f'{index:06d}.json':
            _fail('chain_inventory')
        raw = path.read_bytes()
        value = json.loads(raw)
        if (value.get('sequence') != index or type(value.get('sequence')) is not int
                or value.get('supersedes_sha256') != previous or value.get('binding') != bound
                or (chain and chain[-1][0]['kind'] == 'submission')):
            _fail('chain_changed')
        if value.get('kind') == 'draft':
            if not isinstance(value.get('reason'), str) or not value['reason'].strip():
                _fail('change_reason_required')
            if _review(value['review'], bound, value.get('confirmed')) != value['review']:
                _fail('review_binding')
            if run is not None:
                _verify_principal_review(run, bound, value['review'], role='independent',
                                         event_source=event_source)
        elif value.get('kind') == 'submission':
            if (not chain or chain[-1][0].get('confirmed') is not True
                    or value.get('independent_draft_sha256') != previous):
                _fail('latest_confirmed_draft_required')
            if set(value.get('formal_files', {})) != set(_formal_names(bound['stage'])):
                _fail('formal_inventory')
            if value['formal_files'][_formal_names(bound['stage'])[0]] != chain[-1][0]['review']:
                _fail('submitted_review_changed')
        else:
            _fail('chain_kind')
        previous = hashlib.sha256(raw).hexdigest()
        chain.append((value, previous))
    return chain


def _append(directory, chain, value):
    directory.mkdir(parents=True, exist_ok=True)
    value = dict(value, sequence=len(chain)+1, supersedes_sha256=chain[-1][1] if chain else None)
    path = directory/f'{len(chain)+1:06d}.json'
    try:
        write_new_json(path, value)
    except FileExistsError:
        _fail('chain_changed')
    return value, _sha(path)


def write_independent_draft(run, key, stage, review, *, profile='correction-scope',
                           supersedes_sha256=None, reason, confirmed=False, before_write=lambda: None,
                           event_source=None):
    run, arm, _, directory = _paths(run, key, stage)
    _open(run, arm, stage)
    bound = binding(run, key, stage, profile=profile, live=True)
    chain = _chain(directory, bound, run=run, event_source=event_source)
    if (chain and chain[-1][0]['kind'] == 'submission'):
        _fail('already_submitted')
    if supersedes_sha256 != (chain[-1][1] if chain else None):
        _fail('latest_draft_required')
    if not isinstance(reason, str) or not reason.strip():
        _fail('change_reason_required')
    review = _review(deepcopy(review), bound, confirmed)
    _verify_principal_review(run, bound, review, role='independent', event_source=event_source)
    before_write()
    _open(run, arm, stage)
    if binding(run, key, stage, profile=profile, live=True) != bound:
        _fail('binding_changed')
    _, sha = _append(directory, chain, dict(kind='draft', binding=bound,
        review=review, confirmed=confirmed, reason=reason))
    return dict(key=key, stage=stage, draft_sha256=sha, confirmed=confirmed)


def finalize_stage_review(run, key, stage, primary_notes, *, profile='correction-scope',
                          independent_draft_sha256, before_write=lambda: None, event_source=None):
    # Import only at the explicit submission boundary; legacy writer imports
    # this module too. Both paths share the original decision construction.
    from scripts.write_role_stage_decision import build_formal_decision
    primary_notes = deepcopy(primary_notes)
    run, arm, path, directory = _paths(run, key, stage)
    _open(run, arm, stage, partial_submission=True)
    bound = binding(run, key, stage, profile=profile, live=True)
    chain = _chain(directory, bound, run=run, event_source=event_source)
    if not chain:
        _fail('latest_confirmed_draft_required')
    last, tip = chain[-1]
    if last['kind'] == 'submission':
        if last['independent_draft_sha256'] != independent_draft_sha256 or last['primary_notes'] != primary_notes:
            _fail('submitted_opinion_changed')
        submission = last
    else:
        _open(run, arm, stage)
        if tip != independent_draft_sha256 or last.get('confirmed') is not True:
            _fail('latest_confirmed_draft_required')
        other = last['review']
        _verify_principal_review(run, bound, other, role='independent', event_source=event_source)
        primary, decision = build_formal_decision(run, key, stage, primary_notes, other,
            independent_sha256=hashlib.sha256(encoded(other)).hexdigest(), profile=profile)
        names = _formal_names(stage)
        before_write()
        _open(run, arm, stage)
        if binding(run, key, stage, profile=profile, live=True) != bound:
            _fail('binding_changed')
        submission, tip = _append(directory, chain, dict(kind='submission', binding=bound,
            independent_draft_sha256=independent_draft_sha256, primary_notes=primary_notes,
            formal_files=dict(zip(names, (other, primary, decision)))))
    _validate_formal_snapshot(submission)
    # A committed snapshot is recoverable, but cannot be replaced by a new
    # judgment. Existing bytes are verified and never rewritten, even on error.
    for name in _formal_names(stage):
        before_write()
        _open(run, arm, stage, partial_submission=True)
        if (binding(run, key, stage, profile=profile, live=True) != bound
                or _chain(directory, bound, run=run, event_source=event_source)[-1][1] != tip):
            _fail('binding_or_chain_changed')
        target = arm/name
        expected = submission['formal_files'][name]
        if target.exists():
            if target.read_bytes() != encoded(expected):
                _fail('formal_file_changed')
            continue
        try:
            write_new_json(target, expected)
        except FileExistsError:
            if target.read_bytes() != encoded(expected):
                _fail('formal_file_changed')
    return submission['formal_files']['decision-'+stage+'.json']


def _validate_formal_snapshot(submission):
    from scripts.write_role_stage_decision import build_formal_decision
    bound = submission['binding']
    names = _formal_names(bound['stage'])
    other = submission['formal_files'][names[0]]
    primary, decision = build_formal_decision(bound['run_directory'], bound['key'], bound['stage'],
        submission['primary_notes'], other, independent_sha256=hashlib.sha256(encoded(other)).hexdigest(),
        profile=bound['profile'])
    # v2 requires both sides of the identity contract.  The primary
    # attestation is checked here after the formal snapshot is reconstructed;
    # a hand-authored primary JSON cannot bypass the same-body check.
    run = Path(bound['run_directory'])
    if plan_mode(run) == MODE_V2:
        _verify_principal_review(run, bound, primary, role='primary')
    if submission['formal_files'] != dict(zip(names, (other, primary, decision))):
        _fail('submitted_opinion_changed')


def validate_submission(path, *, expected_mode=None, event_source=None):
    """Extra handoff bookkeeping only; the existing strict gate still follows."""
    path = Path(path)
    run, arm, stage = path.parent.parent, path.parent, path.stem
    mode = plan_mode(run, required=True)
    required_path = arm/(stage+'-host-required.json')
    required = _read(required_path) if required_path.exists() else {}
    if expected_mode is not None and mode != expected_mode:
        _fail('plan_mode_changed')
    if required.get(MODE_FIELD) != mode:
        _fail('required_mode_changed')
    if mode is None:
        if (arm/'review-drafts'/stage).exists():
            _fail('opt_in_required')
        return
    value = _read(path)
    bound = binding(run, value['key'], stage)
    chain = _chain(arm/'review-drafts'/stage, bound, run=run, event_source=event_source)
    if not chain or chain[-1][0]['kind'] != 'submission':
        _fail('submission_required')
    submission = chain[-1][0]
    _validate_formal_snapshot(submission)
    for name in _formal_names(stage):
        if (arm/name).read_bytes() != encoded(submission['formal_files'][name]):
            _fail('formal_file_changed')
