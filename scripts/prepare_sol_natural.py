"""Offline actual-application capture; no credentials or paid execution entry."""
import argparse
from decimal import Decimal
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.evaluation import sol_natural_contract as contract
from app.runtime.sol_natural_provider import SolNaturalProvider, SolReviewProvider
from scripts import natural_duty_preparation as base


class CaptureFactory(base.CaptureFactory):
    def make(self):
        old = super().make()
        # Identity only: neither directory is created and chat is never reached.
        reviewer = SolReviewProvider(api_key='', directory=Path('_offline_only/review'),
                                     task_directory=Path('_offline_only'))
        return SolNaturalProvider(old.generator, reviewer)


def cost_envelope():
    # Cumulative timeout allowance is shared across roles; logical calls stay 2+4.
    costs = []
    retries = contract.CONTRACT.descriptor()['transport_retries']
    for extra_generation in range(retries+1):
        generation, reviews = 2+extra_generation, 4+retries-extra_generation
        remaining, cost = contract.CONTRACT.descriptor()['total_tokens'], Decimal(0)
        for cap, rate in ((generation*32768, '2.8'), (reviews*16384, '2'),
                          (generation*64000, '.8'), (reviews*64000, '.4')):
            used = min(remaining, cap)
            cost += Decimal(used)*Decimal(rate)/1_000_000
            remaining -= used
        costs.append(cost)
    return str(max(costs))


def capture(run_id):
    factory = CaptureFactory()
    with TemporaryDirectory(prefix='riftcoach-sol-natural-') as directory:
        prepared = base.build_application(provider_factory=factory, output_root=directory,
                                          run_id=run_id, candidate=contract)
        try:
            prepared.run()
        except base._Captured:
            pass
        if factory.first is None:
            raise ValueError('sol_first_request_not_reached')
    raw = contract.request_bytes(factory.first)
    preparation = dict(version='sol-natural-offline-preparation-v1', run_id=run_id,
        first_request_sha256=base.sha(raw), source_sha256=base.SOURCE_SHA,
        source_projection_time=base.SOURCE_NOW, relationship='observed', memory_records=0,
        source_scope='frozen_public_development_not_holdout', preselected_knowledge=False,
        contract=contract.CONTRACT.snapshot().model_dump(mode='json'),
        limits={key: contract.CONTRACT.descriptor()[key] for key in
                ('max_calls', 'total_tokens', 'execution_timeout_s', 'transport_retries')},
        estimated_uncached_cny=cost_envelope(), hard_billing_cap=False,
        provider_requests=0, key_read=False, semantic_approval=False,
        execution_authorized=False, paid_launcher_ready=False, production_admitted=False)
    return factory.first, preparation


def prepare(run_id):
    return capture(run_id)[1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default='sol-natural-offline-20261019')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.run_id)
    with args.output.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(result, ensure_ascii=True, indent=2) + '\n')
    print(json.dumps(dict(provider_requests=0, key_read=False, paid_launcher_ready=False)))
