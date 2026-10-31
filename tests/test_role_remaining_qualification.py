"""Continuation covers only new inputs and cannot weaken stage acceptance."""
from copy import deepcopy
import json
from types import SimpleNamespace as NS

import pytest

from scripts import run_role_remaining_qualification as runner
from app.evaluation.role_qualification import prepare_qualification


def test_remaining_plan_preserves_identity_and_exact_unrun_inputs():
    plan, requests = runner.prepare()
    original, _ = prepare_qualification()
    expected = [r for r in original['cases'] if r['key'] not in runner.PRIOR_KEYS]
    assert plan['cases'] == expected
    sealed = json.loads(runner.INTERRUPTION.read_bytes())['public_json_contents']['plan.json']['preparation_plan']
    assert plan['identity'] == sealed['identity']
    assert len(requests) == 12
    assert len(set(plan['prior_keys']) | set(requests)) == 15
    assert not (set(plan['prior_keys']) & set(requests))
    assert plan['batch_budget']['max_calls'] == 28
    assert plan['batch_budget']['max_tokens'] == 2709504
    assert plan['batch_budget']['max_seconds'] == 8400
    assert all(b'expected_initial' not in v for v in requests.values())
    assert not plan['allow_reassessment']


@pytest.mark.parametrize('accepted,defects,base_allowed,expected',[
    (True,[],True,True), (False,[{'kind':'unsupported_explanation'}],True,False),
    (True,[],False,False), (True,[{'kind':'wrong_correction'}],True,False),
])
def test_continuation_never_uses_incidental_defect_exception(monkeypatch,accepted,defects,base_allowed,expected):
    monkeypatch.setattr(runner.Observer,'validate_stage',lambda *_, **kwargs:base_allowed)
    decision = dict(accepted=accepted,assessment=dict(stage='final',defects=defects))
    assert runner.StrictObserver.validate_stage({}, {'expected_initial':'reject'}, None, decision) is expected


def test_rejected_correction_intent_stops_before_editor(monkeypatch):
    monkeypatch.setattr(runner.Observer,'validate_stage',lambda *_, **kwargs:True)
    decision = dict(accepted=True,assessment=dict(stage='initial',defects=[]),target_and_correction_valid=False)
    assert not runner.StrictObserver.validate_stage({}, {'expected_initial':'reject'}, None, decision)


def test_closed_batch_stops_before_preparation_ci_or_credentials(monkeypatch,tmp_path):
    closed = tmp_path/'closed.json'
    closed.write_text('{}')
    monkeypatch.setattr(runner,'CLOSED_RESULT',closed)
    monkeypatch.setattr(runner,'prepare',lambda:pytest.fail('prepared closed batch'))
    monkeypatch.setattr(runner,'verify_public_ci',lambda *_:pytest.fail('CI called'))
    monkeypatch.setattr(runner,'load_role_settings',lambda *_:pytest.fail('credentials read'))
    with pytest.raises(ValueError,match='remaining_batch_closed_or_exists'):
        runner.run(NS(execute=True))


def test_prior_export_change_rejected(monkeypatch,tmp_path):
    changed = tmp_path/'changed.json'
    changed.write_bytes(runner.PRIOR_RESULT.read_bytes()+b'\n')
    monkeypatch.setattr(runner,'PRIOR_RESULT',changed)
    with pytest.raises(ValueError,match='remaining_prior_evidence_changed'):
        runner.prepare()


def test_different_model_identity_cannot_consume_prior_observations(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'INTERRUPTION', tmp_path/'not-closed')
    original,requests = prepare_qualification()
    changed = deepcopy(original)
    changed['identity']['manifest_sha256']='0'*64
    monkeypatch.setattr(runner,'prepare_qualification',lambda:(changed,requests))
    with pytest.raises(ValueError,match='remaining_candidate_identity_changed'):
        runner.prepare()


def test_interrupted_preview_keeps_frozen_plan_after_executor_repairs():
    plan,requests=runner.prepare()
    assert runner.canonical_sha(plan)=='4f9d9b77aec2f0bb583a2cba3686ffd403653c64b7863b6fb9f78a6b63ba0ce2'
    assert len(requests)==12
    assert runner.run(NS(execute=False,output=None))['historical_closed']
