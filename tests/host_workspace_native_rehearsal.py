"""Explicitly synthetic transport + real native Host integration rehearsal.

Not a paid entrypoint. No credentials, SDK, model HTTP, old run reads or old
case resends. All transport records are OFFLINE test fixtures; only the Host
author and native importer are real. The outer audit must report actual project
Provider/HTTP/tokens as zero, separately from inner fixture accounting.
"""
import argparse
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import socket
import subprocess
import sys

from scripts.document_sampling_screening import load_private

ROOT = Path(__file__).resolve().parents[1]
adapter = load_private(ROOT / 'scripts/document_full_report_workspace.py',
                       'scripts._native_workspace_rehearsal')
base, diagnostic = adapter.base, adapter.diagnostic
base.VERSION = base.runner.VERSION = 'SYNTHETIC-workspace-native-rehearsal-v1'
base.RUN_ID = 'SYNTHETIC-workspace-native-rehearsal-20261012-checked'
REPORT = ('# 工作区链路演练报告\n\n'
          '这份短报告只记录来源中五场比赛的队列：五场实际 queue_id 均为420。'
          '这句话不判断胜负原因，也不把观摩对象当成阅读者。\n\n'
          '报告应把事实、相关性和复盘假设分开表达。[K5]')


def controls():
    inputs = diagnostic.source_inputs(REPORT)
    request = base.TimedDocumentWorkflow.make_request(inputs)
    request = replace(request, metadata={**request.metadata,
        'coach_budget_contract': 'coach-bounded-review-v2'})
    request = base.identity.prepare_request(request, base.identity.BASELINE)
    material = dict(report_origin='New tiny report for local workspace rehearsal only',
        source_key='workspace-probe', source_stage='initial', report=REPORT,
        calibrated_blocks=[], current_input_json=inputs.data_json,
        source_message=request.messages[2].content,
        deterministic_source_message=request.messages[3].content,
        full_policy_text=request.messages[0].content,
        provenance='SYNTHETIC TRANSPORT FIXTURE; no Provider request occurred. '
                   'New local task, not V2/H5/S8 or any closed-batch re-review.')
    row = dict(key='workspace-probe:initial', variant=base.identity.BASELINE,
        source_key='workspace-probe', source_stage='initial', stage='initial',
        expected_verdict='accept', request_sha256=base.sha(base.identity.request_bytes(request)),
        report_sha256=base.sha(REPORT.encode()), material_sha256=base.sha(base.options.canonical(material)),
        policy_sha256=base.sha(request.messages[0].content.encode()), temperature=request.temperature)
    return [(row, material, request)]


_prepare = adapter.prepare
def prepare(**kwargs):
    plan, rows = _prepare(**kwargs)
    for path in ('tests/host_workspace_native_rehearsal.py', 'tests/test_document_semantic_execution.py'):
        plan['source_sha256'][path] = base.sha((ROOT / path).read_bytes())
    plan.update(scope='SYNTHETIC transport, real native Host; new tiny local report only.',
                synthetic_transport=True, actual_project_provider_calls=0,
                actual_project_http_requests=0, actual_project_tokens=0,
                runner_contract=base.VERSION)
    # The reused observer reserves the full 600-second request *after* local
    # setup. Give this zero-network fixture room for that existing guard.
    plan['budget']['max_active_seconds'] = 1200
    return plan, rows


_task = base.host.task
def task(*args, **kwargs):
    value = json.loads(_task(*args, **kwargs))
    value['instructions'] = (
        'This is a LOCAL WORKSPACE INTEGRATION REHEARSAL. response.json was authored by '
        'a deterministic OFFLINE fixture, not by a Provider. Transport counters are synthetic, '
        'not real HTTP or usage. Review this new tiny report, full source and synthetic '
        'opinion independently; do not certify any old business report or paid call. '
        + value['instructions'])
    return json.dumps(value, ensure_ascii=False)


base.controls, base.prepare, base.host.task = controls, prepare, task


def no_network(*args, **kwargs):
    raise RuntimeError('rehearsal_python_network_forbidden')


def start(args):
    # The fixture class only writes synthetic records; block Python sockets too.
    socket.socket.connect = no_network
    socket.create_connection = no_network
    plan, rows = prepare(root_thread_id=args.root_thread_id,
                         independent_thread_id=args.independent_thread_id)
    directory = args.directory.resolve()
    expected = (base.OPERATOR_ROOT / 'rehearsal-runs' / base.RUN_ID).resolve()
    if directory != expected:
        raise ValueError('rehearsal_directory_mismatch')
    with base.CodexReadOnlyClient(args.codex_executable) as client:
        preflight = base.verify_native_principals(client, plan)
        source = base.CodexHostReviewEventSource(client, plan)
        directory.mkdir(parents=True, exist_ok=False)
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        pin = base.sha(base.options.canonical(plan))
        base.write_new_json(directory / 'plan.json', dict(preparation_plan=plan,
            plan_sha256=pin, execution_head=head, ci_run='LOCAL-SYNTHETIC-NO-CI-CLAIM'))
        now = datetime.now(timezone.utc)
        base.write_new_json(directory / 'authorization.json', dict(version=base.AUTH_VERSION,
            authorized=True, user_instruction='Continue authorized LOCAL no-paid workspace repair. '
            'Synthetic test authorization only; never valid for Provider execution.',
            head=head, ci_run='LOCAL-SYNTHETIC-NO-CI-CLAIM', plan_sha256=pin, budget=plan['budget'],
            issued_at=now.isoformat(), expires_at=(now + timedelta(hours=2)).isoformat()))
        base.write_new_json(directory / 'execution-preflight.json', preflight)
        fixture = load_private(ROOT / 'tests/test_document_semantic_execution.py',
                               'tests._explicit_synthetic_transport')
        fixture.identity, fixture.transport = base.identity, base.transport
        provider = fixture.OfflineProvider()
        result = base.runner.observe(directory, plan, rows, provider, source)
        print(json.dumps(dict(evidence='SYNTHETIC TRANSPORT / REAL NATIVE HOST',
            actual_project_provider_calls=0, actual_project_http_requests=0,
            actual_project_tokens=0, inner_fixture_result=result), ensure_ascii=False), flush=True)
        if not result['scan_completed']:
            raise SystemExit(1)


if __name__ == '__main__':
    # Reuse the real material/submit/replay/seal CLI. The paid run remains
    # disabled; the separate start action takes no package, API key or cost grant.
    if sys.argv[1:2] == ['start']:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('action', choices=('start',))
        parser.add_argument('--directory', type=Path, required=True)
        parser.add_argument('--root-thread-id', required=True)
        parser.add_argument('--independent-thread-id', required=True)
        parser.add_argument('--codex-executable', type=Path, required=True)
        start(parser.parse_args())
    else:
        base.main()
