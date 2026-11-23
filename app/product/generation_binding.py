"""Private, server-selected execution identity captured with a new task."""
from hashlib import sha256
import json

from app.tasks.continuation import ContinuationError, PRODUCT_WORKER_PROFILES, contract_for_worker_profile


def capture(profile):
    if profile not in PRODUCT_WORKER_PROFILES:
        raise ValueError('generation_profile_unavailable')
    module = contract_for_worker_profile(profile)
    from app.skills.catalog import SkillCatalog
    skill = SkillCatalog.from_directory(module.ASSETS / 'skills').get('recent-form-review')
    components = [row.model_dump(mode='json') for row in module.component_fingerprints(skill)]
    return dict(schema_version=1, worker_profile=profile,
                execution_contract=module.CONTRACT.snapshot().model_dump(mode='json'),
                components_sha256=sha256(json.dumps(components, sort_keys=True, separators=(',', ':')).encode()).hexdigest())


def verify(pin, profile):
    if pin is None:
        from app.product.player_wording_worker import WORKER_PROFILE
        if profile == WORKER_PROFILE:
            raise ContinuationError('generation_binding_required')
        return
    if not isinstance(pin, dict) or pin.get('worker_profile') != profile:
        raise ContinuationError('generation_profile_mismatch')
    if pin != capture(profile):
        raise ContinuationError('generation_binding_changed')
