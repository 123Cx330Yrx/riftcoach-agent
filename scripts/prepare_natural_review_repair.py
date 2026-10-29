"""Read-only proof for reusing a sealed pair; no credentials or model sends."""
import argparse
from pathlib import Path

from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import digest
from scripts import natural_review_repair_continuation as repair
from scripts import sol_natural_launch as launch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent-operator', required=True, type=Path)
    parser.add_argument('--parent-seal-sha', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    parent = args.parent_operator.resolve()
    output = args.output.resolve()
    if output.is_relative_to(parent) or parent.is_relative_to(output.parent):
        raise ValueError('repair_proof_outside_parent_required')
    with launch.host(repair.read(parent/'plan.json')) as events:
        proof = repair.audit(parent, args.parent_seal_sha, events)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_new_json(output, proof)
    bound = repair.bind(output, digest(output.read_bytes()))
    launch.emit(dict(proof=str(output), proof_sha256=bound['proof_sha256'],
        inherited_operations=bound['prefix_operations'], inherited_budget=bound['historical_budget'],
        remaining_attempts=bound['remaining_attempts'], provider_requests=0, key_reads=0,
        execution_authorized=False, publication_allowed=False))


if __name__ == '__main__':
    main()
