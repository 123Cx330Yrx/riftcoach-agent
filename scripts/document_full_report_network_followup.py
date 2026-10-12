"""Prospective three-report run after the operator changed the network route.

Keep the closed batch immutable. Reuse its request builder and execution gates;
only the new run identity and public pre-execution evidence differ.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'scripts/document_full_report_diagnostic.py'
spec = importlib.util.spec_from_file_location('scripts._network_full_report', ROOT / SOURCE)
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)
base = diagnostic.base

VERSION = 'document-full-report-network-followup-v1'
EVIDENCE = {
    'data/evaluation/results/document_full_report_initial_result_20261012.json':
        '47da76c94f4688e62ff4687bd018abe455139f5dc50723ebc7a6f033ccdbcce3',
    'data/evaluation/results/document_full_report_initial_close_audit_20261012.json':
        'eceb3b8ee71b85ad7cd49b4eb8475b46541a5fc288dc0804181952a3c1f4b023',
    'data/evaluation/results/document_full_report_route_followup_20261012.json':
        '7f82aa96e25d1d3969569009c487a98ecc9b8c7b2d6dd5e9d614aa5768008a59',
}
base.VERSION = base.runner.VERSION = VERSION
base.AUTH_VERSION = base.runner.AUTH_VERSION = 'document-full-report-network-authorization-v1'
base.RUN_ID = 'document-full-report-network-followup-20261012'
base.ADAPTER_SOURCE = 'scripts/document_full_report_network_followup.py'
base.OPERATOR_ROOT = Path(
    'C:/Users/33502/Documents/Agent/outputs/riftcoach-full-report-network-followup-20261012')


def prepare(*, root_thread_id, independent_thread_id):
    for path, expected in EVIDENCE.items():
        if base.sha((ROOT / path).read_bytes()) != expected:
            raise ValueError('network_followup_evidence_changed')
    plan, rows = diagnostic.prepare(root_thread_id=root_thread_id,
                                    independent_thread_id=independent_thread_id)
    for path in (SOURCE, 'tests/test_document_full_report_network_followup.py', *EVIDENCE):
        plan['source_sha256'][path] = base.sha((ROOT / path).read_bytes())
    plan.update(runner_contract=VERSION, network_followup_evidence=EVIDENCE.copy(),
        prior_run_id='document-full-report-initial-20261012',
        prior_run_reopened=False, prior_unknown_usage_calls=1,
        network_boundary='Operator switched from TUN to system proxy. Public DNS/WLAN '
        'and one TCP/TLS connection succeeded; this does not prove historical cause, '
        'persistent connectivity or model API availability. No agent network reconfiguration.',
        scope='New separately authorized observation of the same three full reports after '
        'the network route changed. No old budget reuse, edits, fresh, retries or qualification.')
    return plan, rows


base.prepare = prepare
Package = base.Package

if __name__ == '__main__':
    base.main()
