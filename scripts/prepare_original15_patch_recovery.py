"""Zero-send proof and actual native-prefix consumption before paid preparation."""
import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from app.evaluation import original15_patch_recovery as engine, sol_review_contract as contract
from app.evaluation.sol_natural_session import SessionPaused, digest
from app.evaluation.golden_journal import write_new_json
from scripts import sol_original15_launch as original, sol_natural_launch as base
from scripts.original15_native_snapshot import CaseReplayReadSnapshot
from scripts.reviewer_profile_batch import inventory


def prepare(parent, seal_sha, key, output):
    parent, output = Path(parent).absolute(), Path(output).absolute()
    plan = engine.read(parent/'plan.json')
    if (Path.cwd().resolve() != contract.ROOT or Path(sys.executable).resolve() != Path(plan['python']).resolve()
            or output.resolve() != output or output.exists()
            or any(output.is_relative_to(p) or p.is_relative_to(output)
                for p in (parent, parent.with_name(parent.name+'-authors'), contract.ROOT))):
        raise ValueError('patch_recovery_preparation_paths')
    output.mkdir(parents=True)
    checkpoints = []
    def deny(*args, **kwargs):
        raise AssertionError('patch_recovery_preparation_provider_forbidden')
    with base.host(plan) as events:
        client = events.client
        snapshot = CaseReplayReadSnapshot(client)
        events.client = snapshot
        try:
            spec = engine.prepare_parent(parent, seal_sha, key, events, output/'parent-proof.json')
            with TemporaryDirectory(prefix='original15-patch-inheritance-') as temporary:
                session, gate = engine.open_session(Path(temporary)/'operator', spec, events,
                    sink=lambda value: checkpoints.append(value))
                session.max_new_models = 0
                try:
                    with session:
                        engine.run_case(session, original.router_for(session, 'OFFLINE_NO_SEND', deny))
                except SessionPaused as error:
                    if str(error) != 'session_awaiting_patch_coordination':
                        raise
                else:
                    raise ValueError('patch_recovery_preparation_boundary_not_reached')
                proof = spec['proof']
                if (session.cursor != 9 or session.new_models != 0 or list(gate.handles()) != proof['accepted_handles']
                        or session.status()['closed'] or session.status()['unresolved']
                        or inventory(session.transport_root) != {p.removeprefix('transport/'):sha
                            for p,sha in proof['inherited_files'].items() if p.startswith('transport/')}):
                    raise ValueError('patch_recovery_preparation_unexpected_activity')
                material = engine.read(session.journal_root/'patch-conflicts.json')
                if engine.direct.inventory_sha(material) != proof['conflict_inventory_sha256']:
                    raise ValueError('patch_recovery_preparation_conflict_changed')
                write_new_json(output/'conflict-inventory.json', material)
                write_new_json(output/'preflight-checkpoints.json', checkpoints)
                result = dict(version=engine.VERSION+'-zero-send-preparation', key=key,
                    parent_proof_sha256=spec['proof_sha256'], parent_seal_sha256=seal_sha,
                    inherited_operations=8, replayed_operations=session.cursor,
                    inherited_budget=proof['historical_budget'],
                    inherited_batch_accounting=proof['historical_batch_accounting'],
                    inherited_active_seconds=proof['inherited_active_seconds'],
                    original_native_reviews_replayed=True, original_author_bytes_verified=True,
                    original_receipts_replayed=True, literal_prefix_consumed_by_current_workflow=True,
                    paused=True, next_stage='patch-coordination', new_native_tasks=0,
                    actual_cwd=str(Path.cwd().resolve()), actual_python=str(Path(sys.executable).resolve()),
                    original_guard_stdout_sha256=checkpoints[0]['guard_sha256'],
                    exit_checkpoint_stdout_sha256=checkpoints[-1]['checkpoint_sha256'],
                    temporary_preflight_destroyed=True, real_recovery_session_created=False,
                    paid_launcher_ready=False, provider_requests=0, key_reads=0,
                    qualified=False, publication_allowed=False)
            engine.verify_parent(spec)
        finally:
            events.client = client
            snapshot.responses.clear()
    write_new_json(output/'preparation.json', result)
    return dict(output=str(output), preparation_sha256=digest((output/'preparation.json').read_bytes()),
        parent_proof_sha256=spec['proof_sha256'], provider_requests=0, key_reads=0, paid_launcher_ready=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--seal-sha', required=True)
    parser.add_argument('--case', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.parent, args.seal_sha, args.case, args.output), ensure_ascii=True))


if __name__ == '__main__':
    main()
