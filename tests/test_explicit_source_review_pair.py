from types import SimpleNamespace as NS
import json

import pytest

from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_explicit_source_projection import VERSION
from scripts import run_explicit_source_review_pair as runner
from scripts import run_review_model_comparison as stopped
from tests.test_explicit_source_projection import actual_arguments
from tests.test_review_model_comparison import fake_provider, decision
from tests.test_golden_native_partitioned_tool_review import tool_response, valid_review
from dataclasses import replace


def test_preparation_is_reproducible_without_private_run_files(monkeypatch):
    from pathlib import Path
    original = Path.open

    def guard(path, *args, **kwargs):
        if '/data/runs/' in path.as_posix():
            pytest.fail('preparation accessed private run files')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', guard)
    variants, plan = runner.prepare_pair()
    assert len(variants) == 2
    assert plan['proposed_diagnostic_budget'] == dict(max_calls=2, max_seconds_total=600,
        max_seconds_per_call=300, total_token_reservation=154846)
    assert all(r.metadata['source_projection'] == VERSION for _, _, r in variants)
    assert runner.RUN_DIRECTORY != stopped.RUN_DIRECTORY


@pytest.mark.parametrize('mode', ['missing_approval', 'wrong_plan', 'ci_failure', 'already_run'])
def test_gates_precede_credentials_or_provider(monkeypatch, tmp_path, mode):
    variants, plan = runner.prepare_pair()
    args = NS(execute=True, approval_plan_sha=plan['preparation_sha256'], ci_run='test', env_file=None)
    called = []
    def prepare():
        called.append('prepare')
        return variants, plan
    def ci(_):
        called.append('ci')
        if mode == 'ci_failure':
            raise ValueError('exact_sha_public_ci_required')
        return 'a' * 40
    monkeypatch.setattr(runner, 'prepare_pair', prepare)
    monkeypatch.setattr(runner, 'verify_public_ci', ci)
    monkeypatch.setattr(runner, 'RUN_DIRECTORY', tmp_path)
    import dotenv
    monkeypatch.setattr(dotenv, 'dotenv_values', lambda *_: pytest.fail('gate accessed credentials'))
    if mode == 'missing_approval':
        args.approval_plan_sha = ''
    elif mode == 'wrong_plan':
        args.approval_plan_sha = 'b' * 64
    with pytest.raises(FileExistsError if mode == 'already_run' else ValueError):
        runner.run(args)
    assert called == ([] if mode == 'missing_approval' else
                      ['prepare'] if mode == 'wrong_plan' else ['prepare', 'ci'])


def test_original_bad_response_stops_new_batch_before_second_call(tmp_path, actual_arguments):
    variants, plan = runner.prepare_pair()
    provider = fake_provider([replace(tool_response(actual_arguments), model='glm-5.3')])
    result = runner.observe(provider, tmp_path, variants, plan,
                            adjudicate=lambda *_: pytest.fail('invalid response reached host acceptance'))
    assert result['experiment'] == runner.EXPERIMENT
    assert result['error_code'] == 'semantic_source_id_unknown'
    assert result['reserved_calls'] == result['completed_calls'] == 1
    assert result['unknown_usage_calls'] == 0
    assert not (tmp_path / variants[1][0]).exists()
    public = json.loads((tmp_path / variants[0][0] / 'response.json').read_text(encoding='utf-8'))
    assert public['tool_calls'][0]['arguments'] == actual_arguments


def test_offline_acceptance_journal_binds_actual_projected_request(tmp_path):
    variants, plan = runner.prepare_pair()
    provider = fake_provider([replace(tool_response(valid_review()), model='glm-5.3')] * 2)
    result = runner.observe(provider, tmp_path, variants, plan, adjudicate=decision(True))
    assert result['pair_accepted'] and not result['production_admitted']
    assert result['experiment'] == runner.EXPERIMENT
    for name, _, request in variants:
        journal = json.loads((tmp_path / name / 'journal.json').read_text(encoding='utf-8'))
        assert journal['diagnostic_experiment'] == runner.EXPERIMENT
        assert journal['source_projection'] == VERSION
        assert journal['policy_sha256'] == digest(request.messages[0].content)
        assert journal['validator_policy_sha256'] != journal['policy_sha256']
        assert journal['raw_sha256'] == digest(compact(valid_review()))
