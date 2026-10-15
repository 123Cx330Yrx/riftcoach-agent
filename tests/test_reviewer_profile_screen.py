"""Offline provenance, contrast and isolation checks; no model quality claims."""
from dataclasses import replace
import json
import shutil
import socket

import pytest

from app.evaluation.natural_duty_contract import role_for_request
from app.evaluation.source_patch_editor import report_inputs
from scripts import prepare_reviewer_profile_screen as screen


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('offline screen attempted network')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


@pytest.fixture(scope='module')
def source():
    return screen.source_inputs()


def copy_materials(tmp_path):
    for name in ('r01.md', 'r02.md', 'evaluation.json'):
        shutil.copyfile(screen.PACKAGE/name, tmp_path/name)
    return tmp_path


def test_saved_requests_rebuild_without_network_or_model_results():
    manifest, requests = screen.prepare()
    assert json.loads((screen.PACKAGE/'manifest.json').read_text(encoding='utf-8')) == manifest
    assert len(requests) == 4
    for key, request in requests.items():
        assert json.loads((screen.PACKAGE/'requests'/(key+'.json')).read_text(encoding='utf-8')) == request
        assert len(request['messages']) == 4
        assert request['messages'][0]['role'] == 'system'
        assert request['tools'][0]['name'] == 'submit_report_review'
    assert manifest['provider_calls'] == 0
    assert not manifest['execution_ready'] and not manifest['execution_authorized']
    assert not manifest['qualified'] and not manifest['publication_allowed']
    assert manifest['selected_execution_profile'] is None
    assert manifest['actual_channel_estimate'] is None
    assert 'proposed_profile' not in manifest
    reference = manifest['official_reference_profile']
    assert (reference['provider'], reference['model'], reference['reasoning_effort'], reference['api']) == (
        'openai', 'gpt-6.1-sol', 'high', 'responses')
    budget = manifest['proposed_budget']
    assert budget['official_reference_uncached_estimate_usd'] == '1.82272'
    assert 'standard_uncached_estimate_usd' not in budget
    assert 'official reference only' in budget['pricing_basis']
    assert 'not a third-party channel quote or actual cost' in budget['pricing_basis']
    assert not budget['hard_billing_cap'] and not budget['input_tokenizer_verified']
    assert all(r['model_result'] is None and r['actual_http'] is None for r in manifest['rows'])


def test_derived_pair_preserves_full_source_and_business_policy(source):
    derived = [report_inputs(source, (screen.PACKAGE/(c+'.md')).read_text(encoding='utf-8'))
               for c in ('r01', 'r02')]
    for inputs in derived:
        old, new = json.loads(source.data_json), json.loads(inputs.data_json)
        old.pop('source_index')
        new.pop('source_index')
        assert old == new
        assert len(inputs.source.blocks) == len(source.source.blocks)
        for duty in screen.DUTIES:
            original = screen.make_request(source, duty)
            request = screen.research_request(inputs, duty)
            assert request.messages[0].content == original.messages[0].content
            assert request.tools == original.tools
            assert request.messages[3].content == original.messages[3].content


def test_evaluation_labels_do_not_enter_model_requests(tmp_path):
    package = copy_materials(tmp_path)
    before = screen.prepare(package)[1]
    path = package/'evaluation.json'
    evaluation = json.loads(path.read_text(encoding='utf-8'))
    for case in evaluation['cases']:
        case['proposed_whole_report_verdict'] = 'DO_NOT_LEAK_EXPECTED_LABEL'
        case['rationale'] = 'DO_NOT_LEAK_PRIMARY_OPINION'
    path.write_text(json.dumps(evaluation, ensure_ascii=False), encoding='utf-8')
    assert screen.prepare(package)[1] == before
    assert 'DO_NOT_LEAK' not in json.dumps(before)


@pytest.mark.parametrize('name', ['r01.md', 'r02.md'])
def test_extra_report_change_rejected(tmp_path, name):
    package = copy_materials(tmp_path)
    path = package/name
    path.write_text(path.read_text(encoding='utf-8') + '\nextra assertion', encoding='utf-8')
    with pytest.raises(ValueError, match='screen_not_one_exact_edit|screen_derivation_changed'):
        screen.prepare(package)


def test_material_tamper_rejected(tmp_path, monkeypatch):
    path = tmp_path/'material.json'
    path.write_bytes(screen.MATERIAL.read_bytes() + b' ')
    monkeypatch.setattr(screen, 'MATERIAL', path)
    with pytest.raises(ValueError, match='public_source_snapshot_changed'):
        screen.source_inputs()


def test_old_candidate_identity_cannot_accept_screen(source):
    for duty in screen.DUTIES:
        with pytest.raises(ValueError, match='natural_duty_review_identity'):
            role_for_request(screen.research_request(source, duty))


def test_policy_drift_not_hidden_by_reconstruction(monkeypatch):
    original = screen.make_request
    def changed(*args, **kwargs):
        request = original(*args, **kwargs)
        return replace(request, messages=(replace(request.messages[0], content='new policy'), *request.messages[1:]))
    monkeypatch.setattr(screen, 'make_request', changed)
    with pytest.raises(ValueError, match='closed_public_request_reconstruction_changed'):
        screen.source_inputs()
