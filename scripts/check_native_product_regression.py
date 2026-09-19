"""Reproduce the saved attribution miss and input sizes without Provider I/O.

This measures protocol acceptance, not semantic correctness. Both full reports
keep the original sources; source-binding repairs have separate pipeline tests.
"""
import json
from pathlib import Path
from decimal import Decimal

from app.evaluation import golden_native_issues_review as native
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from app.evaluation.golden_review_experiment import digest
from app.harness.steps import EvaluationRequest, KnowledgeEvidence, KnowledgeCitation

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / 'data/evaluation/datasets/golden_native_product_attribution_controls_v1.json'


def inspect():
    import hashlib
    data = json.loads(DATASET.read_text(encoding='utf-8'))
    artifact = ROOT / data['origin_artifact']
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == data['origin_artifact_sha256']
    original = json.loads(artifact.read_text(encoding='utf-8'))
    sources = {}
    for item in data['source_files']:
        path = ROOT / item['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
        sources[path.name] = path.read_text(encoding='utf-8')
    summary = json.loads(sources['player_summary.json'])
    raw = json.loads(sources['retrieval_evidence.json'])
    knowledge = KnowledgeEvidence(context=raw['context'], source_ids=tuple(raw['source_ids']),
        citations=tuple(KnowledgeCitation(**c) for c in raw['citations']), abstained=raw['abstained'])
    rows = summary['matches']
    mean = lambda values: sum(values) / Decimal(len(values))
    wins = mean([Decimal(str(r['damage_per_min'])) for r in rows if r['win']])
    losses = mean([Decimal(str(r['damage_per_min'])) for r in rows if not r['win']])
    mid_losses = mean([Decimal(str(r['damage_per_min'])) for r in rows if not r['win'] and r['role'] == 'MIDDLE'])
    # This independent arithmetic contradicts the original 'mainly support' claim.
    assert wins-mid_losses > (wins-losses)*Decimal('0.95')
    cases = []
    for case in data['cases']:
        assert digest(case['report']) == case['report_sha256']
        assert case['report'].count(case['target']) == 1
        req = EvaluationRequest(summary, sources['deterministic_report.md'], knowledge,
                                case['report'], data['user_utterance'])
        inputs = native.build_inputs(req)
        ceiling = estimate_runtime_request_input_ceiling(native.request(inputs))
        assert ceiling <= 63936
        # Preserve and reproduce the observed false negative. Never relabel it
        # as a semantic pass just because the response satisfies the wire schema.
        observed = native.validate(original['responses'][-1]['content'], inputs)[0]
        cases.append(dict(id=case['id'], input_ceiling=ceiling, expected_report=case['expected_report'],
                          original_review_wire_verdict=observed.verdict,
                          fresh_model_judgment=False))
    return dict(scope='offline_saved_false_negative_and_regression_inputs', cases=cases,
        damage_gap_all=str(wins-losses), damage_gap_mid=str(wins-mid_losses),
        removed_support_change=str(mid_losses-losses), semantic_fix_proven=False,
        new_provider_calls=0, labels_sent_to_model=False)


if __name__ == '__main__':
    print(json.dumps(inspect(), ensure_ascii=False, indent=2))
