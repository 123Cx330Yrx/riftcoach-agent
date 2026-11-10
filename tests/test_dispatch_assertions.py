"""Regression for the Linux CI false positive and retained path enforcement."""
import pytest

from tests.dispatch_assertions import assert_dispatch_python


@pytest.mark.parametrize('executable,platform,command', [
    ('/opt/hostedtoolcache/Python/3.11.17/x64/bin/python', 'linux',
     '/opt/hostedtoolcache/Python/3.11.17/x64/bin/python -m scripts.example read'),
    ('/opt/Python runtime/bin/python', 'linux',
     "'/opt/Python runtime/bin/python' -m scripts.example read"),
    ('C:/Python runtime/python.exe', 'win32',
     "& 'C:/Python runtime/python.exe' -m scripts.example read"),
])
def test_absolute_interpreter_is_accepted(executable, platform, command):
    assert_dispatch_python(command, executable, platform, command_count=1)


@pytest.mark.parametrize('command', [
    'python -m scripts.example read',
    './python -m scripts.example read',
    '/wrong/bin/python -m scripts.example read',
    'prefix /opt/bin/python -m scripts.example read',
    'Verified Python executable: /opt/bin/python',
    '/opt/bin/python -m scripts.example read\npython -m scripts.example verify',
])
def test_missing_bare_relative_or_wrong_interpreter_is_rejected(command):
    with pytest.raises(AssertionError):
        assert_dispatch_python(command, '/opt/bin/python', 'linux', command_count=1)
