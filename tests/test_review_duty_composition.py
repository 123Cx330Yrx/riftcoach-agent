"""Scripted offline contract/consumer witnesses, never model quality evidence."""
from dataclasses import replace
import re
import socket

import pytest

from app.evaluation import document_review_timing_adapter as timing
from app.evaluation.golden_explicit_source_projection import _unpack
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.source_patch_editor import report_inputs
from app.providers.models import ChatResponse, TokenUsage, ToolCall
from scripts import review_duty_composition as duty
from scripts.prepare_review_duty_probe import fact_policy
from scripts.report_timed_document_workflow import TimedDocumentWorkflow
from tests.test_coarse_revision_editor import cases, BEFORE, AFTER


PASS = compact(dict(score=95, verdict='pass', issues=[], advisories=[], issue_resolutions=[]))


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Offline duty composition cannot connect')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


@pytest.fixture(scope='module')
def sample():
    _, inputs, _, raw = cases()['claim-scope:4']
    return inputs, raw


def opinions(inputs, facts_raw, completion_raw=PASS, stage='initial'):
    return (duty.bind(inputs, 'facts', stage, facts_raw),
            duty.bind(inputs, 'completion', stage, completion_raw))


def test_complete_request_and_fact_policy_are_preserved_and_live_identity_rejects(sample):
    inputs, _ = sample
    base = TimedDocumentWorkflow.make_request(inputs)
    for name in duty.DUTIES:
        request = duty.review_request(inputs, name)
        assert request.messages[1:] == base.messages[1:]
        assert request.tools == base.tools
        assert (request.temperature, request.top_p, request.max_tokens, request.timeout_s) == (1, .95, 32768, 600)
        with pytest.raises(ValueError):
            timing.request_bytes(request)
    assert duty.review_request(inputs, 'facts').messages[0].content == fact_policy(base.messages[0].content)


def test_missing_citation_is_not_a_fact_only_gate_but_unknown_citation_remains_one(sample):
    inputs, _ = sample
    no_citation = report_inputs(inputs, re.sub(r'\[K\d+\]', '', inputs.source.report))
    with pytest.raises(ValueError, match='missing_knowledge_citation'):
        TimedDocumentWorkflow.validate_review(PASS, no_citation)
    assert duty.validate(PASS, no_citation, 'facts').verdict == 'pass'
    # A legal completion pass does not certify that the omission was justified.
    state = duty.pair(no_citation, opinions(no_citation, PASS), 'initial')
    assert state['all_duties_pass'] and not state['semantic_approval'] and not state['production_admitted']
    unknown = report_inputs(inputs, inputs.source.report + '\n\n[K9999]')
    with pytest.raises(ValueError, match='unknown_knowledge_citation'):
        duty.validate(PASS, unknown, 'facts')


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'report', 'input', 'request', 'stage'])
def test_pair_cannot_mix_reports_sources_duties_requests_or_stages(sample, fault):
    inputs, raw = sample
    pair = list(opinions(inputs, raw))
    if fault == 'missing': pair.pop()
    elif fault == 'duplicate': pair[1] = pair[0]
    elif fault == 'report': pair[1] = replace(pair[1], report_sha256='0' * 64)
    elif fault == 'input': pair[1] = replace(pair[1], input_sha256='0' * 64)
    elif fault == 'request': pair[1] = replace(pair[1], request_sha256='0' * 64)
    elif fault == 'stage': pair[1] = replace(pair[1], stage='fresh')
    with pytest.raises(ValueError, match='duty_pair'):
        duty.pair(inputs, pair, 'initial')


@pytest.mark.parametrize('fault', ['source', 'block', 'advisory', 'pass_with_issue', 'revision_empty', 'resolution', 'injection'])
def test_invalid_wire_source_and_security_are_not_bypassed(sample, fault):
    import json
    inputs, raw = sample
    value = json.loads(raw)
    if fault == 'source': value['issues'][0]['source_ids'] = [99999]
    elif fault == 'block': value['issues'][0]['block'] = 64
    elif fault == 'advisory': value['advisories'] = [dict(block=1), dict(block=1)]
    elif fault == 'pass_with_issue': value['verdict'] = 'pass'
    elif fault == 'revision_empty': value['issues'] = []
    elif fault == 'resolution': value['issue_resolutions'] = [dict(previous_id=1, disposition='withdrawn', final_issue=None, source_ids=[32], explanation='Synthetic invalid fresh mapping')]
    elif fault == 'injection': value['issues'][0]['category'] = 'prompt_injection'
    with pytest.raises(ValueError): duty.validate(compact(value), inputs, 'facts')


def test_two_original_opinions_reach_editor_without_verdict_merge(sample):
    import json
    inputs, raw = sample
    second = json.loads(raw)
    second['issues'][0]['explanation'] = 'Synthetic completion issue, not a GLM or Host judgment.'
    second['issues'][0]['suggested_correction'] = 'Synthetic incompatible correction retained verbatim.'
    pair = opinions(inputs, raw, compact(second))
    with pytest.raises(ValueError, match='edit_not_admissible'):
        duty.edit_request(inputs, pair, conflict_status='unassessed')
    with pytest.raises(ValueError, match='edit_not_admissible'):
        duty.edit_request(inputs, pair, conflict_status='conflict')
    # Pure caller input cannot prove semantic compatibility; never auto-publish.
    request = duty.edit_request(inputs, pair, conflict_status='clear')
    _, data = _unpack(request)
    assert 'accepted_review' not in data
    assert data['duty_reviews']['duties']['facts']['raw'] == raw
    assert data['duty_reviews']['duties']['completion']['review'] == second
    assert not data['duty_reviews']['semantic_conflict_checked']


@pytest.mark.parametrize('raw', [PASS, compact(dict(score=0, verdict='fail', issues=[], advisories=[], issue_resolutions=[]))])
def test_both_pass_skips_edit_and_terminal_never_goes_to_editor(sample, raw):
    inputs, _ = sample
    pair = opinions(inputs, raw)
    with pytest.raises(ValueError, match='edit_not_admissible'):
        duty.edit_request(inputs, pair, conflict_status='clear')


def test_actual_editor_assembly_produces_two_fresh_requests_over_new_report(sample):
    inputs, raw = sample
    pair = opinions(inputs, raw)
    request = duty.edit_request(inputs, pair, conflict_status='clear')
    response = ChatResponse(provider='zhipu', model='glm-5.3-flash', content=None, finish_reason='tool_calls',
        tool_calls=(ToolCall(id='offline-script', name='submit_block_edits', arguments=dict(edits={
            'block_4': [dict(before=BEFORE, after=AFTER, reason='Synthetic editor consumer witness.')]})),),
        usage=TokenUsage(input_tokens=10, output_tokens=10))
    exchange = Exchange(request, response, duty.request_sha(request))
    assembly = duty.inspect_edit(request, exchange, inputs, pair, conflict_status='clear')
    assert assembly.report == inputs.source.report.replace(BEFORE, AFTER)
    assert 'accepted_review' not in compact(assembly.journal)
    revised = report_inputs(inputs, assembly.report)
    for name in duty.DUTIES:
        fresh = duty.review_request(revised, name, 'fresh')
        assert assembly.journal['fresh_request_sha256'][name] == duty.request_sha(fresh)
        assert fresh.messages[1:] == TimedDocumentWorkflow.make_request(revised).messages[1:]
        assert 'duty_reviews' not in ''.join(m.content for m in fresh.messages)
    with pytest.raises(ValueError, match='duty_pair_binding'):
        duty.pair(revised, pair, 'fresh')
    after = duty.pair(revised, opinions(revised, PASS, stage='fresh'), 'fresh')
    assert after['report_sha256'] == digest(assembly.report)
    assert after['all_duties_pass'] and not after['production_admitted']
    with pytest.raises(ValueError, match='exchange_identity'):
        duty.inspect_edit(request, replace(exchange, receipt_request_sha256='0'*64), inputs, pair, conflict_status='clear')
    altered = replace(response, tool_calls=(replace(response.tool_calls[0], arguments=dict(edits={
        'block_4': [dict(before='missing anchor', after=AFTER, reason='Synthetic bad anchor.')]})),))
    with pytest.raises(ValueError, match='anchor_not_unique'):
        duty.inspect_edit(request, replace(exchange, response=altered), inputs, pair, conflict_status='clear')
