from dataclasses import replace
import json

import pytest

from app.evaluation import golden_native_buffered_block_review as current
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
from app.harness.steps import RevisionRequest
from tests import test_golden_native_block_tool_review as block_tests
from tests.test_golden_native_partitioned_tool_review import exchange_provider, tool_response, valid_review
from tests.test_native_editor_product_budget import offline  # autouse no-network guard


@pytest.fixture(autouse=True)
def committed_inputs_only(monkeypatch):
    from pathlib import Path
    original = Path.open
    def checked(path, *args, **kwargs):
        assert 'data/runs/' not in path.as_posix(), 'Tests must use committed source fixtures'
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', checked)


def independent(flat, count):
    value = block_tests.grouped(flat, count)
    del value['issue_resolutions']
    return value


def test_independent_contract_preserves_raw_and_declares_internal_projection():
    _, inputs, count = block_tests.control()
    raw = compact(independent(valid_review(advisory=True), count))
    payload, wire, journal = current.validate(raw, inputs)
    assert payload.verdict == 'pass' and not payload.issues
    assert journal['parsed_review'] == json.loads(raw) == wire.model_dump()
    assert journal['raw'] == raw and journal['raw_sha256'] == digest(raw)
    assert journal['validator_projection']['issue_resolutions'] == []
    prepared = current.request(inputs)
    assert set(prepared.tools[0].input_schema['required']) == {'reviews', 'score', 'verdict'}
    assert 'issue_resolutions' not in prepared.messages[0].content
    assert not prepared.messages[1].content.startswith(current.native.schema_notation(prepared.tools[0].input_schema))
    original = current.previous.request(inputs)
    header = current.native.schema_notation(original.tools[0].input_schema) + '\n'
    assert prepared.messages[1].content == original.messages[1].content[len(header):]
    assert prepared.messages[2:] == original.messages[2:]
    assert journal['policy_sha256'] == digest(prepared.messages[0].content)


@pytest.mark.parametrize('fault', ['extra_old_field', 'missing_block', 'bad_source', 'contradiction', 'duplicate_key'])
def test_independent_schema_does_not_relax_other_guards(fault):
    _, inputs, count = block_tests.control()
    value = independent(valid_review(issue=True), count)
    if fault == 'extra_old_field': value['issue_resolutions'] = []
    elif fault == 'missing_block': value['reviews'].pop()
    elif fault == 'bad_source': value['reviews'][3]['issues'][0]['source_ids'] = [99999]
    elif fault == 'contradiction': value['verdict'] = 'pass'
    raw = compact(value)
    if fault == 'duplicate_key': raw = raw[:-1] + ',"score":95}'
    with pytest.raises(ValueError): current.validate(raw, inputs)


def test_reassessment_keeps_required_prior_issue_mapping():
    _, inputs, count = block_tests.control()
    before = independent(valid_review(issue=True), count)
    before['score'] = 'invalid'
    raw = compact(before)
    prepared = current.request(inputs, previous_raw=raw, diagnostics={'errors': ['score']})
    assert 'issue_resolutions' in prepared.tools[0].input_schema['required']
    resolved = independent(valid_review(issue=True), count)
    with pytest.raises(ValueError): current.validate(compact(resolved), inputs, previous_raw=raw)
    resolved['issue_resolutions'] = []
    with pytest.raises(ValueError, match='resolution_inventory'):
        current.validate(compact(resolved), inputs, previous_raw=raw)
    resolved['issue_resolutions'] = [dict(previous_id=1, disposition='replaced', final_issue=1,
        source_ids=[31], explanation='Scripted prior finding mapping.')]
    payload, _, journal = current.validate(compact(resolved), inputs, previous_raw=raw)
    assert len(payload.issues) == 1 and journal['validator_projection'] is None
    assert journal['previous_issues'][0]['block'] == 4
    assert journal['policy_sha256'] == digest(prepared.messages[0].content)


def test_workflow_recovers_explicitly_then_edits_blockers_and_independently_rechecks():
    req, inputs, count = block_tests.control()
    flat = valid_review(issue=True, advisory=True)
    before = independent(flat, count)
    before['score'] = 'invalid'
    recovered = block_tests.grouped(flat, count)
    recovered['issue_resolutions'] = [dict(previous_id=1, disposition='replaced', final_issue=1,
        source_ids=[31], explanation='Scripted prior finding mapping.')]
    provider = exchange_provider([tool_response(before), tool_response(recovered),
        req.report, tool_response(independent(valid_review(advisory=True), count))])
    flow = current.NativeBusinessReviewWorkflow(BudgetedReviewSender(provider))
    initial = flow.evaluate(req)
    edited = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, initial))
    final = flow.evaluate(replace(req, report=edited.report))
    assert final.verdict.value == 'pass' and flow.calls == 4 and flow.revisions == 1
    editor_data = json.loads(provider.requests[2].messages[1].content.split('[UNTRUSTED DATA]\n')[1].split('\n[END UNTRUSTED DATA]')[0])
    assert len(editor_data['accepted_review']['issues']) == 1
    assert 'advisories' not in editor_data['accepted_review']
    assert 'issue_resolutions' not in provider.requests[3].tools[0].input_schema['properties']


def test_actual_product_five_call_budget_with_phase_specific_contract(tmp_path, monkeypatch):
    original_group = block_tests.grouped
    def initial_group(flat, count):
        value = original_group(flat, count)
        del value['issue_resolutions']
        return value
    monkeypatch.setattr(block_tests, 'current', current)
    monkeypatch.setattr(block_tests, 'grouped', initial_group)
    block_tests.test_block_tool_actual_product_five_call_budget(tmp_path, monkeypatch)


def test_runner_declares_buffered_transport_and_route(capsys, tmp_path):
    from types import SimpleNamespace
    from scripts.run_golden_native_review import run
    plan = run(SimpleNamespace(execute=False, suite='claim-scope', case_index=1,
        provider_route='direct'), candidate_module=current)
    assert plan['provider_route'] == 'direct' and plan['stream_tool_arguments'] is False
    assert plan['max_calls_per_report'] == 5 and plan['max_tokens_per_report'] == 401920


def test_archived_failed_positive_compatibility_is_only_new_contract_offline_evidence():
    from pathlib import Path
    from scripts.run_golden_native_review import prepare_claim_scope
    artifact = json.loads(Path('data/evaluation/results/golden_block_buffered_pair_result_eadb930.json').read_text(encoding='utf-8'))
    case = artifact['cases'][1]
    assert case['original_result']['cases'][0]['valid'] is False
    # claim-scope:1 is the identical attribution:2 input with committed sources.
    _, req = prepare_claim_scope(1)
    assert digest(req.report) == artifact['plan']['conditions'][1]['report_sha256']
    raw = compact(case['response']['tool_calls'][0]['arguments'])
    payload, _, _ = current.validate(raw, current.native.build_inputs(req))
    assert payload.verdict == 'pass' and not payload.issues
