"""Pin a zero-network development-core preparation; not a paid executable package."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from app.evaluation.golden_journal import write_new_json
from app.evaluation.review_bound_qualification import frozen_cases
from scripts import review_duty_execution as execution
from scripts.review_duty_host_gate import sha

ROOT = execution.ROOT
SOURCE = 'data/evaluation/fixtures/document_review_duty_followup_20261014/duty-3-facts-initial/material.json'
AUDIT = 'data/evaluation/results/document_review_duty_followup_close_audit_20261014.json'


def prepare():
    audit = json.loads((ROOT/AUDIT).read_bytes())
    expected = {Path(p):v for p,v in audit['package_file_sha256'].items()}
    material_path = ROOT/SOURCE
    if sha(material_path) != expected[material_path]:
        raise ValueError('duty_execution_source_snapshot_changed')
    material = json.loads(material_path.read_bytes())
    source = next(s for c,s in frozen_cases()[0] if c['key']==material['source_key'])
    inputs = execution.duty.TimedDocumentWorkflow.build_inputs(replace(source,report=material['report']))
    if inputs.data_json != material['current_input_json']:
        raise ValueError('duty_execution_full_input_changed')
    plan = execution.preparation(inputs,primary='01a1248f-e18c-7282-92bf-7ceb2eb5dce4',
        independent='01a12f0c-bb7c-74e3-ad92-775eefbe399a')
    return dict(kind='complementary-review-development-core-preparation-v1',plan=plan,
        plan_sha256=__import__('hashlib').sha256(execution.canonical_json(plan)).hexdigest(),
        input_snapshot=dict(path=SOURCE,sha256=sha(material_path),source_key=material['source_key'],
            provenance='Reuse complete input only; no historical Provider opinion or Host label supplied.'),
        source_sha256={p:sha(ROOT/p) for p in ('scripts/prepare_review_duty_execution.py',
            'tests/test_review_duty_execution.py',*plan['source_sha256'])},
        provider_calls=0,new_host_tasks=0,production_admitted=False,
        execution_ready=False,execution_authorized=False,
        remaining_execution_dependencies=['Real observed worker/transport adapter with source-bound child startup',
            'Cross-process strict read-only replay and create-only seal',
            'Pinned new authorization, same-head public CI, native and cwd/Python preflight'],
        estimates=dict(maximum_calls=5,glm_high=4,flash_high=1,maximum_tokens=483840,
            maximum_active_seconds=2700,maximum_host_seconds=86400,uncached_cny='5.8609664',hard_billing_cap=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    output=args.output.resolve()
    if output.is_relative_to(ROOT/'data/runs'):
        raise ValueError('duty_execution_preparation_outside_runs')
    result=prepare()
    write_new_json(output,result)
    print(json.dumps(dict(plan_sha256=result['plan_sha256'],provider_calls=0,execution_ready=False),ensure_ascii=True))
