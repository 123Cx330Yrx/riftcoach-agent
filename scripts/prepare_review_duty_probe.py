"""Create-only, offline material for a proposed review-duty comparison.

No provider, credentials, transport, authorization, Host dispatch or run is
created here. These partial-scope requests are NOT product review requests.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.evaluation.document_review_timing_adapter import role_for_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from app.evaluation.golden_stream_bridge import REQUEST
from app.runtime.coach_contract import DOCUMENT_REVIEW_COACH_CONTRACT
from scripts.audit_full15_repair_readiness import SEAL, SEAL_SHA

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'OFFLINE-review-duty-probe-v1'
CASES = (('claim-scope:4', 'initial'), ('scope:3', 'final'), ('scope:4', 'initial'))

# Exact clause replacements expose the treatment for inspection. No case,
# paragraph, number, expected answer or historical Host opinion is inserted.
REPLACEMENTS = (
    ('你是RiftCoach报告审查员。检查完整报告和全部来源，判断报告是否有需要修复的真实问题。',
     '你是RiftCoach报告事实审查员。检查完整报告和全部来源，只审查报告已有断言、建议及其论证的事实正确性；本次不评任务完成度。'),
    ('报告正文至少一处以实际提供且支持建议的[K编号]引用知识，不能只列来源名或随机挂编号。若无适用知识，说明不足并移除无依据建议，不编造引用。',
     '核对报告实际使用的[K编号]与建议是否有来源支持，不接受随机挂编号或编造引用；没有引用本身不在本次职责内，无依据建议仍需修正。'),
    ('对可用且匹配位置/英雄的OP.GG事实，报告至少把一项tier/rank/rate连到条件建议或待验行动，标明位置、检索时间和当前快照边界；只列数字/免责声明不算实际使用。',
     '核对报告实际使用的OP.GG事实、位置、检索时间、当前快照边界及其建议是否受来源支持；没有使用某项可用事实本身不在本次职责内。'),
    ('检查全部实际建议及其知识依据。',
     '检查全部实际建议及其知识依据，不评价建议是否足够丰富或是否完成全部用户任务。'),
    ('分数、结论和问题应一致，不为凑问题扣分。',
     '分数、结论和问题仅对应本次事实审查职责，应保持一致，不为凑问题扣分；本次pass不代表完整报告或任务通过。'),
)


def packed(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(value):
    raw = packed(value)
    result = REQUEST.validate_json(raw, strict=True)
    return replace(result, **{k: value[k] for k in ('temperature', 'timeout_s', 'top_p')})


def fact_policy(original):
    result = original
    for before, after in REPLACEMENTS:
        if result.count(before) != 1:
            raise ValueError('duty_probe_policy_drift')
        result = result.replace(before, after)
    return result


def prepare():
    original_bytes = (ROOT / SEAL).read_bytes()
    if sha(original_bytes) != SEAL_SHA:
        raise ValueError('duty_probe_seal_changed')
    public = json.loads(original_bytes)['public_json_contents']
    files, rows = {}, []
    for ordinal, (key, stage) in enumerate(CASES, 1):
        prefix = key.replace(':', '-') + '/' + stage + '/'
        baseline = public[prefix + 'issued-request.json']
        if role_for_request(decode(baseline)) != 'review':
            raise ValueError('duty_probe_baseline_not_review')
        candidate = deepcopy(baseline)
        candidate['messages'][0]['content'] = fact_policy(baseline['messages'][0]['content'])
        candidate['metadata']['offline_review_duty'] = VERSION
        # Full original report and sources, schema, parameters and teaching.
        if candidate['messages'][1:] != baseline['messages'][1:]:
            raise ValueError('duty_probe_source_or_report_changed')
        if any(candidate[k] != baseline[k] for k in baseline if k not in ('messages', 'metadata')):
            raise ValueError('duty_probe_non_policy_change')
        try:
            role_for_request(decode(candidate))
        except ValueError as exc:
            rejected_by_old_identity = str(exc)
        else:
            raise ValueError('duty_probe_partial_scope_admitted_as_full')
        for arm, request in (('full', baseline), ('facts', candidate)):
            name = f'{ordinal:02d}-{arm}.json'
            raw = packed(request)
            ceiling = estimate_runtime_request_input_ceiling(decode(request))
            if ceiling > 64000 or request['max_tokens'] != 32768 or request['timeout_s'] != 600:
                raise ValueError('duty_probe_envelope')
            files[name] = raw
            rows.append(dict(file=name, source_case=key, source_stage=stage, arm=arm,
                request_sha256=sha(raw), source_request_sha256=sha(packed(baseline)),
                non_system_messages_sha256=sha(packed(request['messages'][1:])),
                schema_sha256=sha(packed(request['tools'])),
                policy_sha256=sha(request['messages'][0]['content'].encode('utf-8')),
                estimated_input_ceiling=ceiling, output_reservation=32768,
                proposed_model='glm-5.3', proposed_reasoning='high',
                historical_full_identity_accepts=(arm == 'full'),
                rejection=None if arm == 'full' else rejected_by_old_identity))
    if (ROOT / SEAL).read_bytes() != original_bytes:
        raise ValueError('duty_probe_seal_mutated')
    input_ceiling = sum(r['estimated_input_ceiling'] for r in rows)
    # Existing diagnostic tariff assumption, not a current provider quote/bill.
    price = DOCUMENT_REVIEW_COACH_CONTRACT.pricing_profiles['zhipu', 'glm-5.3']
    estimate = lambda inputs, outputs: str((Decimal(inputs) * price.input_cost_per_million
        + Decimal(outputs) * price.output_cost_per_million) / 1000000)
    files['manifest.json'] = packed(dict(kind=VERSION, status='prepared_not_authorized_not_executable',
        seal=SEAL, seal_sha256=SEAL_SHA, requests=rows,
        source_sha256={p: sha((ROOT / p).read_bytes()) for p in (
            'scripts/prepare_review_duty_probe.py',
            'app/evaluation/document_review_timing_adapter.py',
            'app/evaluation/glm53_bounded_revision_budget_reachability.py')},
        proposed_limits=dict(glm_calls=6, flash_calls=0, request_seconds=600,
            activity_seconds=3600, host_seconds=86400, input_per_request=64000,
            output_per_request=32768, total_tokens=6 * (64000 + 32768), retries=0),
        measured_input_ceiling_sum=input_ceiling,
        measured_plus_output_reservation=input_ceiling + 6 * 32768,
        price_source='DOCUMENT_REVIEW_COACH_CONTRACT / ADR0108 snapshot, not a fresh quote',
        assumed_cny_per_million=dict(uncached_input=str(price.input_cost_per_million),
            output=str(price.output_cost_per_million)),
        measured_envelope_estimate_cny=estimate(input_ceiling, 6 * 32768),
        maximum_envelope_estimate_cny=estimate(6 * 64000, 6 * 32768),
        billing_hard_cap=False, provider_calls=0, new_host_tasks=0, new_qualification=0,
        authorized=False, execution_ready=False, product_admitted=False,
        limits=['Only duty/system and an explicit offline metadata marker change within each pair.',
            'Score/pass in the facts arm is partial-scope and cannot publish a product report.',
            'Familiar development inputs, one response per arm; no stability or holdout estimate.',
            'No execution adapter, authorization, native checkpoint or production aggregation exists.']))
    return files


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    output = parser.parse_args().output_dir.absolute()
    if output.resolve() != output or output.is_relative_to(ROOT / 'data/runs'):
        raise ValueError('duty_probe_output_must_be_outside_runs')
    files = prepare()
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        with (output / name).open('xb') as stream:
            stream.write(raw)
    print(json.dumps(dict(files=len(files), status='prepared_not_authorized', provider_calls=0)))
