"""Bound real-public evidence and counterexamples; zero model IO."""
from copy import deepcopy
from dataclasses import replace

import pytest
from pydantic import ValidationError

from app.evaluation.role_task_outcome import assess_task_outcome, prepare_observation, may_continue_initial
from scripts.audit_role_task_outcome import audit, historical_cases, historical_assessment


@pytest.fixture(scope='module')
def cases():
    return historical_cases()


def test_real_tail_success_preserves_failed_reviewer_and_closed_admission():
    result = audit()
    correct, tail = result['observations']
    assert correct['reviewer_quality'] and correct['task_outcome']
    assert not tail['reviewer_quality'] and tail['task_outcome']
    assert tail['assessment']['stages'][0]['defects'][0]['kind'] == 'unsupported_explanation'
    assert len(result['original15_keys']) == len(set(result['original15_keys'])) == 15
    assert result['provider_requests'] == 0
    for observation in (correct, tail):
        assert not any(observation[key] for key in ('review_controls_qualified', 'actual_product_task_qualified',
            'production_admitted', 'execution_enabled', 'fresh_execution_verified',
            'continuous_task_budget_verified', 'original15_coverage_complete'))


@pytest.mark.parametrize('kind', ['missed_error', 'false_positive', 'wrong_correction',
    'unsupported_source', 'internal_contradiction'])
def test_final_success_cannot_erase_different_initial_defects(cases, kind):
    key = 'claim-scope:4'
    host = historical_assessment(key, cases[key])
    host['stages'][0]['defects'] = [dict(kind=kind, detail='Counterfactual host finding; final text happened to be correct.')]
    result = assess_task_outcome(key, cases[key], host)
    assert not result['reviewer_quality'] and result['task_outcome']
    assert result['assessment']['stages'][0]['defects'][0]['kind'] == kind
    assert not result['review_controls_qualified']


@pytest.mark.parametrize('stage,kind', [('revision', 'wrong_final_report'),
    ('revision', 'correct_content_lost'), ('revision', 'identity_or_goal_changed'),
    ('final', 'missed_error'), ('final', 'unsupported_explanation')])
def test_propagation_or_bad_final_review_blocks_outcome(cases, stage, kind):
    key = 'claim-scope:4'
    host = historical_assessment(key, cases[key])
    row = next(s for s in host['stages'] if s['stage'] == stage)
    row.update(accepted=False, defects=[dict(kind=kind, detail='Bound full-source review rejects this stage.')])
    assert not assess_task_outcome(key, cases[key], host)['task_outcome']


@pytest.mark.parametrize('field', ['facts_and_sources_correct', 'correct_content_preserved',
    'identity_and_goal_preserved', 'true_errors_fixed'])
def test_final_score_cannot_hide_report_failure(cases, field):
    key = 'claim-scope:4'
    host = historical_assessment(key, cases[key])
    host['final_report'][field] = False
    assert not assess_task_outcome(key, cases[key], host)['task_outcome']


@pytest.mark.parametrize('mutation', ['initial_pass', 'wrong_final_input', 'missing_edit', 'extra_call', 'correct_revised'])
def test_actual_replay_rejects_semantic_and_control_path_counterexamples(cases, mutation):
    key = 'claim-scope:4'
    calls = deepcopy(cases[key])
    if mutation == 'initial_pass':
        calls[0]['response'] = cases['claim-scope:1'][0]['response']
    elif mutation == 'wrong_final_input':
        calls[-1]['request'] = calls[0]['request']
    elif mutation == 'missing_edit':
        calls.pop(1)
    elif mutation == 'extra_call':
        calls.append(calls[-1])
    else:
        key = 'claim-scope:1'
        calls = deepcopy(cases[key])
        calls[0]['response'] = cases['claim-scope:4'][0]['response']
    with pytest.raises(ValueError):
        prepare_observation(key, calls)


@pytest.mark.parametrize('mutation', ['source', 'candidate', 'replay', 'stage', 'missing', 'order', 'report', 'blank', 'contradiction'])
def test_host_cannot_rebind_omit_or_silence_checks(cases, mutation):
    key = 'claim-scope:4'
    host = historical_assessment(key, cases[key])
    field = {'source': 'input_sha256', 'candidate': 'candidate_sha256', 'replay': 'replay_sha256'}
    if mutation in field:
        host[field[mutation]] = '0' * 64
    elif mutation == 'stage':
        host['stages'][0]['stage_sha256'] = '0' * 64
    elif mutation == 'missing':
        host['stages'].pop(0)
    elif mutation == 'order':
        host['stages'].reverse()
    elif mutation == 'report':
        host['final_report']['report_sha256'] = '0' * 64
    elif mutation == 'blank':
        host['stages'][0]['source_review'] = ' '
    else:
        host['stages'][0]['accepted'] = True
    with pytest.raises((ValueError, ValidationError)):
        assess_task_outcome(key, cases[key], host)


def test_unknown_usage_and_excessive_replay_budget_are_not_success(cases):
    key = 'claim-scope:4'
    calls = deepcopy(cases[key])
    calls[-1]['response'] = None
    with pytest.raises(ValueError, match='incomplete_calls'):
        prepare_observation(key, calls)
    calls = deepcopy(cases[key])
    calls[0]['response'] = replace(calls[0]['response'], usage=replace(calls[0]['response'].usage, input_tokens=401921))
    with pytest.raises(ValueError, match='replay_token_limit'):
        prepare_observation(key, calls)


def test_changed_supplied_usage_cannot_reuse_host_binding(cases):
    key = 'claim-scope:4'
    host = historical_assessment(key, cases[key])
    calls = deepcopy(cases[key])
    calls[0]['response'] = replace(calls[0]['response'], usage=replace(calls[0]['response'].usage, input_tokens=1, output_tokens=1))
    with pytest.raises(ValueError, match='assessment_binding_mismatch'):
        assess_task_outcome(key,calls,host)


@pytest.mark.parametrize('expected,confirmed,kind,allowed', [
    ('reject', True, 'unsupported_explanation', True),
    ('accept', True, 'unsupported_explanation', False),
    ('reject', False, 'unsupported_explanation', False),
    ('reject', True, 'wrong_correction', False),
    ('reject', True, 'false_positive', False),
    ('reject', True, 'missed_error', False),
    ('reject', True, 'unsupported_source', False),
])
def test_diagnostic_continuation_is_limited_to_safe_target_and_incidental_explanation(cases, expected, confirmed, kind, allowed):
    row = historical_assessment('claim-scope:4', cases['claim-scope:4'])['stages'][0]
    row['defects'][0]['kind'] = kind
    assert may_continue_initial(row, expected_initial=expected, target_and_correction_valid=confirmed) is allowed


def test_mixed_defects_cannot_use_incidental_explanation_allowance(cases):
    row = historical_assessment('claim-scope:4', cases['claim-scope:4'])['stages'][0]
    row['defects'].append(dict(kind='wrong_correction', detail='Incorrect requested edit.'))
    assert not may_continue_initial(row, expected_initial='reject', target_and_correction_valid=True)
