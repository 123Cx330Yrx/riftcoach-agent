"""No paid retries or budget resets are hidden in interruption continuation."""
from copy import deepcopy
from types import SimpleNamespace as NS

import pytest

from scripts import run_role_unexecuted_qualification as runner


def test_continuation_only_covers_untouched_inputs_and_charges_parent():
    plan,requests=runner.prepare()
    assert list(requests)==['claim-scope:2','claim-scope:5','claim-scope:6','claim-scope:7',
        'observed:1','observed:2','observed:3','observed:4','observed:5']
    assert set(plan['excluded_started_keys'])=={'claim-scope:3','scope:4','scope:3'}
    assert not set(requests)&set(plan['excluded_started_keys'])
    assert plan['charged_prior_budget']==dict(max_calls=7,max_tokens=102455,max_seconds=2700)
    assert plan['batch_budget']['max_calls']==19
    assert plan['batch_budget']['max_seconds']==5700
    assert all(plan['batch_budget'][k]+plan['charged_prior_budget'][k]<=plan['original_batch_budget'][k]
        for k in ('max_calls','max_tokens','max_seconds'))
    assert plan['host_handoff']=='bounded_file_decisions'
    assert not plan['allow_reassessment'] and plan['sdk_retries']==0
    assert all(b'expected_initial' not in raw for raw in requests.values())


@pytest.mark.parametrize('defect',['unknown_usage','call_limit','tokens','started_key'])
def test_parent_constraints_cannot_be_bypassed(monkeypatch,defect):
    evidence=deepcopy(runner.interruption())
    if defect=='unknown_usage':
        evidence['unknown_usage_calls']=1
    elif defect=='call_limit':
        evidence['provider_requests']=10
    elif defect=='tokens':
        evidence['input_tokens']=2_709_504
    else:
        evidence['unexecuted_keys'].append('scope:3')
    monkeypatch.setattr(runner,'interruption',lambda:evidence)
    with pytest.raises(ValueError):
        runner.prepare()


def test_closed_or_bad_preparation_fails_before_keys_or_ci(monkeypatch,tmp_path):
    monkeypatch.setattr(runner,'load_role_settings',lambda *_:pytest.fail('credentials accessed'))
    monkeypatch.setattr(runner,'verify_public_ci',lambda *_:pytest.fail('CI accessed'))
    monkeypatch.setattr(runner,'RUN_DIRECTORY',tmp_path/'new')
    monkeypatch.setattr(runner,'CLOSED_RESULT',tmp_path/'closed')
    with pytest.raises(ValueError,match='preparation_required'):
        runner.run(NS(execute=True,env_file=tmp_path/'unused',ci_run='x',plan_sha='bad'))
    (tmp_path/'new').mkdir()
    monkeypatch.setattr(runner,'prepare',lambda:pytest.fail('closed batch prepared'))
    with pytest.raises(ValueError,match='batch_closed_or_exists'):
        runner.run(NS(execute=True))


def test_original_seal_uses_raw_bytes_not_public_projection(monkeypatch,tmp_path):
    evidence=deepcopy(runner.interruption())
    raw=tmp_path/'raw'
    raw.mkdir()
    (raw/'changed.json').write_text('{}')
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    evidence['run_directory']='raw'
    evidence['original_file_sha256']={'changed.json':'0'*64}
    monkeypatch.setattr(runner,'interruption',lambda:evidence)
    with pytest.raises(ValueError,match='parent_raw_changed'):
        runner.verify_original_seal()
