"""A quota interruption cannot refund charges or rerun started controls."""
import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from scripts import run_correction_scope_unexecuted as runner
from scripts import run_correction_scope_qualification as prior
from scripts.diagnose_role_context import canonical_sha
from app.evaluation.golden_review_experiment import compact, digest


@pytest.fixture
def same_checkout_parent(tmp_path, monkeypatch):
    """Represent a closed parent produced on this OS; retain real case inputs.

    The original seal belongs to Windows. Its raw manifest bytes are not the
    Linux checkout's bytes and must not be silently migrated by production code.
    These preparation tests use a synthetic seal; raw acceptance is tested
    separately by the full observation tests and verify_parent execution gate.
    """
    evidence = json.loads(prior.CLOSED_RESULT.read_bytes())
    current, _ = runner.qualification.prepare_qualification()
    saved = evidence['public_json_contents']['plan.json']
    plan = saved['preparation_plan']
    plan.update(identity=current['identity'], cases=current['cases'],
        original15_plan_sha256=digest(compact(current)))
    saved['plan_sha256'] = evidence['plan_sha256'] = canonical_sha(plan)
    path = tmp_path/'same-checkout-parent.json'
    path.write_text(json.dumps(evidence), encoding='utf-8')
    preparation = tmp_path/'preparation.json'
    preparation.write_text(json.dumps(plan), encoding='utf-8')
    monkeypatch.setattr(prior, 'CLOSED_RESULT', path)
    monkeypatch.setattr(prior, 'CLOSED_SHA', hashlib.sha256(path.read_bytes()).hexdigest())
    monkeypatch.setattr(prior, 'PREPARATION', preparation)
    return evidence


def test_only_thirteen_untouched_requests_fit_original_remaining_budget(same_checkout_parent):
    plan, requests = runner.prepare()
    original, all_requests = prior.prepare()
    assert plan['identity'] == original['identity']
    assert plan['cases'] == original['cases'][2:]
    assert requests == {r['key']: all_requests[r['key']] for r in plan['cases']}
    assert len(requests) == 13
    assert plan['charged_prior_budget'] == dict(max_calls=4, max_tokens=58913, max_seconds=1132.828)
    assert plan['batch_budget']['max_calls'] == 31
    assert plan['excluded_started_keys'] == ['claim-scope:1', 'claim-scope:4']
    for name in ('max_calls', 'max_tokens', 'max_seconds'):
        assert plan['charged_prior_budget'][name] + plan['batch_budget'][name] <= original['batch_budget'][name]
    assert not plan['review_controls_qualified'] and not plan['allow_reassessment']


@pytest.mark.parametrize('defect', ['seal', 'unknown_usage', 'boundary', 'identity', 'charges'])
def test_parent_changes_do_not_unlock_new_calls(tmp_path, monkeypatch, defect, same_checkout_parent):
    evidence = json.loads(prior.CLOSED_RESULT.read_bytes())
    if defect == 'unknown_usage':
        evidence['unknown_usage_calls'] = 1
    elif defect == 'boundary':
        evidence['completed_keys'].append('claim-scope:4')
    elif defect == 'identity':
        evidence['public_json_contents']['plan.json']['preparation_plan']['identity']['manifest_sha256'] = '0'*64
    elif defect == 'charges':
        evidence['provider_requests'] = 5
    path = tmp_path/'parent.json'
    path.write_text(json.dumps(evidence), encoding='utf-8')
    if defect == 'seal':
        path.write_bytes(path.read_bytes() + b' ')
    monkeypatch.setattr(prior, 'CLOSED_RESULT', path)
    if defect != 'seal':
        monkeypatch.setattr(prior, 'CLOSED_SHA', hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match='correction_scope_'):
        runner.prepare()


def test_closed_continuation_is_rejected_before_parent_or_ci(tmp_path, monkeypatch):
    path = tmp_path/'run'
    path.mkdir()
    monkeypatch.setattr(runner, 'RUN_DIRECTORY', path)
    monkeypatch.setattr(runner, 'prepare', lambda: pytest.fail('prepare accessed'))
    with pytest.raises(ValueError, match='closed_or_exists'):
        runner.run(NS(execute=True))


def test_raw_parent_is_audited_before_any_execution(monkeypatch):
    monkeypatch.setattr(runner, 'RUN_DIRECTORY', runner.ROOT/'tmp/never-created-unexecuted-test')
    monkeypatch.setattr(runner, 'prepare', lambda: ({}, {}))
    def reject():
        raise ValueError('sealed_file_hash')
    monkeypatch.setattr(runner, 'verify_parent', reject)
    monkeypatch.setattr(prior, 'execute_prepared', lambda *a, **k: pytest.fail('CI or execution reached'))
    with pytest.raises(ValueError, match='sealed_file_hash'):
        runner.run(NS(execute=True))
