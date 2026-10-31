"""ADR0119 opt-in product contract; original diagnostic requests are reused.

The execution snapshot is new. Review messages, schema, transport and policy
remain byte-identical to the dual-necessity candidate; no default is switched.
"""
import hashlib
import json
import sys

from app.evaluation import sol_review_contract as parent

VERSION = 'natural-flash-sol-product-v1'
WORKER_PROFILE = 'sol-dual-product-v1'
ROOT, legacy = parent.ROOT, parent.legacy
ASSETS = ROOT / 'examples/runtime_profiles/sol_product_v1'
CONTEXT, RESPONSE_MODE, REVIEW_TRANSPORT = parent.CONTEXT, parent.RESPONSE_MODE, parent.REVIEW_TRANSPORT
PROVIDER, MODEL, PROFILE = parent.PROVIDER, parent.MODEL, parent.PROFILE
REVIEW_PROVIDER, REVIEW_MODEL, REVIEW_PROFILE = parent.REVIEW_PROVIDER, parent.REVIEW_MODEL, parent.REVIEW_PROFILE
FRESH_REVIEW_RESERVATION = parent.FRESH_REVIEW_RESERVATION
make_request, restore_context, validate_business = parent.make_request, parent.restore_context, parent.validate_business
role_for_request, request_identity = parent.role_for_request, parent.request_identity
request_bytes, request_sha = parent.request_bytes, parent.request_sha


class ProductContract(parent.DualNecessityContract):
    def descriptor(self):
        value = super().descriptor()
        value.update(contract_id=VERSION, component_contract=VERSION,
            max_calls=8, total_tokens=401920, execution_timeout_s=900,
            transport_retries=2, generation_logical_calls=4,
            time_basis='cumulative-active-seconds', workflow_scope='opt-in-product',
            qualification_only=False, publication_policy='dual-review-exact-application-v1',
            reused_business_contract=parent.VERSION)
        return value

    def snapshot(self):
        return legacy.CoachContractSnapshot(contract_id=VERSION, version=self.version,
            sha256=hashlib.sha256(json.dumps(self.descriptor(), sort_keys=True, separators=(',', ':')).encode()).hexdigest())

    def require_provider(self, provider):
        parent.parent.baseline.SolNaturalContract.require_provider(self, provider)
        from app.runtime.observed_provider import ObservedLLMProvider
        selected = provider._delegate if isinstance(provider, ObservedLLMProvider) else provider
        if getattr(selected, 'contract_module', None) is not sys.modules[__name__]:
            raise ValueError('sol_product_provider_contract')


CONTRACT = ProductContract(version='1.7.0')


def component_fingerprints(skill):
    from app.evaluation.prompt_context_identity import ComponentFingerprint
    rows = {r.component_id: r for r in parent.component_fingerprints(skill)}
    for path in ('app/product/sol_contract.py', 'app/product/sol_workflow.py',
                 'app/product/manual_retry_grant.py'):
        key = path.replace('/', '.').removesuffix('.py')
        rows[key] = ComponentFingerprint(component_id=key, source=path,
            sha256=hashlib.sha256((ROOT / path).read_text(encoding='utf-8').encode()).hexdigest())
    return tuple(rows.values())
