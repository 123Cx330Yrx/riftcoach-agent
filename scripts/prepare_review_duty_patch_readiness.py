"""Read-only readiness audit with one create-only output; no package, grant or run."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import digest
from scripts import review_duty_patch_execution as execution
from scripts.review_duty_patch_launch import _launch as launch
from scripts.prepare_review_duty_execution import load_inputs, SOURCE
from scripts.codex_review_event_source import CodexReadOnlyClient
from scripts.run_boundary_examples_v2 import verify_native_principals


def prepare():
    if launch.RUN.exists() or launch.RUN.is_symlink() or launch.PACKAGE.exists() or launch.PACKAGE.is_symlink():
        raise ValueError('readiness_requires_no_business_package_or_run')
    inputs = load_inputs()
    plan = execution.preparation(inputs, primary=launch.PRIMARY, independent=launch.INDEPENDENT)
    startup = launch.startup(dict(python=sys.executable, cwd=str(launch.ROOT)))
    try:
        with CodexReadOnlyClient(launch.CODEX) as client:
            native = verify_native_principals(client, plan)
    except Exception as error:
        native = dict(verified=False, error_type=type(error).__name__)
    history = launch.ROOT/'data/evaluation/results/review_duty_chain_close_audit_20261014.json'
    audit = json.loads(history.read_bytes())
    frozen = {}
    for field in ('frozen_source_sha256', 'package_file_sha256', 'original_file_sha256'):
        for name, pin in audit[field].items():
            path = Path(name)
            if not path.is_absolute():
                path = launch.ROOT/path
            if execution.sha(path) != pin:
                raise ValueError('readiness_historical_pin_changed')
        frozen[field] = dict(count=len(audit[field]), unchanged=True)
    return dict(kind='direct-patch-readonly-readiness-v1', checked_at=datetime.now(timezone.utc).isoformat(),
        implementation_base_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=launch.ROOT, text=True).strip(),
        execution_head=None, plan=plan, plan_sha256=hashlib.sha256(execution.canonical_json(plan)).hexdigest(),
        input_snapshot=dict(path=SOURCE, sha256=execution.sha(launch.ROOT/SOURCE),
            full_input_sha256=digest(inputs.data_json), report_sha256=digest(inputs.source.report),
            historical_opinions_or_labels_supplied=False),
        source_sha256=launch.source_inventory(), startup=startup, native_preflight=native,
        historical_audit=dict(path=str(history), sha256=execution.sha(history), verified=frozen),
        budget=dict(maximum_calls=4, glm_high=4, flash_high=0, maximum_tokens=387072,
            maximum_active_seconds=2400, maximum_host_seconds=86400, per_request_seconds=600,
            per_request_output_tokens=32768, uncached_cny='5.718016', hard_billing_cap=False),
        stage_order=['facts-initial', 'completion-initial', 'compatibility', 'edit', 'application',
            'facts-fresh', 'completion-fresh'],
        implemented_layers=['Guarded isolated worker', 'Single claim and Host mailbox',
            'Four shared-budget requests and unique application', 'Strict phase reconstruction and external seal'],
        remaining_dependencies=['New create-only business package/preparation and exact source freeze',
            'Public CI green for the eventual clean exact execution HEAD',
            'New explicit paid grant bound to that preparation; old grants cannot apply',
            'Immediate native/path preflight and complete actual review of each dispatched checkpoint'],
        provider_calls=0, new_host_tasks=0, business_package_created=False,
        execution_ready=False, execution_authorized=False, production_admitted=False,
        live_quality_proven=False, natural_task_call_count=6, production_call_limit=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    output = parser.parse_args().output.absolute()
    if output.resolve() != output or output.is_relative_to(launch.ROOT/'data/runs') or output.is_relative_to(launch.PACKAGE):
        raise ValueError('readiness_output_path')
    if output.exists():
        raise FileExistsError(output)
    record = prepare()
    write_new_json(output, record)
    print(json.dumps(dict(output=str(output), sha256=execution.sha(output),
        source_files=len(record['source_sha256']), native_verified=record['native_preflight']['verified'],
        execution_ready=False, execution_authorized=False), ensure_ascii=True))


if __name__ == '__main__':
    main()
