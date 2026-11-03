"""Only the two never-sent full reports, with explicit executable dispatch paths."""
import importlib.util
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'scripts/document_full_report_diagnostic.py'
spec = importlib.util.spec_from_file_location('scripts._remaining_full_report', ROOT / SOURCE)
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)
base = diagnostic.base
VERSION = 'document-full-report-remaining-initial-v1'
diagnostic.CASES = (('H5', 'reject'), ('S8', 'reject'))
EVIDENCE = {
    'data/evaluation/results/document_full_report_network_result_20261012.json':
        '746ae66a490fe211bb4fca3a305e329bcf9b94a70cc709c452ba1956a58ed086',
    'data/evaluation/results/document_full_report_network_close_audit_20261012.json':
        'c29139af631580bc9be87610bfc6a74c85324b86fc0af947a82c2dd333403a10',
    'data/evaluation/results/host_explicit_cwd_probe_20261012.json':
        'cf23819bb3add8c37c84eb4d6c3f2aba43b1f212841c832b0c2f5586fa4f994b',
}
base.VERSION = base.runner.VERSION = VERSION
base.AUTH_VERSION = base.runner.AUTH_VERSION = 'document-full-report-remaining-authorization-v1'
base.RUN_ID = 'document-full-report-remaining-initial-20261012'
base.ADAPTER_SOURCE = 'scripts/document_full_report_remaining_initial.py'
base.OPERATOR_ROOT = Path(
    'C:/Users/33502/Documents/Agent/outputs/riftcoach-full-report-remaining-initial-20261012')


def prepare(*, root_thread_id, independent_thread_id):
    for path, expected in EVIDENCE.items():
        if base.sha((ROOT / path).read_bytes()) != expected:
            raise ValueError('remaining_initial_evidence_changed')
    prior = base.read(ROOT / next(iter(EVIDENCE)))
    if prior['result']['unexecuted'] != ['report-H5:initial', 'report-S8:initial']:
        raise ValueError('remaining_initial_prior_scope_changed')
    plan, rows = diagnostic.prepare(root_thread_id=root_thread_id,
                                    independent_thread_id=independent_thread_id)
    for path in (SOURCE, 'tests/test_document_full_report_remaining_initial.py', *EVIDENCE):
        plan['source_sha256'][path] = base.sha((ROOT / path).read_bytes())
    plan.update(runner_contract=VERSION, prior_evidence=EVIDENCE.copy(),
        prior_run_reopened=False, omitted_uncertified_key='report-V2:initial',
        dispatch_execution='Generated dispatch contains verified absolute repository cwd '
        'and current Python executable; no inferred backend subdirectory.',
        scope='Two never-sent H5/S8 initial reviews only. V2 remains uncertified and is '
        'not resent or re-reviewed. No old budget reuse, edits, fresh, retries or qualification.')
    plan['limitations'] = [s.replace('Three single observations', 'Two single observations')
                           for s in plan['limitations']]
    return plan, rows


# Replace only this private runner's checkpoint module, never a frozen/shared
# helper. Keep its full task validation and document-artifact verification.
checkpoint = base.load_private(ROOT / 'scripts/host_review_task_checkpoint.py',
                               'scripts._remaining_initial_checkpoint')
_dispatch = checkpoint.dispatch


def explicit_dispatch(path, expected_sha256, *, document_artifacts=False):
    cwd = ROOT.resolve(strict=True)
    python = Path(sys.executable).resolve(strict=True)
    if not cwd.is_dir() or not python.is_file():
        raise ValueError('remaining_initial_execution_paths_invalid')
    body = _dispatch(path, expected_sha256, document_artifacts=document_artifacts)
    executable = ("& '" + str(python).replace("'", "''") + "'"
                  if sys.platform == 'win32' else shlex.quote(str(python)))
    body = body.replace('python -m ', executable + ' -m ')
    return (f'Verified working directory (tool workdir): {cwd}\n'
            f'Verified Python executable: {python}\n'
            'Use these literal absolute paths; do not append backend or infer another directory.\n'
            + body)


checkpoint.dispatch = explicit_dispatch
base.runner.checkpoint = checkpoint
base.prepare = prepare
Package = base.Package
runner = base.runner
identity = base.identity
transport = base.transport

if __name__ == '__main__':
    base.main()
