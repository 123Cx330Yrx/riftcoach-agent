"""Capture the actual natural-task first-send boundary without sending or keys."""
import argparse
from dataclasses import asdict
from decimal import Decimal
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.evaluation import sol_necessity_contract as contract
from app.runtime.sol_natural_provider import SolNaturalProvider, SolReviewProvider
from scripts import natural_duty_preparation as base


class CaptureFactory(base.CaptureFactory):
    def make(self):
        old = super().make()
        reviewer = SolReviewProvider(api_key='', directory=Path('_offline_only/review'),
            task_directory=Path('_offline_only'), contract_module=contract)
        return SolNaturalProvider(old.generator, reviewer, contract_module=contract)


def cost_envelope():
    prices = contract.CONTRACT.pricing_profiles
    flash, sol = prices['zhipu', 'glm-5.3-flash'], prices['tianjige', 'gpt-6.1-sol']
    costs = []
    limits = contract.CONTRACT.descriptor()
    for extra_generation in range(limits['transport_retries']+1):
        generation, reviews = 2+extra_generation, 4+limits['transport_retries']-extra_generation
        remaining, cost = limits['total_tokens'], Decimal(0)
        # Allocate the shared token envelope to the most costly categories first.
        for cap, rate in sorted(((generation*32768, flash.output_cost_per_million),
                (reviews*16384, sol.output_cost_per_million),
                (generation*64000, flash.input_cost_per_million),
                (reviews*64000, sol.input_cost_per_million)), key=lambda x:x[1], reverse=True):
            used = min(remaining, cap)
            cost += Decimal(used)*rate/1_000_000
            remaining -= used
        costs.append(cost)
    return str(max(costs))


def prepare(run_id='necessity-natural-offline-20261024'):
    factory = CaptureFactory()
    with TemporaryDirectory(prefix='riftcoach-necessity-natural-') as directory:
        application = base.build_application(provider_factory=factory, output_root=directory,
            run_id=run_id, candidate=contract)
        try:
            application.run()
        except base._Captured:
            pass
        if factory.first is None:
            raise ValueError('necessity_natural_first_request_not_reached')
    raw = contract.request_bytes(factory.first)
    return dict(kind='necessity-natural-offline-preparation-v1', run_id=run_id,
        contract=contract.CONTRACT.snapshot().model_dump(mode='json'),
        first_request_sha256=base.sha(raw), source_sha256=base.SOURCE_SHA,
        relationship='observed', memory_records=0, preselected_knowledge=False,
        source_scope='familiar_public_development_not_holdout',
        profile=asdict(contract.REVIEW_PROFILE), group_independently_verified=False,
        logical_generation_calls=2, logical_review_calls=4,
        limits={k:contract.CONTRACT.descriptor()[k] for k in
            ('max_calls', 'total_tokens', 'execution_timeout_s', 'transport_retries')},
        estimated_uncached_cny=cost_envelope(), hard_billing_cap=False,
        provider_requests=0, key_read=False, paid_launcher_ready=False,
        execution_authorized=False, semantic_approval=False, qualified=False,
        production_admitted=False, publication_allowed=False,
        remaining_before_paid=['Explicit new task authorization and frozen code/CI binding',
            'Manual repeated-timeout continuation policy; current Runtime has one bounded automatic retry',
            'Actual native author/check-answer/final/import preflight for the new task'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = prepare()
    with args.output.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2)+'\n')
    print(json.dumps(dict(provider_requests=0, key_read=False, paid_launcher_ready=False)))
