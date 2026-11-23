"""Add a current authorization window while retaining original15 evidence identity.

Install only in the external controller. This never changes an old grant, case
binding, session, budget, source tree, request, receipt or review. A continuation
is an explicit, separately pinned human authorization for the original envelope.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

VERSION = 'sol-original15-additive-authorization-v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class AdditiveAuthorization:
    def __init__(self, launch, control, config):
        self.launch = launch
        self.control = Path(control).resolve()
        self.original_sha = config['authorization_sha256']
        self.original_validator = getattr(launch.validate_grant,
            'original_validator', launch.validate_grant)
        self.selection = config.get('authorization_continuation')

    def validate(self, value, plan, pin, *, now=None):
        now = now or datetime.now(timezone.utc)
        original_path = self.control / 'authorization.json'
        if sha(original_path) != self.original_sha or json.loads(original_path.read_bytes()) != value:
            raise ValueError('original15_original_authorization_required')
        if not self.selection:
            return self.original_validator(value, plan, pin, now=now)
        selection = self.selection
        if set(selection) != {'file', 'sha256', 'module_sha256'}:
            raise ValueError('original15_continuation_selection_invalid')
        name = selection['file']
        if (not isinstance(name, str) or not name.startswith('authorization-continuation-')
                or Path(name).name != name or not name.endswith('.json')):
            raise ValueError('original15_continuation_path_invalid')
        path = self.control / name
        if (path.resolve() != path or path.is_symlink() or path.stat().st_nlink != 1
                or sha(path) != selection['sha256']
                or sha(__file__) != selection['module_sha256']):
            raise ValueError('original15_continuation_controls_changed')
        # Check the original grant as a historical record, using its issue time.
        # Its old expiry remains expired; only the separate grant below can
        # authorize the actual current time.
        historical_issue = datetime.fromisoformat(value['issued_at'])
        self.original_validator(value, plan, pin, now=historical_issue)
        continuation = json.loads(path.read_bytes())
        fixed = dict(version=VERSION, original_authorization_sha256=self.original_sha,
            original_plan_sha256=pin, original_operator=str(Path(plan['operator'])),
            original_envelope=self.launch.grant_binding(plan, pin),
            scope='remaining_original_batch', reset_accounting=False,
            rewrite_original_authorization=False, automatic_retries=False,
            qualified=False, publication_allowed=False)
        if (set(continuation) != set(fixed) | {'issued_at', 'expires_at', 'user_authorization_evidence'}
                or any(continuation.get(k) != v for k, v in fixed.items())):
            raise ValueError('original15_continuation_scope_changed')
        issued = datetime.fromisoformat(continuation['issued_at'])
        expires = datetime.fromisoformat(continuation['expires_at'])
        evidence = continuation['user_authorization_evidence']
        if (issued.utcoffset() is None or expires.utcoffset() is None or now.utcoffset() is None
                or not issued <= now < expires or not timedelta(0) < expires-issued <= timedelta(days=1)
                or issued < datetime.fromisoformat(value['expires_at'])
                or not isinstance(evidence, str) or not evidence.strip()):
            raise ValueError('original15_specific_unexpired_continuation_required')

    def state(self, value, plan, pin):
        try:
            self.validate(value, plan, pin)
        except ValueError as error:
            return dict(active=False, code=str(error))
        return dict(active=True, kind='additive_continuation' if self.selection else 'original')


def install(launch, control, config):
    validator = AdditiveAuthorization(launch, control, config)
    def validate(value, plan, pin, *, now=None):
        return validator.validate(value, plan, pin, now=now)
    validate.original_validator = validator.original_validator
    launch.validate_grant = validate
    return validator
