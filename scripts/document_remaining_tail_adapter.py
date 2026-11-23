"""Five unexecuted tails, using isolated copies of the frozen checkpoint core.

No old imported module is patched. The closed first case is excluded, never
resigned or replayed as a successful stage. CLI: run / handoff / seal, followed
by the corresponding existing checkpoint command arguments.
"""
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import sys

from scripts import run_document_accepted_tails as original

KEYS = ('claim-scope:6', 'observed:2', 'observed:3', 'observed:4', 'observed:5')
RUN_ID = 'document-remaining-checkpoint-tails-20261009'
PREVIOUS_SEAL = 'data/evaluation/results/golden_document_checkpoint_tails_result_20261009.json'
PREVIOUS_SHA = 'b87882fd3fc86bc1d3dc873930aabe090fc4b63e1ad1c3ae7405d31a32ca7700'
ADAPTER_SOURCE = 'scripts/document_remaining_tail_adapter.py'


def isolated(name):
    """Load our fixed repository code without replacing sys.modules entries."""
    spec = importlib.util.spec_from_file_location(
        'scripts._remaining_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = isolated('run_document_accepted_tails')
runner = isolated('run_document_checkpoint_tails')
handoff = isolated('document_checkpoint_tail_handoff')
seal = isolated('seal_document_checkpoint_tails')
base = runner.base
_checkpoint_prepare = runner.prepare


def controls():
    """Validate the closed inventory, then reuse unchanged accepted inputs."""
    path = base.ROOT / PREVIOUS_SEAL
    if base.sha(path) != PREVIOUS_SHA:
        raise ValueError('remaining_tail_prior_seal_changed')
    previous = json.loads(path.read_bytes())
    result = previous['execution_result']
    if (previous['run_id'] != 'document-checkpoint-tails-20261009'
            or result.get('error_code') != 'checkpoint_tail_operator_abort'
            or result['calls'] != 1 or previous['stages']
            or result['unexecuted_keys'] != list(KEYS)):
        raise ValueError('remaining_tail_prior_inventory_changed')
    variants = original.controls()
    if [row['key'] for row, *_ in variants] != list(original.KEYS):
        raise ValueError('remaining_tail_historical_inventory_changed')
    return [item for item in variants if item[0]['key'] in KEYS]


def prepare(*, root_thread_id, independent_thread_id):
    plan = _checkpoint_prepare(root_thread_id=root_thread_id,
        independent_thread_id=independent_thread_id)
    roles = {'glm-5.3-flash': 5, 'glm-5.3': 5}
    prices = runner.backend.CONTRACT.pricing_profiles
    cost = sum(count * (Decimal(64000) * prices['zhipu', model].input_cost_per_million
        + Decimal(32768) * prices['zhipu', model].output_cost_per_million) / 1_000_000
        for model, count in roles.items())
    plan.update(historical_initial_inputs=5, role_calls=roles,
        previous_closed_seal=PREVIOUS_SEAL, previous_closed_seal_sha256=PREVIOUS_SHA,
        excluded_case=dict(key='scope:4', reason='executed_edit_unattested_host_abort',
            credit=0, provider_calls_repeated=False),
        development_independent_model='gpt-6.1-sol',
        success_scope='Five previously unexecuted historical-accepted-opinion-conditioned '
            'tails only. The closed scope:4 edit remains unattested. No same-batch '
            'original15 or product qualification; attribution:1 and scope:3 remain unresolved.')
    plan['budget'].update(max_calls=10, max_tokens=967680, max_active_seconds=3000,
        estimated_uncached_cny=str(cost))
    return plan


def observe(factory, directory, plan, *, event_source,
            adjudicate=runner.wait_reviews, before_send=lambda: None):
    if (plan.get('run_id') != RUN_ID
            or plan.get('host_task_checkpoint', {}).get('version') != runner.checkpoint.VERSION):
        raise ValueError('remaining_tail_plan')

    def inspect_checkpoint(path, remaining):
        submission = adjudicate(path, remaining)
        folder = Path(path).parent
        required = json.loads(Path(path).read_bytes())
        value = json.loads((folder / 'stage.json').read_bytes())
        bound = required['binding']
        expected_task = json.loads(handoff.task_from_stage(plan, value, bound, folder.parent))
        handoff.validate_checkpoint_files(folder, submission, expected_task, plan, bound)
        return submission

    return legacy.observe(factory, directory, plan, event_source=event_source,
        adjudicate=inspect_checkpoint, before_send=before_send)


# Explicit wiring is local to these four isolated module objects. Frozen old
# helpers and replays keep their original module objects, KEYS and run_id.
legacy.KEYS, legacy.controls = KEYS, controls
runner.legacy = legacy
runner.KEYS, runner.RUN_ID, runner.controls = KEYS, RUN_ID, controls
runner.SOURCE_FILES = (*runner.SOURCE_FILES, ADAPTER_SOURCE)
runner.prepare, runner.observe = prepare, observe
handoff.runner = runner
seal.runner, seal.handoff = runner, handoff


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('run', 'handoff', 'seal'):
        raise SystemExit('usage: document_remaining_tail_adapter {run|handoff|seal} [arguments]')
    action = sys.argv.pop(1)
    {'run': runner.main, 'handoff': handoff.main, 'seal': seal.main}[action]()


if __name__ == '__main__':
    main()
