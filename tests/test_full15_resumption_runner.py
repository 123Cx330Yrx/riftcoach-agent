import json

from scripts import run_full15_resumption_candidate as runner
from scripts.diagnose_role_context import canonical_sha


def test_full15_runner_prepares_all_cases_without_provider_io():
    plan = runner.prepare(root_thread_id='root', independent_thread_id='independent')
    assert len(plan['cells']) == 15
    assert plan['sequence'] == [cell['key'] for cell in plan['cells']]
    assert plan['budget']['role_calls'] == {'glm-5.3': 30, 'glm-5.3-flash': 15}
    assert plan['budget']['max_calls'] == 45
    assert plan['execution_authorized'] is False
    assert plan['paid_plan_frozen'] is False
    assert plan['new_qualification'] == 0
    assert canonical_sha(plan) == canonical_sha(json.loads(json.dumps(plan)))


def test_runner_controls_keep_candidate_baseline_byte_contract():
    rows, variants = runner.controls()
    assert len(rows) == len(variants) == 15
    for row, (_, _, _, request) in zip(rows, variants):
        assert row['candidate_request_sha256']
        assert runner.candidate.request_identity(request) == ('zhipu', 'glm-5.3')
