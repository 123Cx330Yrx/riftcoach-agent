"""SDK wrappers must not turn a known read timeout into a connect timeout."""
import httpx
import pytest
from openai import APITimeoutError, APIConnectionError

from scripts.reviewer_responses_transport import classify_exception


@pytest.mark.parametrize('cause,expected', [
    (httpx.ReadTimeout('PRIVATE'), 'read_timeout'),
    (httpx.ConnectTimeout('PRIVATE'), 'connect_timeout'),
    (httpx.PoolTimeout('PRIVATE'), 'pool_timeout'),
    (httpx.ProxyError('PRIVATE'), 'proxy_error'),
    (httpx.ReadError('PRIVATE'), 'read_error'),
])
@pytest.mark.parametrize('wrapper', [APITimeoutError, APIConnectionError])
def test_specific_io_cause_wins_over_generic_sdk_wrapper(cause, expected, wrapper):
    error = wrapper(request=httpx.Request('POST', 'https://example.invalid'))
    error.__cause__ = cause
    assert classify_exception(error) == expected


def test_unexplained_sdk_timeout_keeps_existing_fallback():
    error = APITimeoutError(request=httpx.Request('POST', 'https://example.invalid'))
    assert classify_exception(error) == 'connect_timeout'
