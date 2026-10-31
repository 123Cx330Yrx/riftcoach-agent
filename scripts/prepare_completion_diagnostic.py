"""Zero-send verification of the diagnostic engine against original native evidence."""
import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from app.evaluation import completion_diagnostic_session as engine
from app.evaluation import sol_completion_contract as contract
from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import SessionPaused, digest
from app.runtime.sol_natural_provider import SolNaturalProvider, SolReviewProvider
from app.providers.zhipu import ZhipuProvider
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
from app.evaluation.golden_stream_bridge import NATURAL_FLASH_TRANSPORT_ID
from scripts.reviewer_profile_batch import inventory
from scripts.sol_natural_launch import host


class NoGenerationProvider:
    provider_name, model_name = 'zhipu', 'glm-5.3-flash'
    thinking_profile_id = ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE.profile_id
    sdk_max_retries, runtime_profile = 0, None
    capabilities, transport_id = ZhipuProvider.capabilities, NATURAL_FLASH_TRANSPORT_ID

    def chat(self, *args, **kwargs):
        raise AssertionError('completion_generation_forbidden')


def prepare(proof_file, proof_sha, output):
    output = Path(output).resolve()
    spec = engine.parent_binding(proof_file, proof_sha)
    parent = Path(spec['proof']['parent_operator'])
    authors = parent.with_name(parent.name+'-authors')
    plan = engine.read(parent/'plan.json')
    if Path.cwd().resolve() != contract.ROOT.resolve() or Path(sys.executable).resolve() != Path(plan['python']).resolve():
        raise ValueError('completion_actual_execution_paths_required')
    if output.exists() or any(output.is_relative_to(p) or p.is_relative_to(output)
                              for p in (parent, authors, contract.ROOT, Path(plan['cwd']))):
        raise ValueError('completion_new_external_output_required')
    before = inventory(parent), inventory(authors)
    calls = []

    def boundary():
        calls.append('control-b')
        raise SessionPaused('completion_verified_zero_send_boundary')

    def deny(*args, **kwargs):
        raise AssertionError('completion_offline_provider_forbidden')

    with TemporaryDirectory(prefix='completion-diagnostic-') as temporary, host(plan) as events:
        session, gate = engine.open_session(Path(temporary)/'operator', spec, events,
                                            before_new_model=boundary)
        router = SolNaturalProvider(NoGenerationProvider(), SolReviewProvider(api_key='OFFLINE_NO_SEND',
            directory=session.transport_root/'review', task_directory=session.transport_root,
            sender=deny, contract_module=contract), contract_module=contract)
        try:
            with session:
                engine.run_chain(session, router)
        except SessionPaused as error:
            if str(error) != 'completion_verified_zero_send_boundary':
                raise
        else:
            raise ValueError('completion_diagnostic_boundary_not_reached')
        if (calls != ['control-b'] or session.cursor != 9 or session.new_models != 0
                or inventory(session.transport_root)
                or list(gate.handles()) != [spec['proof']['accepted_handle']]):
            raise ValueError('completion_diagnostic_unexpected_new_activity')
        inherited = engine.read(session.root/'parent-import.json')
    if before != (inventory(parent), inventory(authors)):
        raise ValueError('completion_diagnostic_changed_originals')
    result = dict(version='completion-diagnostic-native-preparation-v1',
        parent_proof_sha256=proof_sha, parent_seal_sha256=spec['proof']['parent_seal_sha256'],
        contract=contract.CONTRACT.snapshot().model_dump(mode='json'),
        actual_cwd=str(Path.cwd().resolve()), actual_python=str(Path(sys.executable).resolve()),
        imported_operations=9, inherited_budget=inherited['historical_budget'],
        inherited_active_seconds=spec['proof']['inherited_active_seconds'],
        original_native_and_author_replayed=True, original_inventories_unchanged=True,
        next_stage='control-b', provider_requests=0, key_reads=0,
        paid_launcher_ready=False, execution_authorized=False,
        semantic_improvement_proven=False, qualified=False, publication_allowed=False)
    output.mkdir(parents=True, exist_ok=False)
    write_new_json(output/'preparation.json', result)
    return dict(provider_requests=0, key_reads=0, next_stage='control-b',
                preparation_sha256=digest((output/'preparation.json').read_bytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof', type=Path, required=True)
    parser.add_argument('--proof-sha', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.proof, args.proof_sha, args.output), ensure_ascii=True))


if __name__ == '__main__':
    main()
