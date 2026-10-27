"""Share one live native read within one gate validation, never across reviews.

The provenance validator and byte validator inspect the same current response.
All their existing checks still execute. Nothing is cached between validation
calls, and collaboration files are still read by the pinned original reader.
"""
from copy import deepcopy
from functools import wraps
import hashlib
import json
from pathlib import Path


READ_METHODS = frozenset(('thread/read', 'thread/turns/list'))
STATS = dict(validations=0, actual_reads=0, duplicate_reads=0)


class ValidationReadSnapshot:
    def __init__(self, client):
        self.client = client
        self.responses = {}

    def request(self, method, params):
        if method not in READ_METHODS:
            return self.client.request(method, params)
        key = (method, json.dumps(params, sort_keys=True, separators=(',', ':'), allow_nan=False))
        if key not in self.responses:
            # A failed read is never cached or converted into a previous success.
            value = self.client.request(method, params)
            STATS['actual_reads'] += 1
            self.responses[key] = deepcopy(value)
        else:
            STATS['duplicate_reads'] += 1
        return deepcopy(self.responses[key])

    def __getattr__(self, name):
        return getattr(self.client, name)


def wrap_validation(previous, verify_controls):
    @wraps(previous)
    def validate(self, handle, submission):
        verify_controls()
        source = self.event_source
        client = source.client
        if isinstance(client, ValidationReadSnapshot):
            raise ValueError('original15_native_snapshot_nested_validation')
        snapshot = ValidationReadSnapshot(client)
        source.client = snapshot
        STATS['validations'] += 1
        try:
            return previous(self, handle, submission)
        finally:
            source.client = client
            snapshot.responses.clear()
    return validate


def install(control, config):
    selected = config.get('native_validation_snapshot')
    if selected is None:
        return
    control = Path(control).resolve()
    module = control/'original15_native_snapshot.py'
    manifest = control/selected['file']

    def verify():
        if (manifest.parent != control
                or hashlib.sha256(module.read_bytes()).hexdigest() != selected['module_sha256']
                or hashlib.sha256(manifest.read_bytes()).hexdigest() != selected['sha256']):
            raise ValueError('original15_native_snapshot_controls_changed')
        value = json.loads(manifest.read_bytes())
        if (value.get('version') != 'original15-native-validation-snapshot-v1'
                or value.get('plan_sha256') != config['plan_sha256']
                or value.get('scope') != 'one_validation_call'
                or value.get('cross_validation_cache') is not False
                or value.get('existing_validators_unchanged') is not True
                or value.get('collaboration_file_reader_unchanged') is not True):
            raise ValueError('original15_native_snapshot_plan_binding')

    verify()
    from scripts import reviewer_profile_batch as batch
    previous = batch.ExactNativeGate._validate
    installed = getattr(previous, '_native_validation_snapshot', None)
    if installed is not None:
        if installed != selected:
            raise ValueError('original15_native_snapshot_install_changed')
        return
    validate = wrap_validation(previous, verify)
    validate._native_validation_snapshot = dict(selected)
    batch.ExactNativeGate._validate = validate
