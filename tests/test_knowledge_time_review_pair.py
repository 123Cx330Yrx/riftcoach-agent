"""The date experiment changes evidence, never labels or review policy."""
import json

import pytest

from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import REQUEST, REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.providers.zhipu import ZhipuProvider
from app.providers.zhipu_profiles import ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE
from scripts import run_knowledge_time_review_pair as runner
from scripts.native_contract_options import body
from scripts.prepare_review_model_comparison import mock_wire


def test_pair_changes_only_attributable_times_and_single_reference_edit(monkeypatch):
    import socket
    from pathlib import Path

    original_read = Path.read_text
    def read(path, *args, **kwargs):
        assert 'data/runs/' not in path.as_posix() and path.name != '.env'
        return original_read(path, *args, **kwargs)
    def no_network(*args, **kwargs):
        raise AssertionError('offline preparation cannot use network')
    monkeypatch.setattr(Path, 'read_text', read)
    monkeypatch.setattr(socket, 'create_connection', no_network)
    variants, plan = runner.prepare()
    original = json.loads(runner.EVIDENCE.read_text(encoding='utf-8'))
    old = REQUEST.validate_json(compact(original['public_json_contents']['transport/review/request-003.json']))
    before, after = body(old), body(variants[0][2])
    assert before['source_roots']['additional'] == after['source_roots']['additional']
    after['source_roots']['catalog_sha256'] = before['source_roots']['catalog_sha256']
    times = after['knowledge'].pop('retrievals')
    for citation in after['knowledge']['citations']:
        assert citation.pop('retrievals') == [
            {'provider': row['provider'], 'retrieved_at': row['retrieved_at']}
            for row in times if citation['chunk_id'] in row['chunk_ids']]
    assert after == before and times == plan['retrievals']
    assert len(times) == 3 and all(row['retrieved_at'] for row in times)
    assert variants[0][2].messages[0] == variants[1][2].messages[0] == old.messages[0]
    assert variants[0][2].tools == variants[1][2].tools == old.tools
    original_blocks = variants[0][1].source.blocks
    corrected_blocks = variants[1][1].source.blocks
    assert [index for index, (a, b) in enumerate(zip(original_blocks, corrected_blocks, strict=True), 1) if a != b] == [27]
    assert all(cell['expected_host_only'] not in compact(REQUEST.dump_python(v[2], mode='json'))
        for v, cell in zip(variants, plan['cells'], strict=True))
    assert runner.prepare()[1] == plan
    saved = json.loads((runner.ROOT / 'data/evaluation/results/golden_knowledge_time_preparation_v2.json').read_text(encoding='utf-8'))
    assert saved['preparation_plan'] == plan
    assert saved['preparation_plan_sha256'] == digest(compact(plan))
    assert plan['provider_requests'] == 0 and not plan['production_admitted']


def test_real_failed_sources_now_resolve_their_own_times_without_changing_history():
    from app.evaluation import golden_native_issues_review as native
    from hashlib import sha256

    failure_bytes = runner.PREDECESSOR.read_bytes()
    failure = json.loads(failure_bytes)
    variants, plan = runner.prepare()
    assert plan['predecessor_result_sha256'] == sha256(failure_bytes).hexdigest()
    old_sources = failure['host_review']['selected_issue_sources']
    assert [row['source_id'] for row in old_sources] == [26, 27, 28, 29, 30]
    new_sources = native.resolve_refs(variants[0][1], [row['source_id'] for row in old_sources])
    for old, new in zip(old_sources, new_sources, strict=True):
        value = dict(new['value'])
        assert value.pop('retrievals') == [
            {'provider': row['provider'], 'retrieved_at': row['retrieved_at']}
            for row in plan['retrievals'] if value['chunk_id'] in row['chunk_ids']]
        assert 'retrievals' not in old['value'] and value == old['value']
        assert new['key'] == old['key'] and new['path'] == old['path']
    assert not failure['conclusion']['pair_accepted']
    assert runner.PREDECESSOR.read_bytes() == failure_bytes


def test_sdk_wire_uses_glm_high_and_bound_request_without_network():
    from types import SimpleNamespace
    variants, _ = runner.prepare()
    for _, _, request in variants:
        captured = []
        def create(**kwargs):
            captured.append(kwargs)
            return iter(())
        provider = ZhipuProvider.from_candidate_profile(
            client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))),
            model='glm-5.3', profile=ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE)
        provider._open_stream_for_adapter(request, tool_stream=True, include_usage_tail=True)
        wire = mock_wire(captured[0])
        assert wire['model'] == 'glm-5.3' and wire['reasoning_effort'] == 'high'
        assert wire['max_tokens'] == 32768 and wire['stream'] is True
        assert captured[0]['timeout'] == 300
        assert validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)


@pytest.mark.parametrize('failure', ['approval', 'ci', 'existing_batch'])
def test_execution_stops_before_credentials_or_calls(monkeypatch, tmp_path, failure):
    variants, plan = runner.prepare()
    monkeypatch.setattr(runner, 'prepare', lambda: (variants, plan))
    output = tmp_path / 'batch'
    monkeypatch.setattr(runner, 'RUN_DIRECTORY', output)
    args = runner.parser().parse_args(['--execute', '--approval-plan-sha', digest(compact(plan))])
    def ci(_):
        assert failure == 'ci'
        raise ValueError('test_failed_ci')
    monkeypatch.setattr(runner, 'verify_public_ci', ci)
    if failure == 'approval':
        args.approval_plan_sha = 'outdated'
    elif failure == 'existing_batch':
        output.mkdir()
    with pytest.raises(ValueError, match={
        'approval': 'specific_preparation_approval',
        'ci': 'test_failed_ci',
        'existing_batch': 'batch_exists',
    }[failure]):
        runner.run(args)
    assert not output.exists() or not list(output.iterdir())
