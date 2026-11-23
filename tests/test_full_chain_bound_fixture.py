"""Complete fixture binding, not automated semantic judging."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from scripts.full_chain_bound_fixture import ROOT, FIXTURE, load_bundle, sha
from scripts.report_timed_document_workflow import TimedDocumentWorkflow as Workflow, request_sha
from scripts.run_full15_resumption_candidate import selected_controls
from app.evaluation.source_patch_editor import report_inputs


@pytest.fixture(scope='module')
def material():
    seed = selected_controls(timing_mode='time600')[1][0][1]
    old = json.loads((ROOT / 'data/evaluation/fixtures/full_chain_host_count_20261013.json').read_text(encoding='utf-8'))
    return Workflow.build_inputs(replace(seed, report=old['report']))


def test_whole_response_survives_actual_editor_and_final_request(material):
    responses, assembly = load_bundle(ROOT / FIXTURE, sha(ROOT / FIXTURE), material)
    edit = responses['revision'].tool_calls[0].arguments
    assert json.loads(assembly.journal['raw']) == edit
    op = assembly.journal['operations'][0]
    assert {k: op[k] for k in ('before', 'after', 'reason')} == edit['edits']['block_4'][0]
    assert '2/5=40%' in op['reason']  # authored regression, NOT a semantic classifier
    final_inputs = report_inputs(material, assembly.report)
    before, after = json.loads(material.data_json), json.loads(final_inputs.data_json)
    for value in (before, after):
        del value['source_index']['blocks'], value['source_index']['source_digest']
    assert before == after
    assert assembly.journal['final_review_request_sha256'] == request_sha(Workflow.make_request(final_inputs))
    assert assembly.journal['semantic_approval'] is False


@pytest.mark.parametrize('fault', ['changed_reason', 'missing_reason', 'wrong_input', 'wrong_report',
    'wrong_revised_report', 'legacy_format', 'missing_stage', 'wrong_model'])
def test_drift_or_incomplete_fixtures_fail_before_consumption(tmp_path, material, fault):
    value = json.loads((ROOT / FIXTURE).read_text(encoding='utf-8'))
    original_pin = sha(ROOT / FIXTURE)
    if fault == 'changed_reason':
        value['responses']['revision']['tool_calls'][0]['arguments']['edits']['block_4'][0]['reason'] = 'old unrelated means reason'
    if fault == 'missing_reason':
        del value['responses']['revision']['tool_calls'][0]['arguments']['edits']['block_4'][0]['reason']
    if fault == 'wrong_input': value['input_sha256'] = '0' * 64
    if fault == 'wrong_report': value['report_sha256'] = '0' * 64
    if fault == 'wrong_revised_report': value['revised_report_sha256'] = '0' * 64
    if fault == 'legacy_format': value = dict(before='old', after='new')
    if fault == 'missing_stage': del value['responses']['final']
    if fault == 'wrong_model': value['responses']['revision']['model'] = 'glm-5.3'
    path = tmp_path / 'bundle.json'
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    with pytest.raises(ValueError):
        load_bundle(path, original_pin if fault == 'changed_reason' else sha(path), material)


def test_reauthoring_a_reason_is_not_semantic_certification(tmp_path, material):
    # A new pin can bind a wrong explanation. Host review must still reject it;
    # a hash or schema must never pretend to prove semantics.
    value = deepcopy(json.loads((ROOT / FIXTURE).read_text(encoding='utf-8')))
    value['responses']['revision']['tool_calls'][0]['arguments']['edits']['block_4'][0]['reason'] = 'unrelated means direction'
    path = tmp_path / 'reauthored.json'
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    _, assembly = load_bundle(path, sha(path), material)
    assert assembly.journal['operations'][0]['reason'] == 'unrelated means direction'
    assert assembly.journal['semantic_approval'] is False
