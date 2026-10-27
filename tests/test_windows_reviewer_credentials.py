import sys
from types import SimpleNamespace
import uuid

import pytest

from scripts import windows_reviewer_credentials as credentials


def test_install_reads_only_when_original_send_boundary_requests_key(monkeypatch):
    reads = []
    monkeypatch.setattr(credentials, 'read_key', lambda: reads.append('read') or 'test-reviewer-secret')
    base = SimpleNamespace(continuation_credentials=lambda **kwargs: pytest.fail('old prompt used'))
    credentials.install(base, group=credentials.GROUP, base_url=credentials.BASE_URL)
    assert reads == []
    with pytest.raises(credentials.CredentialStoreError, match='profile_mismatch'):
        base.continuation_credentials(reviewer_group='GPT-pro')
    assert reads == []
    generator, key = base.continuation_credentials(reviewer_group=credentials.GROUP)
    assert reads == ['read'] and key == 'test-reviewer-secret'
    assert generator.api_key == 'UNUSED_GENERATION_FORBIDDEN'
    assert 'test-reviewer-secret' not in repr(generator)


def test_wrong_endpoint_cannot_install_or_read(monkeypatch):
    monkeypatch.setattr(credentials, 'read_key', lambda: pytest.fail('key read for wrong endpoint'))
    base = SimpleNamespace(continuation_credentials='original')
    with pytest.raises(credentials.CredentialStoreError, match='profile_mismatch'):
        credentials.install(base, group=credentials.GROUP, base_url='https://elsewhere.invalid/v1')
    assert base.continuation_credentials == 'original'


def test_missing_key_does_not_prompt_or_fall_back(monkeypatch):
    def missing():
        raise credentials.CredentialStoreError('stored_reviewer_key_missing')
    monkeypatch.setattr(credentials, 'read_key', missing)
    monkeypatch.setattr(credentials.getpass, 'getpass', lambda *a: pytest.fail('unexpected prompt'))
    base = SimpleNamespace()
    credentials.install(base, group=credentials.GROUP, base_url=credentials.BASE_URL)
    with pytest.raises(credentials.CredentialStoreError, match='stored_reviewer_key_missing'):
        base.continuation_credentials(reviewer_group=credentials.GROUP)


@pytest.mark.skipif(sys.platform != 'win32', reason='real Windows Credential Manager integration')
def test_real_native_store_read_replace_delete_and_missing():
    target = 'RiftCoach/test-only/' + str(uuid.uuid4())
    try:
        credentials.store_key('fake-value-one', target=target)
        assert credentials.read_key(target=target) == 'fake-value-one'
        credentials.store_key('fake-value-two', target=target)
        assert credentials.read_key(target=target) == 'fake-value-two'
    finally:
        credentials.remove_key(target=target)
    with pytest.raises(credentials.CredentialStoreError, match='stored_reviewer_key_missing'):
        credentials.read_key(target=target)


def test_cli_never_prints_the_key(monkeypatch, capsys):
    monkeypatch.setattr(credentials.sys, 'stdin', SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(credentials.getpass, 'getpass', lambda *a: 'fake-cli-secret')
    saved = []
    monkeypatch.setattr(credentials, 'store_key', saved.append)
    monkeypatch.setattr(credentials, 'read_key', lambda: saved[-1])
    assert credentials.main(['store']) == 0
    captured = capsys.readouterr()
    assert 'fake-cli-secret' not in captured.out + captured.err
    assert 'windows-credential-manager' in captured.out
