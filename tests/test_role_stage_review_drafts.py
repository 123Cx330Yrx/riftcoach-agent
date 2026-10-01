"""Working human opinions never release IO or become a new quality protocol."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import digest
from scripts import role_stage_review_drafts as drafts
from scripts import write_role_stage_decision as writer
from scripts import run_correction_scope_qualification as campaign
from scripts import run_role_task_observation as observer
from scripts import qualify_role_observations as audit
from scripts.diagnose_role_context import canonical_sha
from tests.test_role_observation_qualification import make_run, read, change


@pytest.fixture
def pending(make_run, tmp_path):
    """Only synthetic copied receipts are opened; real closed runs stay intact."""
    original, _ = make_run(('claim-scope:1',), profile='correction-scope')
    run = tmp_path/'pending'
    shutil.copytree(original, run)
    arm = run/'claim-scope-1'
    independent = read(arm/'independent-initial-review.json')
    primary = read(arm/'primary-initial-review.json')
    notes = {k: primary[k] for k in ('accepted', 'defects', 'reason',
        'target_and_correction_valid', 'final_report_checks', 'report_reason')}
    for name in (*drafts._formal_names('initial'), 'initial-host.json',
                 'case-completed.json', 'task-observation.json'):
        (arm/name).unlink()
    (run/'result.json').unlink()
    saved = read(run/'plan.json')
    saved['preparation_plan'][drafts.MODE_FIELD] = drafts.MODE
    saved['plan_sha256'] = canonical_sha(saved['preparation_plan'])
    (run/'plan.json').write_text(json.dumps(saved), encoding='utf-8')
    required = dict(stage_file='initial.json', decision_file='decision-initial.json',
        response_sha256=audit._sha(arm/'initial.json'), remaining_seconds=100,
        host_review_submission_mode=drafts.MODE)
    write_new_json(arm/'initial-host-required.json', required)
    return run, arm, independent, notes


@pytest.fixture(params=['revision', 'final'])
def pending_edited(make_run, tmp_path, request):
    """Open a copied, real response prefix at its editor or final host gate."""
    stage = request.param
    original, _ = make_run(('claim-scope:4',), profile='correction-scope')
    run = tmp_path/'pending-edited'
    shutil.copytree(original, run)
    arm = run/'claim-scope-4'
    independent = read(arm/('independent-'+stage+'-review.json'))
    primary = read(arm/('primary-'+stage+'-review.json'))
    notes = {k: primary[k] for k in ('accepted', 'defects', 'reason',
        'target_and_correction_valid', 'final_report_checks', 'report_reason')}
    ordinal = drafts.STAGES.index(stage)+1
    transport = run/'transport/claim-scope-4'
    for call in campaign.qualification.read_calls(transport)[ordinal:]:
        for name in call['artifact_sha256']:
            (transport/name).unlink()
    for index, name in enumerate(drafts.STAGES):
        if index < ordinal-1:
            continue
        for artifact in (*drafts._formal_names(name), name+'-host.json'):
            (arm/artifact).unlink()
        if index >= ordinal:
            (arm/(name+'.json')).unlink()
            if (arm/(name+'-journal.json')).exists():
                (arm/(name+'-journal.json')).unlink()
    for name in ('case-completed.json', 'task-observation.json'):
        (arm/name).unlink()
    (run/'result.json').unlink()
    saved = read(run/'plan.json')
    saved['preparation_plan'][drafts.MODE_FIELD] = drafts.MODE
    saved['plan_sha256'] = canonical_sha(saved['preparation_plan'])
    (run/'plan.json').write_text(json.dumps(saved), encoding='utf-8')
    write_new_json(arm/(stage+'-host-required.json'), dict(stage_file=stage+'.json',
        decision_file='decision-'+stage+'.json', response_sha256=audit._sha(arm/(stage+'.json')),
        remaining_seconds=100, host_review_submission_mode=drafts.MODE))
    return run, arm, stage, independent, notes


def propose(pending, *, review=None, previous=None, confirmed=True, **options):
    run, _, independent, _ = pending
    return drafts.write_independent_draft(run, 'claim-scope:1', 'initial',
        independent if review is None else review,
        supersedes_sha256=previous, reason='Explicit offline source review or correction.',
        confirmed=confirmed, **options)['draft_sha256']


def submit(pending, sha, **options):
    run, _, _, notes = pending
    return writer.write_decision(run, 'claim-scope:1', 'initial', notes,
        profile='correction-scope', independent_draft_sha256=sha, **options)


def rejected(review):
    return dict(deepcopy(review), accepted=False,
        defects=[dict(kind='wrong_correction', detail='Offline disputed working opinion.')],
        target_and_correction_valid=False)


def test_working_rejection_can_be_explicitly_corrected_before_submission(pending):
    run, arm, independent, _ = pending
    first = propose(pending, review=rejected(independent), confirmed=False)
    corrected = propose(pending, previous=first)
    assert not any((arm/n).exists() for n in drafts._formal_names('initial'))
    decision = submit(pending, corrected)
    assert decision['accepted']
    assert read(arm/'review-drafts/initial/000001.json')['review']['accepted'] is False
    assert read(arm/'review-drafts/initial/000003.json')['kind'] == 'submission'
    drafts.validate_submission(arm/'initial.json')
    assert campaign.validate_handoff(arm/'initial.json', decision,
        read(run/'plan.json')['preparation_plan'], directory=run) == decision


def test_latest_negative_cannot_be_skipped_or_implicitly_overruled(pending):
    _, arm, independent, _ = pending
    positive = propose(pending)
    negative = propose(pending, review=rejected(independent), previous=positive)
    with pytest.raises(ValueError, match='latest_confirmed_draft_required'):
        submit(pending, positive)
    with pytest.raises(ValueError, match='independent_binding_or_rejection'):
        submit(pending, negative)
    assert not any((arm/n).exists() for n in drafts._formal_names('initial'))
    assert len(list((arm/'review-drafts/initial').iterdir())) == 2


@pytest.mark.parametrize('unknown', [False, True])
def test_unconfirmed_or_unknown_opinion_never_releases_stage(pending, unknown):
    _, arm, independent, _ = pending
    review = dict(independent, accepted=None) if unknown else independent
    sha = propose(pending, review=review, confirmed=False)
    with pytest.raises(ValueError, match='latest_confirmed_draft_required'):
        submit(pending, sha)
    assert not (arm/'decision-initial.json').exists()


def test_primary_can_explicitly_reject_without_changing_independent_acceptance(pending):
    _, arm, _, notes = pending
    sha = propose(pending)
    notes.update(accepted=False, defects=[dict(kind='wrong_final_report', detail='Explicit primary rejection.')])
    decision = submit(pending, sha)
    assert decision['accepted'] is False
    assert read(arm/'independent-initial-review.json')['accepted'] is True
    drafts.validate_submission(arm/'initial.json')


def test_draft_must_supersede_exact_current_tip_and_explain_change(pending):
    run, _, independent, _ = pending
    sha = propose(pending)
    with pytest.raises(ValueError, match='latest_draft_required'):
        propose(pending)
    with pytest.raises(ValueError, match='change_reason_required'):
        drafts.write_independent_draft(run, 'claim-scope:1', 'initial', independent,
            supersedes_sha256=sha, reason=' ', confirmed=True)


def test_new_negative_winning_append_race_prevents_old_positive_submission(pending):
    _, arm, independent, _ = pending
    positive = propose(pending)
    def arrive():
        propose(pending, review=rejected(independent), previous=positive)
    with pytest.raises(ValueError, match='chain_changed'):
        submit(pending, positive, before_write=arrive)
    assert not any((arm/n).exists() for n in drafts._formal_names('initial'))
    assert read(arm/'review-drafts/initial/000002.json')['review']['accepted'] is False


def test_submission_winning_race_freezes_later_draft(pending):
    _, arm, independent, _ = pending
    positive = propose(pending)
    with pytest.raises(ValueError, match='already_submitted'):
        propose(pending, previous=positive, review=rejected(independent),
            before_write=lambda: submit(pending, positive))
    assert len(list((arm/'review-drafts/initial').iterdir())) == 2


@pytest.mark.parametrize('failure', ['independent-initial-review.json', 'primary-initial-review.json', 'decision-initial.json'])
def test_partial_submission_resumes_same_snapshot_without_overwriting(pending, monkeypatch, failure):
    _, arm, _, _ = pending
    sha = propose(pending)
    original = drafts.write_new_json
    def crash(path, value):
        if path.name == failure:
            raise OSError('offline crash before publication')
        original(path, value)
    with monkeypatch.context() as patch:
        patch.setattr(drafts, 'write_new_json', crash)
        with pytest.raises(OSError):
            submit(pending, sha)
    existing = {n: ((arm/n).read_bytes(), (arm/n).stat().st_mtime_ns)
        for n in drafts._formal_names('initial') if (arm/n).exists()}
    assert read(arm/'review-drafts/initial/000002.json')['kind'] == 'submission'
    assert submit(pending, sha)['accepted']
    for name, (raw, modified) in existing.items():
        assert (arm/name).read_bytes() == raw
        assert (arm/name).stat().st_mtime_ns == modified
    drafts.validate_submission(arm/'initial.json')


def test_partial_submission_cannot_change_opinion_or_replace_conflicting_formal_bytes(pending, monkeypatch):
    _, arm, _, notes = pending
    sha = propose(pending)
    original = drafts.write_new_json
    def crash(path, value):
        if path.name == 'primary-initial-review.json':
            raise OSError('offline crash')
        original(path, value)
    with monkeypatch.context() as patch:
        patch.setattr(drafts, 'write_new_json', crash)
        with pytest.raises(OSError):
            submit(pending, sha)
    previous = notes['reason']
    notes['reason'] = 'A different primary opinion.'
    with pytest.raises(ValueError, match='submitted_opinion_changed'):
        submit(pending, sha)
    notes['reason'] = previous
    (arm/'independent-initial-review.json').write_bytes(b'{}')
    with pytest.raises(ValueError, match='formal_file_changed'):
        submit(pending, sha)
    assert (arm/'independent-initial-review.json').read_bytes() == b'{}'
    assert not (arm/'decision-initial.json').exists()


@pytest.mark.parametrize('name', ['independent-initial-review.json', 'primary-initial-review.json', 'decision-initial.json'])
def test_existing_formal_files_are_never_adopted_or_overwritten(pending, name):
    _, arm, _, _ = pending
    sha = propose(pending)
    (arm/name).write_bytes(b'{}')
    with pytest.raises(ValueError, match='(formal_file_exists|already_submitted)'):
        submit(pending, sha)
    assert (arm/name).read_bytes() == b'{}'


@pytest.mark.parametrize('defect', ['plan', 'source', 'stage', 'prepared', 'actual_request', 'actual_response', 'required_mode'])
def test_subject_changes_cannot_rebind_a_working_opinion(pending, defect):
    run, arm, _, _ = pending
    sha = propose(pending)
    if defect == 'plan':
        saved = read(run/'plan.json')
        saved['preparation_plan']['experiment'] = 'another-run'
        saved['plan_sha256'] = canonical_sha(saved['preparation_plan'])
        (run/'plan.json').write_text(json.dumps(saved), encoding='utf-8')
    elif defect == 'required_mode':
        change(arm/'initial-host-required.json', lambda d: d.pop(drafts.MODE_FIELD))
    else:
        target = {'source': arm/'source.json', 'stage': arm/'initial.json',
            'prepared': run/'claim-scope-1-prepared-request.json',
            'actual_request': run/'transport/claim-scope-1/review/request-001.json',
            'actual_response': run/'transport/claim-scope-1/review/response-001.json'}[defect]
        target.write_bytes(target.read_bytes()+b' ')
    with pytest.raises(ValueError):
        submit(pending, sha)
    assert not (arm/'decision-initial.json').exists()


def test_copied_cross_run_chain_is_rejected(pending, tmp_path):
    run, _, _, notes = pending
    sha = propose(pending)
    other = tmp_path/'other-run'
    shutil.copytree(run, other)
    with pytest.raises(ValueError, match='chain_changed'):
        drafts.finalize_stage_review(other, 'claim-scope:1', 'initial', notes,
            independent_draft_sha256=sha)


def test_first_draft_checks_original_source_content_not_self_reported_hashes(pending):
    _, arm, _, _ = pending
    original = read(arm/'source.json')
    change(arm/'source.json', lambda d: d.update(input_json='{}'))
    modified = read(arm/'source.json')
    assert modified['input_sha256'] == original['input_sha256']
    assert modified['report_sha256'] == original['report_sha256']
    with pytest.raises(ValueError, match='original_source_changed'):
        propose(pending)
    assert not (arm/'review-drafts').exists()
    assert not (arm/'decision-initial.json').exists()


def test_first_edited_draft_reconstructs_report_from_actual_responses(pending_edited):
    run, arm, stage, independent, _ = pending_edited
    path = arm/(stage+'.json')
    stage_value = read(path)
    stage_value['report'] += '\n\nContent never returned by the actual editor.'
    stage_value['report_sha256'] = digest(stage_value['report'])
    path.write_text(json.dumps(stage_value), encoding='utf-8')
    change(arm/(stage+'-host-required.json'), lambda d: d.update(response_sha256=audit._sha(path)))
    # A new human opinion can agree with all self-reported hashes; it still
    # cannot replace what the preceding actual response contained.
    review = {k: v for k, v in independent.items() if k not in (
        'key', 'input_sha256', 'stage', 'stage_sha256', 'response_sha256', 'report_sha256',
        'source_file_sha256', 'request_sha256', 'provider_response_sha256', 'final_input_sha256')}
    review['final_report']['report_sha256'] = stage_value['report_sha256']
    with pytest.raises(ValueError, match='actual_stage_changed'):
        drafts.write_independent_draft(run, 'claim-scope:4', stage, review,
            reason='Offline consistent self-hash attack.', confirmed=True)
    assert not (arm/'review-drafts').exists()
    assert not any((arm/n).exists() for n in drafts._formal_names(stage))


@pytest.mark.parametrize('include_stage', [False, True])
def test_first_draft_reconstructs_initial_journal_from_actual_response(pending, include_stage):
    _, arm, _, _ = pending
    path = arm/'initial.json'
    journal = read(arm/'initial-journal.json')
    journal['input_sha256'] = '0'*64
    (arm/'initial-journal.json').write_text(json.dumps(journal), encoding='utf-8')
    if include_stage:
        change(path, lambda d: d.update(journal=journal))
        change(arm/'initial-host-required.json', lambda d: d.update(response_sha256=audit._sha(path)))
    with pytest.raises(ValueError, match='actual_(stage|journal)_changed'):
        propose(pending)
    assert not (arm/'review-drafts').exists()
    assert not (arm/'decision-initial.json').exists()


@pytest.mark.parametrize('field,value', [('key', 'scope:3'), ('stage', 'final'),
    ('source_file_sha256', '0'*64), ('request_sha256', '0'*64)])
def test_foreign_opinion_binding_cannot_be_silently_replaced(pending, field, value):
    _, arm, independent, _ = pending
    with pytest.raises(ValueError, match='review_binding'):
        propose(pending, review=dict(independent, **{field: value}))
    assert not (arm/'review-drafts').exists()


def test_post_submission_or_closed_batch_cannot_receive_corrections(pending):
    run, _, _, _ = pending
    sha = propose(pending)
    submit(pending, sha)
    with pytest.raises(ValueError, match='already_submitted'):
        propose(pending, previous=sha)
    write_new_json(run/'result.json', {'closed': True})
    with pytest.raises(ValueError, match='closed'):
        submit(pending, sha)


def test_closure_between_formal_writes_does_not_publish_decision(pending, monkeypatch):
    run, arm, _, _ = pending
    sha = propose(pending)
    original = drafts.write_new_json
    def close(path, value):
        original(path, value)
        if path.name == 'primary-initial-review.json':
            original(run/'result.json', {'closed': True})
    monkeypatch.setattr(drafts, 'write_new_json', close)
    with pytest.raises(ValueError, match='closed'):
        submit(pending, sha)
    assert not (arm/'decision-initial.json').exists()


def test_direct_formal_files_cannot_bypass_opted_in_actual_handoff(pending):
    run, arm, independent, notes = pending
    primary, decision = writer.build_formal_decision(run, 'claim-scope:1', 'initial', notes,
        independent, independent_sha256=hashlib.sha256(drafts.encoded(independent)).hexdigest(),
        profile='correction-scope')
    for name, value in zip(drafts._formal_names('initial'), (independent, primary, decision)):
        write_new_json(arm/name, value)
    with pytest.raises(ValueError, match='submission_required'):
        campaign.validate_handoff(arm/'initial.json', decision,
            read(run/'plan.json')['preparation_plan'], directory=run)
    change(arm/'initial-host-required.json', lambda d: d.pop(drafts.MODE_FIELD))
    with pytest.raises(ValueError, match='required_mode_changed'):
        campaign.validate_handoff(arm/'initial.json', decision,
            read(run/'plan.json')['preparation_plan'], directory=run)


def test_legacy_writer_and_waiter_cannot_implicitly_finalize_new_mode(pending):
    run, arm, _, notes = pending
    propose(pending)
    with pytest.raises(ValueError, match='explicit_draft_submission_required'):
        writer.write_decision(run, 'claim-scope:1', 'initial', notes, profile='correction-scope')
    with pytest.raises(ValueError, match='explicit_draft_submission_required'):
        writer.wait_and_write_decision(run, 'claim-scope:1', 'initial', notes,
            profile='correction-scope', max_wait_seconds=900)
    assert not (arm/'primary-notes-initial.json').exists()
    assert not (arm/'decision-initial.json').exists()


def test_v2_without_host_event_fails_closed_before_submission(pending):
    run, arm, independent, _ = pending
    saved = read(run/'plan.json')
    plan = saved['preparation_plan']
    plan[drafts.MODE_FIELD] = drafts.MODE_V2
    plan.update(
        root_thread_id='root-thread-1',
        review_event_provider='codex-collaboration-host-v1',
        review_principals={
            'primary': {'principal_id': 'root-principal'},
            'independent': {'principal_id': 'child-principal'},
        },
    )
    saved['plan_sha256'] = canonical_sha(plan)
    (run/'plan.json').write_text(json.dumps(saved), encoding='utf-8')
    change(arm/'initial-host-required.json', lambda value: value.update(
        host_review_submission_mode=drafts.MODE_V2))
    with pytest.raises(ValueError, match='independent_event_missing'):
        propose(pending)
    assert not (arm/'review-drafts').exists()
    assert not (arm/'decision-initial.json').exists()


@pytest.mark.parametrize('include_transport', [False, True])
def test_v2_builds_root_attestation_for_actual_issued_request(pending, include_transport):
    run, arm, independent, notes = pending
    saved = read(run/'plan.json')
    plan = saved['preparation_plan']
    plan[drafts.MODE_FIELD] = drafts.MODE_V2
    plan.update(
        root_thread_id='root-thread-1',
        review_event_provider='codex-collaboration-host-v1',
        review_principals={
            'primary': {'principal_id': 'root-principal'},
            'independent': {'principal_id': 'child-principal'},
        },
    )
    saved['plan_sha256'] = canonical_sha(plan)
    (run/'plan.json').write_text(json.dumps(saved), encoding='utf-8')
    change(arm/'initial-host-required.json', lambda value: value.update(
        host_review_submission_mode=drafts.MODE_V2))
    if not include_transport:
        with pytest.raises(ValueError, match='binding_hash_invalid'):
            writer.build_formal_decision(run, 'claim-scope:1', 'initial', notes, independent,
                independent_sha256=hashlib.sha256(drafts.encoded(independent)).hexdigest(),
                profile='correction-scope')
        return
    bound = drafts.binding(run, 'claim-scope:1', 'initial', profile='correction-scope')
    independent = drafts._review(independent, bound, True)
    primary, _ = writer.build_formal_decision(
        run, 'claim-scope:1', 'initial', notes, independent,
        independent_sha256=hashlib.sha256(drafts.encoded(independent)).hexdigest(),
        profile='correction-scope')
    from scripts.review_independence_contract import validate_primary_attestation
    validate_primary_attestation(primary, plan=plan, bound=bound)


def test_final_submission_validation_cannot_extend_original_clock(pending, monkeypatch):
    _, arm, _, _ = pending
    (arm/'initial-host-required.json').unlink()
    now = [0.0]
    validated = drafts.validate_submission
    def late(path, **options):
        validated(path, **options)
        now[0] = 1.0
    def publish(seconds):
        now[0] += seconds
        submit(pending, propose(pending))
    monkeypatch.setattr(drafts, 'validate_submission', late)
    with pytest.raises(ValueError, match='host_deadline'):
        observer.adjudicate_file(arm/'initial.json', 1, clock=lambda: now[0], sleep=publish)
    assert now[0] == 1.0


def test_cli_child_process_creates_draft_then_explicit_submission(pending, tmp_path):
    run, arm, independent, notes = pending
    independent_path, primary_path = tmp_path/'independent-notes.json', tmp_path/'primary-notes.json'
    independent_path.write_text(json.dumps(independent), encoding='utf-8')
    primary_path.write_text(json.dumps(notes), encoding='utf-8')
    command = [sys.executable, '-m', 'scripts.write_role_stage_decision',
        '--run-directory', str(run), '--profile', 'correction-scope',
        '--key', 'claim-scope:1', '--stage', 'initial']
    result = subprocess.run(command + ['--notes', str(independent_path), '--draft-independent',
        '--confirmed', '--reason', 'Explicit subprocess source review.'],
        cwd=campaign.ROOT, capture_output=True, text=True, check=True, timeout=30)
    sha = json.loads(result.stdout)['draft_sha256']
    assert not (arm/'decision-initial.json').exists()
    result = subprocess.run(command + ['--notes', str(primary_path), '--independent-draft-sha', sha],
        cwd=campaign.ROOT, capture_output=True, text=True, check=True, timeout=30)
    assert json.loads(result.stdout)['accepted']
    drafts.validate_submission(arm/'initial.json')


def test_real_continuous_executor_keeps_earlier_stage_binding_after_three_calls(make_run, tmp_path):
    run, sealed = make_run(('claim-scope:4',), profile='correction-scope', host_drafts=True)
    for stage in drafts.STAGES:
        drafts.validate_submission(run/'claim-scope-4'/(stage+'.json'))
    _, _, _, accepted, keys, _ = audit.inspect_runs([run], evidence_root=tmp_path,
        closed_exports=[sealed], profile='correction-scope')
    assert keys == {'claim-scope:4'} and len(accepted) == 1
    assert read(run/'result.json')['cases'][0]['accounting']['reserved_calls'] == 3


def test_changed_editor_output_stops_before_actual_final_call(make_run):
    def change_revision(path):
        if path.stem == 'revision':
            value = read(path)
            value['report'] += '\n\nThis passage was not generated by the editor.'
            value['report_sha256'] = digest(value['report'])
            path.write_text(json.dumps(value), encoding='utf-8')
    run, result = make_run(('claim-scope:4',), profile='correction-scope',
        host_drafts=True, inspect_fault=change_revision)
    arm = run/'claim-scope-4'
    assert result['error_code'] == 'host_review_actual_stage_changed'
    assert result['cases'][0]['accounting']['reserved_calls'] == 2
    assert not (arm/'review-drafts/revision').exists()
    assert not (arm/'decision-revision.json').exists()
    assert not (arm/'final.json').exists()


@pytest.mark.parametrize('field,value', [
    ('target_and_correction_valid', None), ('target_and_correction_valid', False),
    ('target_and_correction_valid', 1), ('accepted', 1),
    ('defects', [dict(kind='wrong_correction', detail='Contradictory acceptance.')]),
    ('source_file_sha256', '0'*64)])
@pytest.mark.parametrize('pending_edited', ['initial'], indirect=True)
def test_negative_initial_invalid_confirmation_never_becomes_confirmed_draft(pending_edited, field, value):
    run, arm, stage, review, _ = pending_edited
    if stage != 'initial':
        return
    review[field] = value
    if value is None:
        review.pop(field)
    with pytest.raises(ValueError):
        drafts.write_independent_draft(run, 'claim-scope:4', stage, review,
            reason='Explicit source review.', confirmed=True)
    assert not (arm/'review-drafts').exists()
    assert not any((arm/n).exists() for n in drafts._formal_names(stage))


@pytest.mark.parametrize('value', [None, False, 1])
@pytest.mark.parametrize('pending_edited', ['initial'], indirect=True)
def test_primary_negative_requires_explicit_true_before_submission(pending_edited, value):
    run, arm, stage, review, notes = pending_edited
    if stage != 'initial':
        return
    sha = drafts.write_independent_draft(run, 'claim-scope:4', stage, review,
        reason='Explicit source review.', confirmed=True)['draft_sha256']
    notes['target_and_correction_valid'] = value
    if value is None:
        notes.pop('target_and_correction_valid')
    with pytest.raises(ValueError, match='correction_confirmation_required'):
        drafts.finalize_stage_review(run, 'claim-scope:4', stage, notes,
            independent_draft_sha256=sha)
    assert len(list((arm/'review-drafts'/stage).iterdir())) == 1
    assert not any((arm/n).exists() for n in drafts._formal_names(stage))


@pytest.mark.parametrize('field,value', [('facts_and_sources_correct', False),
    ('correct_content_preserved', False), ('identity_and_goal_preserved', False),
    ('true_errors_fixed', False), ('report_sha256', '0'*64)])
def test_accepted_report_must_be_complete_before_confirmed_draft(pending, field, value):
    _, arm, review, _ = pending
    review['final_report'][field] = value
    with pytest.raises(ValueError, match='report_(not_accepted|binding)'):
        propose(pending)
    assert not (arm/'review-drafts').exists()


@pytest.mark.parametrize('pending_edited', ['initial'], indirect=True)
def test_old_incomplete_confirmed_draft_cannot_be_finalized(pending_edited):
    run, arm, stage, review, notes = pending_edited
    if stage != 'initial':
        return
    review.pop('target_and_correction_valid')
    drafts.write_independent_draft(run, 'claim-scope:4', stage, review,
        reason='Incomplete working opinion.', confirmed=False)
    path = arm/'review-drafts'/stage/'000001.json'
    change(path, lambda d: d.update(confirmed=True))  # Simulate old writer's output.
    with pytest.raises(ValueError, match='correction_confirmation_required'):
        drafts.finalize_stage_review(run, 'claim-scope:4', stage, notes,
            independent_draft_sha256=audit._sha(path))
    assert len(list(path.parent.iterdir())) == 1
    assert not any((arm/n).exists() for n in drafts._formal_names(stage))


@pytest.mark.parametrize('pending_edited', ['initial'], indirect=True)
def test_legacy_writer_rejects_missing_independent_confirmation_before_writing(pending_edited):
    run, arm, stage, review, notes = pending_edited
    if stage != 'initial':
        return
    saved = read(run/'plan.json')
    saved['preparation_plan'].pop(drafts.MODE_FIELD)
    saved['plan_sha256'] = canonical_sha(saved['preparation_plan'])
    (run/'plan.json').write_text(json.dumps(saved), encoding='utf-8')
    review.pop('target_and_correction_valid')
    write_new_json(arm/'independent-initial-review.json', review)
    with pytest.raises(ValueError, match='correction_confirmation_required'):
        writer.write_decision(run, 'claim-scope:4', stage, notes, profile='correction-scope')
    assert not (arm/'primary-initial-review.json').exists()
    assert not (arm/'decision-initial.json').exists()


@pytest.mark.parametrize('pending_edited', ['initial', 'revision', 'final'], indirect=True)
def test_negative_opinion_can_still_be_explicitly_submitted(pending_edited):
    run, arm, stage, review, notes = pending_edited
    review = rejected(review)
    notes.update(accepted=False, defects=review['defects'], target_and_correction_valid=False)
    sha = drafts.write_independent_draft(run, 'claim-scope:4', stage, review,
        reason='Explicit rejection.', confirmed=True)['draft_sha256']
    result = drafts.finalize_stage_review(run, 'claim-scope:4', stage, notes,
        independent_draft_sha256=sha)
    assert result['accepted'] is False
    drafts.validate_submission(arm/(stage+'.json'))


@pytest.mark.parametrize('field', ['request_sha256', 'provider_response_sha256', 'final_input_sha256'])
def test_legacy_raw_binding_is_checked_before_any_primary_write(pending, field):
    run, arm, review, notes = pending
    saved = read(run/'plan.json')
    saved['preparation_plan'].pop(drafts.MODE_FIELD)
    saved['plan_sha256'] = canonical_sha(saved['preparation_plan'])
    (run/'plan.json').write_text(json.dumps(saved), encoding='utf-8')
    review[field] = '0'*64
    write_new_json(arm/'independent-initial-review.json', review)
    with pytest.raises(ValueError, match='review_binding'):
        writer.write_decision(run, 'claim-scope:1', 'initial', notes, profile='correction-scope')
    assert not (arm/'primary-initial-review.json').exists()
    assert not (arm/'decision-initial.json').exists()


def test_positive_control_does_not_require_error_correction_confirmation(pending):
    _, arm, review, notes = pending
    review.pop('target_and_correction_valid')
    notes.pop('target_and_correction_valid')
    assert submit(pending, propose(pending))['accepted']
    drafts.validate_submission(arm/'initial.json')


@pytest.mark.parametrize('defect', ['report_check', 'contradictory_defects'])
def test_legacy_acceptance_contract_fails_before_publication(pending, defect):
    run, arm, review, notes = pending
    saved = read(run/'plan.json')
    saved['preparation_plan'].pop(drafts.MODE_FIELD)
    saved['plan_sha256'] = canonical_sha(saved['preparation_plan'])
    (run/'plan.json').write_text(json.dumps(saved), encoding='utf-8')
    if defect == 'report_check':
        review['final_report']['true_errors_fixed'] = False
    else:
        review['defects'] = [dict(kind='wrong_final_report', detail='Conflicts with acceptance.')]
    write_new_json(arm/'independent-initial-review.json', review)
    with pytest.raises(ValueError):
        writer.write_decision(run, 'claim-scope:1', 'initial', notes, profile='correction-scope')
    assert not (arm/'primary-initial-review.json').exists()
    assert not (arm/'decision-initial.json').exists()
