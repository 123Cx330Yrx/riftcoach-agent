"""Frozen actual initial review followed by bounded offline provider doubles."""
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_journal import write_new_json
from app.evaluation.role_qualification import frozen_cases
from app.providers.models import ChatResponse, TokenUsage
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts import run_coarse_revision_tail as runner
from tests.test_role_review_notes import tool_response, request_data


def test_fixture_preserves_actual_review_and_editor_sources():
    plan,prepared=runner.prepare()
    source,response,initial,editor=prepared
    assert plan['initial_review_accepted'] and plan['offline_initial_injections']==1
    assert request_data(editor)['accepted_review']['issues']==response.tool_calls[0].arguments['issues']
    assert request_data(editor)['accepted_review']['issues'][0]['source_ids']==[27,38,39]
    assert 'table_rows_by_id' in request_data(editor)['source_index']
    assert not {'previous_review','advisories'} & request_data(editor)['accepted_review'].keys()
    assert not plan['actual_product_task_qualified'] and not plan['production_admitted']


def test_unregistered_runtime_stops_before_preparation_or_credentials(monkeypatch):
    monkeypatch.setattr(runner,'prepare',lambda:pytest.fail('unregistered execution reached preparation'))
    with pytest.raises(ValueError,match='runtime_contract_not_registered'):
        runner.run(NS(execute=True))


def test_old_product_router_cannot_silently_accept_new_projection():
    from app.runtime.reviewer_roles import role_for_request
    _,prepared=runner.prepare()
    for request in prepared[2:]:
        with pytest.raises(ValueError,match='source_projection_required'):
            role_for_request(request)


@pytest.mark.parametrize('failure',[None,'hash','defects','disagreement'])
def test_file_host_requires_bound_independent_review(tmp_path,failure):
    stage=tmp_path/'revision.json'
    stage.write_text('{"report":"offline"}')
    other=dict(stage='revision',response_sha256=runner.sha(stage),accepted=True,defects=[],source_review='Complete offline source comparison.')
    if failure=='hash': other['response_sha256']='0'*64
    if failure=='defects': other['defects']=['unsupported claim']
    if failure=='disagreement': other['accepted']=False
    independent=tmp_path/'revision-independent.json'
    write_new_json(independent,other)
    decision=dict(stage='revision',response_sha256=runner.sha(stage),accepted=True,defects=[],
        source_review='Primary offline inspection.',independent_sha256=runner.sha(independent))
    write_new_json(tmp_path/'revision-host-decision.json',decision)
    if failure is None:
        assert runner.adjudicate_file(stage,5)['accepted']
    else:
        with pytest.raises(ValueError,match='host_binding'): runner.adjudicate_file(stage,5)
