"""Offline full-report proposal: detection, correction and preservation together.

Creates author materials and prospective request bytes only, never a run,
authorization, provider response or independent calibration.
"""
import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from app.runtime.coach_contract import DOCUMENT_REVIEW_COACH_CONTRACT
from scripts.document_full_report_diagnostic import base, source_facts, source_inputs, source_payload
from scripts import document_relation_request as identity

ROOT = Path(__file__).resolve().parents[1]
SEED = 'data/evaluation/fixtures/host_relation_repair_calibration_20261012/materials.json'
SEED_SHA = '77f22cafa8f28ba3149b786f9bec6113a8a2ee857e85c0110cb9b85b0e82bac8'
MEAN_GOOD = '仅这四局中单的早期死亡胜负组均值并不接近。'
MEAN_BAD = '仅这四局中单的早期死亡胜负组均值接近。'
ORDER_GOOD = '这四局中单的胜负组补刀取值区间有重叠。'
ORDER_BAD = '这四局中单每个胜场的补刀/分钟都低于每个负场。'
CS_PARAGRAPH = ('中单补刀/分钟的胜场为8.95、8.66，负场为9.64、8.38；胜负均值为8.805、9.01。'
    + ORDER_GOOD + '全样本补刀差距受辅助局明显影响；伤害差距则在中单内部已存在，不能主要归因于辅助局。')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def prepare():
    original = (ROOT / SEED).read_bytes()
    if sha(original) != SEED_SHA:
        raise ValueError('joint_review_seed_changed')
    seed = json.loads(original)
    reference = next(c for c in seed['cases'] if c['case_id'] == 'U1')
    texts = [b['text'] for b in reference['report']]
    if len(texts) != 26 or texts[13].count(MEAN_GOOD) != 1:
        raise ValueError('joint_review_seed_shape')
    texts[14] = CS_PARAGRAPH
    artifacts, cells, reports = {}, [], {}
    for name in ('J1', 'J2'):
        blocks = list(texts)
        if name == 'J2':
            blocks[13] = blocks[13].replace(MEAN_GOOD, MEAN_BAD)
            blocks[14] = blocks[14].replace(ORDER_GOOD, ORDER_BAD)
        report = '\n\n'.join(blocks)
        reports[name] = report
        inputs = source_inputs(report)
        if [text for _, text in inputs.source.blocks] != blocks:
            raise ValueError('joint_review_full_report_binding')
        request = base.TimedDocumentWorkflow.make_request(inputs)
        request = replace(request, metadata={**request.metadata,
            'coach_budget_contract': 'coach-bounded-review-v2'})
        if (request.messages[0].content != seed['full_policy_text']
                or request.messages[3].content != reference['deterministic_source_message']
                or source_facts(source_payload(request.messages[2].content)) !=
                   source_facts(source_payload(reference['source_message']))):
            raise ValueError('joint_review_sources_or_policy_changed')
        current = json.loads(inputs.data_json)
        prior = json.loads(reference['current_input_json'])
        for value in (current, prior):
            del value['source_index']['blocks'], value['source_index']['source_digest']
        if current != prior:
            raise ValueError('joint_review_nonreport_input_changed')
        for variant in identity.VARIANTS:
            prepared = identity.prepare_request(request, variant)
            if identity.projection(prepared) != request:
                raise ValueError('joint_review_pair_changed')
            key = f'{name}-{variant}-initial'
            raw = identity.request_bytes(prepared)
            material = dict(report_origin='Author-created familiar-source development report; no independent calibration.',
                report=report, current_input_json=inputs.data_json,
                full_policy_text=prepared.messages[0].content,
                source_message=prepared.messages[2].content,
                deterministic_source_message=prepared.messages[3].content)
            artifacts[f'{key}/material.json'] = encode(material)
            artifacts[f'{key}/prepared-request.json'] = raw
            cells.append(dict(key=key, request_sha256=sha(raw), report_sha256=sha(report.encode()),
                material_sha256=sha(encode(material)), actual_blocks=26,
                input_ceiling=estimate_runtime_request_input_ceiling(prepared),
                stage='initial', report_assessment=None))
    if reports['J2'].replace(MEAN_BAD, MEAN_GOOD, 1).replace(ORDER_BAD, ORDER_GOOD, 1) != reports['J1']:
        raise ValueError('joint_review_pair_not_minimal')
    # These expectations stay outside every Provider/Host material. They are
    # author claims awaiting whole-document independent calibration.
    expectations = dict(origin='primary_author_expectations_not_independent_verdicts',
        J1=dict(blocking_issues=[], requirement='Preserve all supported content; review the entire report.'),
        J2=dict(blocking_issues=[14, 15], checks=[
            'Detect the middle-cohort mean proximity error; retain whole-five-game 2.50/2.67.',
            'Detect false all-win-below-all-loss CS claim: both 8.95 and 8.66 exceed losing 8.38.',
            'CS win mean remains below loss mean; do not reverse it or claim all wins are higher.',
            'Repair suggestions must not deny early-death sample separation or introduce causality.',
            'Review every other assertion, reference, explanation, correction and advisory.']),
        grading=dict(detection='Record each genuine issue separately; empty issues on J2 is missed_error.',
            correction='Assess every returned correction separately; absent correction is not a successful repair.',
            preservation='Assess all correct content in both documents, including optional advice.',
            inference='Any candidate error rejects this candidate on this scope; both pass/no baseline failure gives no improvement evidence.'))
    artifacts['operator-expectations.json'] = encode(expectations)
    price = DOCUMENT_REVIEW_COACH_CONTRACT.pricing_profiles['zhipu', 'glm-5.3']
    cost = 4 * (Decimal(64000) * price.input_cost_per_million +
                Decimal(32768) * price.output_cost_per_million) / 1_000_000
    proposal = dict(kind='OFFLINE-joint-relation-proposal-v1',
        execution_authorized=False, execution_ready=False, independent_calibration=False,
        provider_calls=0, http_calls=0, native_tasks=0, business_submissions=0, new_qualification=0,
        seed_path=SEED, seed_sha256=SEED_SHA, cells=cells,
        report_delta_blocks=[14, 15], complete_sources_and_nonreport_inputs_preserved=True,
        teaching_delta_unchanged=True, familiar_sources_not_holdout=True,
        proposed_budget=dict(max_calls=4, glm53_high=4, flash=0, max_tokens=387072,
            max_active_seconds=2400, max_host_seconds=86400, per_request_seconds=600,
            per_request_output=32768, estimated_uncached_cny=str(cost), hard_billing_cap=False),
        uncompleted_execution_requirements=[
            'Independent full-document calibration of these new exact materials; old U1/U2 calibration does not transfer.',
            'New dedicated runner identity, authorization version and operator/run paths; do not feed old closed entrypoints.',
            'Observed transport, outside-run author answers, inventory checks and real native imports verified on the new adapter.',
            'Concrete new cost authorization; clean frozen HEAD, its green CI and unchanged source/package hashes.',
            'Immediate native capacity/identity and absolute cwd/Python startup checks; no old task resume or recertification.'],
        excluded=['No actual generation/edit/final, retries, redelivery, old batch reopening or product qualification.',
            'No model internal-root-cause or generalization claim.',
            'No payload or task containing operator-expectations.json.'])
    proposal['artifact_sha256'] = {p: sha(raw) for p, raw in artifacts.items()}
    if (ROOT / SEED).read_bytes() != original:
        raise ValueError('joint_review_seed_changed_after_read')
    artifacts['proposal.json'] = encode(proposal)
    return proposal, artifacts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    proposal, artifacts = prepare()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for relative, raw in artifacts.items():
        path = args.output_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    print(json.dumps(dict(cells=len(proposal['cells']), execution_ready=False, provider_calls=0)))
