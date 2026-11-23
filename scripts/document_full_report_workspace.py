"""Prospective workspace-wired runner; paid scope has NOT been selected.

Read/prepare/submit/replay/seal remain usable for explicit local verification.
The run action fails before credentials. A future paid plan must select its own
cases, version, authorization and cost; it cannot reopen any historical batch.
"""
from pathlib import Path
import sys

from scripts.document_sampling_screening import load_private
from scripts.host_review_workspace import HostReviewWorkspace, VERSION as WORKSPACE_VERSION

ROOT = Path(__file__).resolve().parents[1]
diagnostic = load_private(ROOT / 'scripts/document_full_report_diagnostic.py',
                          'scripts._workspace_full_report')
base = diagnostic.base
VERSION = 'document-full-report-workspace-verification-v1'
base.VERSION = base.runner.VERSION = VERSION
base.AUTH_VERSION = base.runner.AUTH_VERSION = 'document-workspace-verification-authorization-v1'
base.RUN_ID = 'document-host-workspace-verification-20261012'
base.ADAPTER_SOURCE = 'scripts/document_full_report_workspace.py'
base.OPERATOR_ROOT = ROOT / 'tmp/host-review-workspace'


def prepare(*, root_thread_id, independent_thread_id):
    plan, rows = diagnostic.prepare(root_thread_id=root_thread_id,
                                    independent_thread_id=independent_thread_id)
    for source in ('scripts/document_full_report_diagnostic.py',
                   'scripts/host_review_workspace.py',
                   'tests/test_host_review_workspace.py'):
        plan['source_sha256'][source] = base.sha((ROOT / source).read_bytes())
    plan.update(runner_contract=VERSION, host_workspace_contract=WORKSPACE_VERSION,
                scope='LOCAL VERIFICATION ONLY. No paid scope selected; no old case resend.',
                paid_execution_enabled=False)
    return plan, rows


def unavailable_paid_run(args):
    raise ValueError('host_workspace_paid_scope_not_selected')


base.prepare = prepare
base.run = unavailable_paid_run
runner, identity, transport = base.runner, base.identity, base.transport
Package = base.Package
workspace = HostReviewWorkspace(cwd=ROOT, python=sys.executable,
    answers=base.OPERATOR_ROOT / 'author-answers',
    evidence_roots=(ROOT / 'data/runs', base.OPERATOR_ROOT / 'rehearsal-runs'))
workspace.install(runner)

if __name__ == '__main__':
    base.main()
