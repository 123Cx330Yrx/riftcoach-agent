"""Network follow-up must not change semantics or inherit closed authorization."""
from datetime import datetime, timedelta, timezone

import pytest

from scripts import document_full_report_diagnostic as prior
from scripts import document_full_report_network_followup as followup


def test_new_identity_keeps_all_requests_and_material_exact():
    old, original = prior.prepare(root_thread_id='root', independent_thread_id='child')
    new, rows = followup.prepare(root_thread_id='root', independent_thread_id='child')
    assert old['run_id'] != new['run_id']
    assert old['kind'] != new['kind']
    assert new['budget'] == old['budget']
    assert new['sequence'] == old['sequence']
    for left, right in zip(original, rows, strict=True):
        assert left[:2] == right[:2]
        assert prior.identity.request_bytes(left[2]) == prior.identity.request_bytes(right[2])
    assert new['network_followup_evidence'] == followup.EVIDENCE
    assert new['prior_run_reopened'] is False
    assert new['prior_unknown_usage_calls'] == 1
    assert new['execution_authorized'] is False
    assert new['new_qualification'] == 0
    assert followup.SOURCE in new['source_sha256']


def test_old_authorization_rejected_even_if_new_digest_is_supplied():
    plan, _ = followup.prepare(root_thread_id='root', independent_thread_id='child')
    now = datetime.now(timezone.utc)
    value = dict(version=prior.base.AUTH_VERSION, authorized=True,
        user_instruction='synthetic offline evidence',
        head='f' * 40, ci_run='test-ci', budget=plan['budget'],
        plan_sha256=followup.base.sha(followup.base.options.canonical(plan)),
        issued_at=now.isoformat(), expires_at=(now + timedelta(hours=24)).isoformat())
    with pytest.raises(ValueError, match='authorization'):
        followup.base.check_authorization(value, plan, 'f' * 40, 'test-ci', now=now)


def test_changed_network_evidence_rejected_before_preparation(monkeypatch):
    path = next(iter(followup.EVIDENCE))
    monkeypatch.setitem(followup.EVIDENCE, path, '0' * 64)
    with pytest.raises(ValueError, match='network_followup_evidence_changed'):
        followup.prepare(root_thread_id='root', independent_thread_id='child')


def test_package_reconstruction_uses_followup_identity(tmp_path):
    package = followup.Package(tmp_path / 'new-package')
    value = package.write(root_thread_id='root', independent_thread_id='child')
    assert package.verify()['verified']
    assert value['preparation_plan']['kind'] == followup.VERSION
    # The frozen original entrypoint cannot accidentally launch the new package.
    with pytest.raises(ValueError, match='sampling_package_plan_changed'):
        prior.Package(package.directory).verify()
