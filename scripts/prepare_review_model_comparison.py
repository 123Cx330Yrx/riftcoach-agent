"""Offline feasibility only: serialize two frozen reviews through a mock SDK.

No credentials, live transport, profile registration or execution switch. The
alternative body is a proposed wire-level comparison, not a working product
Provider. In particular the current Coach and process bridge reject that model.
"""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
from openai import OpenAI

from app.evaluation.golden_review_experiment import compact, digest
from app.providers.zhipu import ZhipuProvider
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
from scripts.diagnose_review_target_layout import prepare

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/evaluation/results/golden_review_model_comparison_feasibility_v1.json'
FROZEN = ROOT / 'data/evaluation/results/golden_review_target_layout_plan_v1.json'
ALTERNATIVE = 'glm-5.3'


def sdk_arguments(request):
    captured = []

    def create(**kwargs):
        captured.append(deepcopy(kwargs))
        return iter(())

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    provider = ZhipuProvider.from_candidate_profile(client=client, model='glm-5.3-flash',
        profile=ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE)
    provider._open_stream_for_adapter(request, tool_stream=True, include_usage_tail=True)
    if len(captured) != 1:
        raise ValueError('unexpected_sdk_submission_count')
    return captured[0]


def mock_wire(arguments):
    captured = []

    def handle(request):
        captured.append(json.loads(request.content))
        if request.url != httpx.URL('https://offline.invalid/api/paas/v4/chat/completions'):
            raise ValueError('unexpected_sdk_url')
        return httpx.Response(200, headers={'content-type': 'text/event-stream'},
            content=b'data: [DONE]\n\n')

    # MockTransport handles every request in-process. No default network client.
    with httpx.Client(transport=httpx.MockTransport(handle)) as http_client:
        with OpenAI(api_key='offline-placeholder', base_url='https://offline.invalid/api/paas/v4/',
                    http_client=http_client, max_retries=0) as client:
            stream = client.chat.completions.create(**deepcopy(arguments))
            try:
                if list(stream):
                    raise ValueError('unexpected_mock_response')
            finally:
                stream.close()
    if len(captured) != 1:
        raise ValueError('unexpected_mock_request_count')
    return captured[0]


def build_plan():
    variants, layout_plan = prepare()
    frozen = json.loads(FROZEN.read_text(encoding='utf-8'))
    if layout_plan != frozen:
        raise ValueError('frozen_review_inputs_changed')
    cells = []
    for (name, _, request), condition in zip(variants, frozen['conditions'], strict=True):
        if condition['layout'] != 'baseline':
            continue
        arguments = sdk_arguments(request)
        baseline = mock_wire(arguments)
        alternative_arguments = deepcopy(arguments)
        alternative_arguments['model'] = ALTERNATIVE
        alternative = mock_wire(alternative_arguments)
        difference = sorted(k for k in baseline.keys() | alternative.keys()
                            if baseline.get(k) != alternative.get(k))
        if difference != ['model']:
            raise ValueError('comparison_changes_more_than_model')
        if (alternative['reasoning_effort'] != 'high'
                or alternative['thinking'] != {'type': 'enabled', 'clear_thinking': False}
                or alternative['max_tokens'] != 32768
                or alternative['tool_choice'] != 'auto'
                or alternative['stream'] is not True
                or alternative['tool_stream'] is not True
                or alternative['stream_options'] != {'include_usage': True}
                or 'response_format' in alternative
                or arguments['timeout'] != 300):
            raise ValueError('review_wire_contract_changed')
        cells.append({
            'id': name, 'report_sha256': condition['report_sha256'],
            'neutral_request_sha256': condition['request_sha256'],
            'baseline_sdk_body_sha256': digest(compact(baseline)),
            'proposed_sdk_body_sha256': digest(compact(alternative)),
            'changed_sdk_fields': difference,
            'input_reservation': condition['input_ceiling'],
            'output_cap': alternative['max_tokens'],
            'messages_sha256': digest(compact(alternative['messages'])),
            'tools_sha256': digest(compact(alternative['tools'])),
            'expected_host_only': condition['expected_host_only'],
        })
    if len(cells) != 2:
        raise ValueError('expected_two_full_report_controls')
    input_total = sum(c['input_reservation'] for c in cells)
    output_total = sum(c['output_cap'] for c in cells)
    # Conservative project sizer, not a vendor-tokenizer proof or billing cap.
    cost = (Decimal(input_total) * 8 + Decimal(output_total) * 28) / 1_000_000
    return {
        'experiment': 'review-model-capability-pair-v1',
        'status': 'offline_feasibility_only',
        'production_admitted': False, 'live_entry_in_this_script': False,
        'provider_requests': 0, 'paid_usage_tokens': 0,
        'baseline_model': 'glm-5.3-flash', 'proposed_model': ALTERNATIVE,
        'reasoning_effort': 'high', 'sdk_retries': 0,
        'labels_sent_to_model': False,
        # This plan is a Git text file; hash canonical JSON so Windows CRLF
        # checkout conversion is not confused with an evidence/content change.
        'frozen_layout_plan_canonical_sha256': digest(compact(frozen)),
        'cells': cells,
        'proposed_diagnostic_budget': {
            'max_calls': 2, 'max_seconds_per_call': 300, 'max_seconds_total': 600,
            'input_reservation_total': input_total, 'output_cap_total': output_total,
            'total_token_reservation': input_total + output_total,
            'uncached_price_cny_per_million_input': '8',
            'price_cny_per_million_output': '28',
            'estimated_cny_at_reservation': str(cost),
            'cost_is_hard_billing_cap': False,
            'no_retry_reassessment_edit_or_api_warmup': True,
        },
        'product_budget_unchanged': {'calls': 5, 'tokens': 401920, 'seconds': 900, 'revisions': 1},
        'scope': 'Mock SDK proves serialization only; not API/account availability, runtime integration, model quality or adoption.',
        'baseline_evidence': 'golden_review_target_layout_result_1d5f7a2.json; historical, not contemporaneous comparative performance.',
        'implementation_dependencies_after_decision': [
            'Explicit diagnostic-only high replay profile; the existing glm-5.3 default is low.',
            'Bound model identity through request policy, process worker, assembler, receipt and response validation; do not globally relax Flash checks.',
            'One shared two-call diagnostic ledger, process deadline and known/unknown usage accounting; exact-HEAD public CI before paid calls.',
        ],
        'decision_branches': {
            'both_semantically_correct': 'Justifies evaluating reviewer role integration; not stable accuracy, causal superiority, full workflow or candidate qualification.',
            'semantic_failure': 'Reject this model-only substitution as sufficient for these controls; stop further calls and preserve every finding.',
            'protocol_or_execution_failure': 'Stop without retry, retain raw response or partial transport and known/unknown usage; semantic capability remains unknown.',
        },
    }


if __name__ == '__main__':
    result = build_plan()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': OUTPUT.as_posix(), 'cells': len(result['cells']),
        'budget': result['proposed_diagnostic_budget'], 'provider_requests': 0}, ensure_ascii=False))
