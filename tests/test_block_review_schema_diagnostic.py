import json

import pytest

from app.providers.models import TokenUsage
from app.providers.stream_adapter_contract import ProviderStreamAssembler, ProviderStreamEvent, StreamToolCallDelta, StreamAdapterError
from scripts import diagnose_block_review_schema as diagnostic


def test_intervention_removes_only_duplicate_notation_from_both_complete_inputs():
    variants, plan = diagnostic.prepare()
    assert len(variants) == 2 and plan['full_reservation'] <= 401920
    assert variants[0][1].messages[0] == variants[1][1].messages[0]
    for _, request, inputs in variants:
        base = diagnostic.base.review.request(inputs)
        assert request.tools == base.tools and request.messages[0] == base.messages[0]
        assert request.messages[2:] == base.messages[2:]
        header = diagnostic.base.review.native.schema_notation(base.tools[0].input_schema) + '\n'
        assert header + request.messages[1].content == base.messages[1].content
        assert request.messages[1].content.startswith('[UNTRUSTED DATA]')
        assert request.timeout_s == base.timeout_s and request.max_tokens == base.max_tokens


def test_actual_terminal_fragments_reproduce_duplicate_member_rejection():
    evidence = json.loads((diagnostic.base.ROOT / 'data/evaluation/results/golden_block_tool_argument_result_1f75120.json').read_text(encoding='utf-8'))
    output = evidence['rejected_output']
    assembler = ProviderStreamAssembler(provider_id='zhipu', requested_model='glm-5.3-flash')
    for tool in output['tools']:
        for fragment in tool['argument_parts']:
            assembler.accept(ProviderStreamEvent(model='glm-5.3-flash', tool_call_deltas=(StreamToolCallDelta(
                index=tool['index'], call_id=tool['id'], name=tool['name'], arguments_delta=fragment),)))
    assembler.accept(ProviderStreamEvent(model='glm-5.3-flash', finish_reason='tool_calls', usage=TokenUsage(**output['usage'])))
    assembler.mark_exhausted()
    with pytest.raises(StreamAdapterError, match='tool_call_arguments'):
        assembler.finalize()
    assert assembler.rejected_tool_arguments() == output
    # A permissive decoder silently keeps the second advisory value. This is
    # why normalizing duplicates would be a behavioral change, not a safe fix.
    parsed = json.loads(evidence['raw_arguments'])
    assert parsed['reviews'][16]['advisories']
    assert evidence['offline_replay']['conflicting_duplicate_member_count'] == 1
