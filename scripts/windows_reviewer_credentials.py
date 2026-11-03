"""Local Windows Credential Manager adapter; never sends a provider request.

Only the existing continuation credential callback is replaced. Authorization,
transport, source review and session replay remain the launcher's responsibility.
"""
import argparse
import ctypes
from ctypes import wintypes
import getpass
import json
import sys
import warnings

BASE_URL = 'https://yujianwudi.top/v1'
GROUP = 'GPT-企业专线'
TARGET = 'RiftCoach/Tianjige/yujianwudi.top-v1/GPT-enterprise-0.25'
CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2  # Same Windows user, survives logoff on this machine.
ERROR_NOT_FOUND = 1168


class CredentialStoreError(RuntimeError):
    """Only fixed public codes, never provider keys or arbitrary native text."""


class _Attribute(ctypes.Structure):
    _fields_ = [('Keyword', wintypes.LPWSTR), ('Flags', wintypes.DWORD),
                ('ValueSize', wintypes.DWORD), ('Value', ctypes.POINTER(ctypes.c_ubyte))]


class _Credential(ctypes.Structure):
    _fields_ = [('Flags', wintypes.DWORD), ('Type', wintypes.DWORD),
                ('TargetName', wintypes.LPWSTR), ('Comment', wintypes.LPWSTR),
                ('LastWritten', wintypes.FILETIME), ('CredentialBlobSize', wintypes.DWORD),
                ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)), ('Persist', wintypes.DWORD),
                ('AttributeCount', wintypes.DWORD), ('Attributes', ctypes.POINTER(_Attribute)),
                ('TargetAlias', wintypes.LPWSTR), ('UserName', wintypes.LPWSTR)]


def _api():
    if sys.platform != 'win32':
        raise CredentialStoreError('windows_credential_manager_required')
    api = ctypes.WinDLL('Advapi32.dll', use_last_error=True)
    api.CredWriteW.argtypes = (ctypes.POINTER(_Credential), wintypes.DWORD)
    api.CredWriteW.restype = wintypes.BOOL
    api.CredReadW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                             ctypes.POINTER(ctypes.POINTER(_Credential)))
    api.CredReadW.restype = wintypes.BOOL
    api.CredDeleteW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD)
    api.CredDeleteW.restype = wintypes.BOOL
    api.CredFree.argtypes = (ctypes.c_void_p,)
    api.CredFree.restype = None
    return api


def _failure(action):
    code = ctypes.get_last_error()
    if code == ERROR_NOT_FOUND:
        raise CredentialStoreError('stored_reviewer_key_missing')
    raise CredentialStoreError(f'windows_credential_{action}_failed_{code}')


def store_key(key, *, target=TARGET):
    if not isinstance(key, str) or not key.strip() or key != key.strip():
        raise CredentialStoreError('reviewer_key_empty_or_surrounding_whitespace')
    raw = key.encode('utf-8')
    if len(raw) > 2560:
        raise CredentialStoreError('reviewer_key_too_long')
    api = _api()
    buffer = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
    entry = _Credential(Type=CRED_TYPE_GENERIC, TargetName=target,
        Comment='RiftCoach Tianjige reviewer; user-selected enterprise group',
        CredentialBlobSize=len(raw), CredentialBlob=buffer,
        Persist=CRED_PERSIST_LOCAL_MACHINE, UserName='RiftCoach/Tianjige')
    try:
        if not api.CredWriteW(ctypes.byref(entry), 0):
            _failure('write')
    finally:
        ctypes.memset(buffer, 0, len(raw))


def read_key(*, target=TARGET):
    api = _api()
    pointer = ctypes.POINTER(_Credential)()
    if not api.CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)):
        _failure('read')
    try:
        entry = pointer.contents
        raw = ctypes.string_at(entry.CredentialBlob, entry.CredentialBlobSize)
        try:
            key = raw.decode('utf-8')
        except UnicodeDecodeError:
            raise CredentialStoreError('stored_reviewer_key_encoding') from None
        if not key.strip():
            raise CredentialStoreError('stored_reviewer_key_empty')
        return key
    finally:
        api.CredFree(pointer)


def remove_key(*, target=TARGET):
    api = _api()
    if not api.CredDeleteW(target, CRED_TYPE_GENERIC, 0):
        _failure('delete')


def install(base, *, group, base_url):
    """Install lazily: preparation and Host-only execution do not read the key."""
    if group != GROUP or base_url != BASE_URL:
        raise CredentialStoreError('stored_reviewer_profile_mismatch')

    def continuation_credentials(*, reviewer_group=GROUP):
        if reviewer_group != GROUP:
            raise CredentialStoreError('stored_reviewer_profile_mismatch')
        from app.providers.config import ZhipuSettings
        key = read_key()
        return ZhipuSettings(api_key='UNUSED_GENERATION_FORBIDDEN',
            base_url='https://open.bigmodel.cn/api/paas/v4', model='glm-5.3-flash'), key

    base.continuation_credentials = continuation_credentials


def main(argv=None):
    parser = argparse.ArgumentParser(description='Manage the local Tianjige reviewer credential.')
    parser.add_argument('action', choices=('store', 'status', 'remove'))
    args = parser.parse_args(argv)
    try:
        if args.action == 'store':
            if not sys.stdin.isatty():
                raise CredentialStoreError('hidden_interactive_key_input_required')
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                key = getpass.getpass('Tianjige GPT-enterprise API key (hidden, saved locally): ')
            try:
                store_key(key.strip())
                if read_key() != key.strip():
                    raise CredentialStoreError('credential_readback_mismatch')
            finally:
                key = None
        elif args.action == 'status':
            read_key()  # Print existence only; never the value or a key hash.
        else:
            remove_key()
        print(json.dumps(dict(ok=True, action=args.action,
            configured=args.action != 'remove', storage='windows-credential-manager',
            base_url=BASE_URL, group=GROUP, provider_requests=0), ensure_ascii=True))
        return 0
    except (CredentialStoreError, getpass.GetPassWarning, EOFError, KeyboardInterrupt) as error:
        code = str(error) if isinstance(error, CredentialStoreError) else 'credential_input_interrupted'
        print(json.dumps(dict(ok=False, code=code, provider_requests=0), ensure_ascii=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
