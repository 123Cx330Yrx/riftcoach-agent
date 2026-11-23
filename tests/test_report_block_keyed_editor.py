"""Offline protocol/consumer checks; scripted replies are not live quality."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from app.evaluation import review_bound_editor as baseline
from app.evaluation.golden_coarse_source_projection import VERSION as PROJECTION
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.source_patch_editor import report_inputs
from app.harness.steps import RevisionRequest
from app.providers.models import ChatMessage, ChatRequest, ChatResponse, MessageRole, TokenUsage, ToolCall
from app.runtime.coach_contract import DOCUMENT_REVIEW_COACH_CONTRACT
from app.runtime.document_review_roles import DocumentRoleRoutedProvider
from app.runtime.review_sender import SharedBudgetReviewSender
from app.runtime.runtime import _ReceiptForwardingCoachBudgetedProvider
from scripts import report_block_keyed_editor as candidate
from scripts.audit_editor_protocol import sdk_projection
from tests.test_coarse_revision_editor import cases, BEFORE, AFTER
from tests.test_reviewer_role_proposal import providers


def change(before=BEFORE, after=AFTER):
    return dict(before=before, after=after, reason='Synthetic necessary edit; not semantic evidence.')


def exchange(request, edits):
    response = ChatResponse(provider='zhipu', model='glm-5.3-flash', content=None, finish_reason='tool_calls',
        tool_calls=(ToolCall(id='scripted-edit', name=candidate.TOOL, arguments=dict(edits=edits)),),
        usage=TokenUsage(input_tokens=10, output_tokens=10))
    return Exchange(request, response, hashlib.sha256(validate_request(request,
        transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())


def test_schema_and_sdk_keep_explicit_selectors_and_complete_sources():
    _, inputs, accepted, _ = cases()['claim-scope:4']
    request = candidate.edit_request(inputs, accepted)
    assert request.messages[1:] == baseline.edit_request(inputs, accepted).messages[1:]
    schema = request.tools[0].input_schema
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    validator.validate(dict(edits={'block_4': [change()]}))
    assert list(validator.iter_errors(dict(edits=[change()])))
    assert list(validator.iter_errors(dict(edits={'block_04': [change()]})))
    assert list(validator.iter_errors(dict(edits={'block_4': []})))
    assert sdk_projection(request)['tools'][0]['function']['parameters'] == schema
    assembly = candidate.inspect_exchange(request, exchange(request, {'block_4': [change()]}), inputs, accepted)
    assert assembly.report == inputs.source.report.replace(BEFORE, AFTER)
    assert assembly.journal['raw'] == json.dumps({'edits': {'block_4': [change()]}},
        ensure_ascii=False, separators=(',', ':'))
    assert assembly.journal['review_source_context']['accepted_review'] == accepted.model_dump(mode='json')
    assert assembly.journal['full_final_review_required'] and not assembly.journal['semantic_approval']


def test_same_anchor_in_two_blocks_can_explicitly_edit_only_the_second():
    _, inputs, accepted, _ = cases()['claim-scope:4']
    # Complete-report copies with a repeated sentence; old source stays intact.
    report = inputs.source.report
    a, b = [text for _, text in inputs.source.blocks
        if not text.lstrip().startswith(('#', '|'))][2:4]
    repeated = '重复文本定位反例。'
    altered = report.replace(a, a + repeated, 1).replace(b, b + repeated, 1)
    copied = report_inputs(inputs, altered)
    first, second = [n for n, (_, text) in enumerate(copied.source.blocks, 1) if repeated in text]
    request = candidate.edit_request(copied, accepted)
    assembly = candidate.inspect_exchange(request,
        exchange(request, {f'block_{second}': [change(repeated, '仅第二处被修改。')]}), copied, accepted)
    assert repeated in report_inputs(copied, assembly.report).source.blocks[first - 1][1]
    assert '仅第二处被修改。' in report_inputs(copied, assembly.report).source.blocks[second - 1][1]
    assert assembly.journal['operations'][0]['block'] == second


def test_more_than_eight_block_changes_still_use_one_tool_submission():
    _, inputs, accepted, _ = cases()['claim-scope:4']
    report = inputs.source.report
    selected = [text for _, text in inputs.source.blocks if not text.lstrip().startswith(('#', '|'))][:10]
    assert len(selected) == 10
    for i, text in enumerate(selected):
        report = report.replace(text, text + f' 离线旧记号{i}。', 1)
    copied = report_inputs(inputs, report)
    edits = {}
    for n, (_, text) in enumerate(copied.source.blocks, 1):
        for i in range(10):
            if f'离线旧记号{i}。' in text:
                edits[f'block_{n}'] = [change(f'离线旧记号{i}。', f'离线新记号{i}。')]
    request = candidate.edit_request(copied, accepted)
    reply = exchange(request, edits)
    assembly = candidate.inspect_exchange(request, reply, copied, accepted)
    assert len(reply.response.tool_calls) == 1 and len(assembly.journal['operations']) == 10
    assert all(f'离线新记号{i}。' in assembly.report for i in range(10))


@pytest.mark.parametrize('fault', ['unknown', 'noncanonical', 'empty_group', 'anchor',
    'overlap', 'extra_field', 'noop', 'citation', 'receipt', 'model', 'old_tool', 'metadata'])
def test_invalid_selection_or_binding_is_never_guessed_or_applied(fault):
    _, inputs, accepted, _ = cases()['claim-scope:4']
    request = candidate.edit_request(inputs, accepted)
    edits = {'block_4': [change()]}
    if fault == 'unknown': edits = {'block_64': [change()]}
    if fault == 'noncanonical': edits = {'block_04': [change()]}
    if fault == 'empty_group': edits = {'block_4': []}
    if fault == 'anchor': edits['block_4'][0]['before'] = 'not present'
    if fault == 'overlap': edits['block_4'].append(deepcopy(edits['block_4'][0]))
    if fault == 'extra_field': edits['block_4'][0]['block'] = 4
    if fault == 'noop': edits['block_4'][0]['after'] = BEFORE
    if fault == 'citation': edits['block_4'][0]['after'] += ' [K9999]'
    reply = exchange(request, edits)
    if fault == 'receipt': reply = replace(reply, receipt_request_sha256='0' * 64)
    if fault == 'model': reply = replace(reply, response=replace(reply.response, model='glm-5.3'))
    if fault == 'old_tool': reply = replace(reply, response=replace(reply.response,
        tool_calls=(replace(reply.response.tool_calls[0], name=baseline.TOOL),)))
    if fault == 'metadata': reply = exchange(replace(request, metadata={**request.metadata, 'unexpected': True}), edits)
    with pytest.raises(ValueError): candidate.inspect_exchange(request, reply, inputs, accepted)


def test_duplicate_inside_selected_block_and_source_drift_are_rejected():
    _, inputs, accepted, _ = cases()['claim-scope:4']
    block = inputs.source.blocks[3][1]
    copied = report_inputs(inputs, inputs.source.report.replace(block, block + BEFORE, 1))
    request = candidate.edit_request(copied, accepted)
    with pytest.raises(ValueError, match='anchor_not_unique'):
        candidate.inspect_exchange(request, exchange(request, {'block_4': [change()]}), copied, accepted)
    request = candidate.edit_request(inputs, accepted)
    with pytest.raises(ValueError):
        candidate.inspect_exchange(request, exchange(request, {}),
            replace(inputs, data_json=inputs.data_json.replace('869.5', '999.5')), accepted)


def test_closed_missing_block_response_is_not_converted_to_candidate_success():
    path = Path('data/evaluation/results/golden_document_remaining_checkpoint_tails_result_20261009.json')
    original = path.read_bytes()
    assert hashlib.sha256(original).hexdigest() == '4628e972c6b2b0015e31454a38724f73319e660ed807a62611fd613ddfbad0c5'
    saved = json.loads(original)['public_json_contents']
    response = saved['claim-scope-6/revision/response.json']
    arguments = response['tool_calls'][0]['arguments']
    assert 'block' not in arguments['edits'][0]
    with pytest.raises(ValueError): baseline.Changes.model_validate(arguments, strict=True)
    with pytest.raises(ValueError): candidate.BlockChanges.model_validate(arguments, strict=True)
    assert path.read_bytes() == original


def test_original_global_operation_cap_cannot_be_multiplied_by_block_groups():
    _, inputs, accepted, _ = cases()['claim-scope:4']
    # Distinct one-character anchors allow a real nonoverlapping boundary test.
    marks = ''.join(chr(0xE000 + i) for i in range(513))
    assert not set(marks).intersection(inputs.source.report)
    a, b = [text for _, text in inputs.source.blocks
        if not text.lstrip().startswith(('#', '|'))][2:4]
    copied = report_inputs(inputs, inputs.source.report.replace(a, a + marks[:512], 1)
        .replace(b, b + marks[512:], 1))
    first, second = [n for n, (_, text) in enumerate(copied.source.blocks, 1)
        if marks[0] in text or marks[-1] in text]
    request = candidate.edit_request(copied, accepted)
    edits = {f'block_{first}': [change(c, 'a') for c in marks[:512]]}
    assembly = candidate.inspect_exchange(request, exchange(request, edits), copied, accepted)
    assert len(assembly.journal['operations']) == 512
    edits[f'block_{second}'] = [change(marks[-1], 'a')]
    with pytest.raises(ValueError, match='operation_limit'):
        candidate.inspect_exchange(request, exchange(request, edits), copied, accepted)


@pytest.mark.parametrize('mode', ['pass', 'reject_fresh', 'bad_edit', 'empty_edit'])
def test_real_workflow_shared_five_call_budget_and_exact_complete_fresh(monkeypatch, mode):
    run_flow(monkeypatch, mode)


def run_flow(monkeypatch, mode, *, workflow_type=candidate.BlockKeyedDocumentWorkflow,
        router_type=DocumentRoleRoutedProvider, contract=DOCUMENT_REVIEW_COACH_CONTRACT):
    req, inputs, _, raw = cases()['claim-scope:4']
    generator, reviewer = providers()
    seen, recorded = [], []
    def generate(request):
        if request.metadata.get('harness_step') == 'revise':
            edits = {} if mode == 'empty_edit' else {'block_4': [change()]}
            if mode == 'bad_edit': edits['block_4'][0]['before'] = 'not present'
            ex = exchange(request, edits)
        else:
            ex = replace(exchange(request, {}), response=ChatResponse(provider='zhipu',
                model='glm-5.3-flash', content='scripted generation', finish_reason='stop',
                usage=TokenUsage(input_tokens=10, output_tokens=10)))
        generator.last_exchange = ex
        return ex.response
    def review(request):
        seen.append(request)
        args = json.loads(raw) if len(seen) == 1 else dict(score=96, verdict='pass',
            issues=[], issue_resolutions=[], advisories=[])
        if len(seen) > 1 and mode == 'reject_fresh':
            args = dict(json.loads(raw), score=40, verdict='fail')
        ex = exchange(request, {})
        response = replace(ex.response, model='glm-5.3', tool_calls=(ToolCall(
            id='scripted-review', name='submit_report_review', arguments=args),))
        reviewer.last_exchange = replace(ex, response=response)
        return response
    monkeypatch.setattr(generator, 'chat', generate)
    monkeypatch.setattr(reviewer, 'chat', review)
    router = router_type(generator, reviewer, source_projection=PROJECTION)
    budget = _ReceiptForwardingCoachBudgetedProvider(router, coach_contract=DOCUMENT_REVIEW_COACH_CONTRACT)
    if contract is not DOCUMENT_REVIEW_COACH_CONTRACT:
        contract.require_provider(router)
        budget.contract = contract  # Test run only; no registry/default mutation.
    for n in (1, 2):
        budget.chat(ChatRequest(messages=(ChatMessage(role=MessageRole.USER, content='scripted generation'),),
            max_tokens=32768, timeout_s=300, metadata={'agent_loop_iteration': n}))
    flow = workflow_type(SharedBudgetReviewSender(budget),
        record=lambda *args: recorded.append(args))
    first = flow.evaluate(req)
    revision = RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, first)
    if mode == 'bad_edit':
        with pytest.raises(ValueError, match='anchor_not_unique'): flow.revise(revision)
        assert budget.calls == 4 and flow.stopped and len(seen) == 1
        assert flow.last_edit_journal is None and len(recorded) == 2
        with pytest.raises(ValueError): flow.revise(revision)
        assert budget.calls == 4
        return
    draft = flow.revise(revision)
    result = flow.evaluate(replace(req, report=draft.report))
    assert result.verdict.value == ('fail' if mode == 'reject_fresh' else 'pass')
    assert budget.calls == 5 and budget.reserved_tokens == 0
    expected = req.report if mode == 'empty_edit' else req.report.replace(BEFORE, AFTER)
    assert draft.report == expected
    prepared = workflow_type.make_request(report_inputs(inputs, expected))
    issued_metadata = dict(seen[-1].metadata)
    assert issued_metadata.pop('coach_budget_contract') == 'coach-bounded-review-v2'
    assert replace(seen[-1], metadata=issued_metadata) == prepared
    assert flow.last_edit_journal['final_review_request_sha256'] == candidate.request_sha(prepared)
    assert flow.last_edit_journal['final_review_receipt_request_sha256'] == candidate.request_sha(seen[-1])
    assert not flow.last_edit_journal['semantic_approval']
    with pytest.raises(ValueError): flow.revise(revision)
    assert budget.calls == 5
    return flow
