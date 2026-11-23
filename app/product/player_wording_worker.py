"""Explicit Worker generation version; review wire contracts are reused exactly."""
import hashlib
import sys

from app.product import sol_chat_contract as parent
from app.product.player_wording_contract import generation_policy, VERSION as WORDING_VERSION

VERSION = parent.VERSION
WORKER_PROFILE = 'sol-dual-product-wording-v2'
ROOT = parent.ROOT
legacy = parent.legacy
ASSETS = ROOT / 'examples/runtime_profiles/sol_product_wording_worker_v2'
CONTEXT = parent.CONTEXT
RESPONSE_MODE = parent.RESPONSE_MODE
REVIEW_TRANSPORT = parent.REVIEW_TRANSPORT
REVIEW_THINKING_PROFILE = parent.REVIEW_THINKING_PROFILE
PROVIDER, MODEL, PROFILE = parent.PROVIDER, parent.MODEL, parent.PROFILE
REVIEW_PROVIDER, REVIEW_MODEL, REVIEW_PROFILE = parent.REVIEW_PROVIDER, parent.REVIEW_MODEL, parent.REVIEW_PROFILE
FRESH_REVIEW_RESERVATION = parent.FRESH_REVIEW_RESERVATION
make_request = parent.make_request
restore_context = parent.restore_context
validate_business = parent.validate_business
role_for_request = parent.role_for_request
request_identity = parent.request_identity
request_bytes = parent.request_bytes
request_sha = parent.request_sha


class WordingWorkerContract(parent.ChatProductContract):
    @property
    def context_policy(self):
        return generation_policy()

    def descriptor(self):
        return {**super().descriptor(), 'generation_wording': WORDING_VERSION,
                'review_contract_version': parent.CONTRACT.version}

    def require_provider(self, provider):
        from app.evaluation.sol_natural_contract import SolNaturalContract
        from app.runtime.observed_provider import ObservedLLMProvider
        SolNaturalContract.require_provider(self, provider)
        selected = provider._delegate if isinstance(provider, ObservedLLMProvider) else provider
        if getattr(selected, 'contract_module', None) is not sys.modules[__name__]:
            raise ValueError('wording_worker_provider_binding')


CONTRACT = WordingWorkerContract(version='1.7.11')


def component_fingerprints(skill):
    from app.evaluation.prompt_context_identity import ComponentFingerprint
    rows = {r.component_id: r for r in parent.component_fingerprints(skill)}
    rows['generation_policy'] = rows['generation_policy'].model_copy(update={
        'sha256': hashlib.sha256(CONTRACT.context_policy.encode()).hexdigest()})
    for path in ('app/product/player_wording_worker.py', 'app/product/player_wording_contract.py',
                 'app/product/generation_binding.py'):
        key = path.replace('/', '.').removesuffix('.py')
        rows[key] = ComponentFingerprint(component_id=key, source=path,
            sha256=hashlib.sha256((ROOT / path).read_text(encoding='utf-8').encode()).hexdigest())
    return tuple(rows.values())
